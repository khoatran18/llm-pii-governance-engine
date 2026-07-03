import logging
from pyspark.sql import DataFrame, Column
import pyspark.sql.functions as F

from src.config.logging import setup_logging
from src.core.dtos.enums import MaskingRule

setup_logging()
logger = logging.getLogger(__name__)

class DataMasker:

    def __init__(self):
        self._transformer_map = {
            MaskingRule.HASH_MASK: self._hash_mask,
            MaskingRule.REDACTED_MASK: self._redact_mask,
            MaskingRule.NULLIFY_MASK: self._nullify_mask,
            MaskingRule.PARTIAL_MASK: self._partial_mask,
            MaskingRule.CLEAR_TEXT: self._clear_text
        }

    def _hash_mask(self, column: str) -> Column:
        """
        Hash the value of a column by applying SHA-256
        """
        return F.sha2(F.col(column).cast("string"), 256)

    def _redact_mask(self, column: str) -> Column:
        """
        Replace the value of a column with a fixed string
        """
        return F.lit("REDACTED")

    def _nullify_mask(self, column: str) -> Column:
        """
        Replace the value of a column with NULL (maintaining the same data type)
        """
        return F.lit(None).cast("string")

    def _partial_mask(self, column: str) -> Column:
        """
        Mask a partial value of a column based on the format of the value
        With Email:                 -> g******@gmail.com
        With Phone or Resident ID:  -> 045*****6789
        """

        # Email Expression
        email_masked = F.expr(f"""
            concat(
                substring({column}, 1, 1),
                repeat('*', greatest(0, length({column}) - length(split({column}, '@')[1]) - 2)),
                '@',
                split({column}, '@')[1]
            )
        """)

        # Name Expression
        # name_masked = F.expr(f"""
        #     concat_ws(' ',
        #         transform(
        #             split({column}, ' '),
        #             word -> concat(substring(word, 1, 1), repeat('*', greatest(0, length(word) - 1)))
        #         )
        #     )
        # """)

        # name_masked = F.regexp_replace(
        #     F.regexp_replace(F.col(column), r"(?<=\s)\w", "*"),  # Mask ký tự đầu của các từ sau
        #     r"(?<=^\w)\w+", "*"  # Mask phần còn lại của từ đầu tiên
        # )

        # name_masked = F.expr(f"regexp_replace({column}, r'(\\w)(\\w+)', '$1***')")

        name_masked = F.regexp_replace(F.col(column), r"(?<=\S)\S", "*")

        # Phone / CCCD Expression
        phone_masked = F.expr(f"""
            concat(
                substring({column}, 1, 3),
                repeat('*', greatest(0, length({column}) - 7)),
                substring({column}, -4, 4)
            )
        """)

        return F.when(F.col(column).like("%@%"), email_masked) \
                .otherwise(
                    F.when(F.col(column).contains(" "), name_masked) \
                     .otherwise(
                         F.when(F.length(F.col(column)) >= 6, phone_masked) \
                          .otherwise(F.lit("[INVALID_DATA]"))
                     )
                )

    def _clear_text(self, column: str) -> Column:
        return F.col(column)

    def get_masking_expression(self, column: str, masking_rule: MaskingRule) -> Column:
        """
        Return a Column expression based on the masking rule
        """
        rule_enum = masking_rule
        if isinstance(masking_rule, str):
            try:
                rule_enum = MaskingRule(masking_rule)
            except ValueError:
                rule_enum = MaskingRule[masking_rule]

        transformer = self._transformer_map.get(rule_enum)
        if transformer:
            return transformer(column).alias(column)
        else:
            logger.error(f"Invalid masking rule: {masking_rule}")
            raise ValueError(f"Invalid masking rule: {masking_rule}")

    def apply_masking(self, df: DataFrame, column: str, masking_rule: MaskingRule) -> DataFrame:
        """
        Backward compatibility
        """
        expr = self.get_masking_expression(column, masking_rule)
        return df.withColumn(column, expr)
