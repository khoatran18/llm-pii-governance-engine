import logging

from pyspark.sql import DataFrame
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

    def _hash_mask(self, df: DataFrame, column: str):
        """
        Hash the value of a column by applying SHA-256
        """
        return df.withColumn(column, F.sha2(F.col(column).cast("string"), 256))

    def _redact_mask(self, df: DataFrame, column: str):
        """
        Replace the value of a column with a fixed string
        """
        return df.withColumn(column, F.lit("REDACTED"))

    def _nullify_mask(self, df: DataFrame, column: str):
        """
        Replace the value of a column with NULL (maintaining the same data type)
        """
        # return df.withColumn(column, F.lit(None).cast(df.schema[column].dataType))
        return df.withColumn(column, F.lit(None))

    def _partial_mask(self, df: DataFrame, column: str):
        """
        Mask a partial value of a column based on the format of the value
        With Email:                 -> g******@gmail.com
        With Phone or Resident ID:  -> 045*****6789
        """
        # For Email
        email_masked = F.expr(f"""
            concat(
                substring({column}, 1, 1),
                repeat('*', greatest(0, length({column}) - length(split({column}, '@')[1]) - 2)),
                '@',
                split({column}, '@')[1]
            )
        """)

        # For Name
        name_masked = F.expr(f"""
            concat_ws(' ',
                transform(
                    split({column}, ' '),
                    word -> concat(substring(word, 1, 1), repeat('*', greatest(0, length(word) - 1)))
                )
            )
        """)

        # For Phone or Resident ID
        phone_masked = F.expr(f"""
            concat(
                substring({column}, 1, 3),
                repeat('*', greatest(0, length({column}) - 7)),
                substring({column}, -4, 4)
            )
        """)

        return df.withColumn(
            column,
            F.when(F.col(column).like("%@%"), email_masked)
            .otherwise(
                F.when(F.col(column).contains(" "), name_masked)
                .otherwise(
                    F.when(F.length(F.col(column)) >= 6, phone_masked)
                    .otherwise(F.lit("[INVALID_DATA]"))
                )
            )
        )


    def _clear_text(self, df: DataFrame, column: str):
        return df

    def apply_masking(self, df: DataFrame, column: str, masking_rule: MaskingRule):
        transformer = self._transformer_map.get(masking_rule)
        if transformer:
            return transformer(df, column)
        else:
            logger.error(f"Invalid masking rule: {masking_rule}")
            raise ValueError(f"Invalid masking rule: {masking_rule}")



    # def _partial_mask(self, df: DataFrame, column: str):
    #     """
    #     Mask a partial value of a column based on the format of the value
    #     With Email:                 -> g******@gmail.com
    #     With Phone or Resident ID:  -> 045*****6789
    #     """
    #     # For Email
    #     logger.info("Step 1")
    #     domain_part = F.element_at(F.split(F.col(column), "@"), 1)
    #     email_name_len = F.length(F.col(column)) - F.length(domain_part) - F.lit(1)
    #
    #     logger.info("Step 2")
    #     email_star_count = F.greatest(F.lit(0), email_name_len - F.lit(1))
    #     logger.info("Step 3")
    #     email_masked = F.concat(
    #         F.substring(F.col(column), 1, 1),
    #         F.repeat("*", email_star_count),
    #         F.lit("@"),
    #         domain_part
    #     )
    #
    #     logger.info("Step 4")
    #     # For Phone or Resident ID
    #     num_star_count = F.greatest(F.lit(0), F.length(F.col(column)) - F.lit(7))
    #     logger.info("Step 5")
    #     phone_masked = F.concat(
    #         F.substring(F.col(column), 1, 3),
    #         F.repeat("*", num_star_count),
    #         F.substring(F.col(column), -4, 4)
    #     )
    #
    #     return df.withColumn(
    #         column,
    #         F.when(F.col(column).like("%@%"), email_masked) \
    #             .otherwise(
    #                 F.when(F.length(F.col(column)) >= 6, phone_masked)
    #                     .otherwise(F.lit("[INVALID_DATA]"))
    #         )
    #     )




