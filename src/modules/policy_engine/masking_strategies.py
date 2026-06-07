from pyspark.sql import DataFrame
import pyspark.sql.functions as F


def hash_mask(df: DataFrame, column: str):
    """
    Hash the value of a column by applying SHA-256
    """
    return df.withColumn(column, F.sha2(F.col(column).cast("string"), 256))

def hash_redact(df: DataFrame, column: str):
    """
    Replace the value of a column with a fixed string
    """
    return df.withColumn(column, F.lit("REDACTED"))

def mask_nullify(df: DataFrame, column: str):
    """
    Replace the value of a column with NULL (maintaining the same data type)
    """
    return df.withColumn(column, F.lit(None).cast(df.schema[column].dataType))

def mask_partial(df: DataFrame, column: str):
    """
    Mask a partial value of a column based on the format of the value
    With Email:                 -> g******@gmail.com
    With Phone or Resident ID:  -> 045*****6789
    """

    # For Email
    domain_part = F.element_at(F.split(F.col(column), "@"), 1)
    email_name_len = F.length(F.col(column)) - F.length(domain_part) - 1

    email_star_count = F.greatest(F.lit(0), email_name_len - 1)
    email_masked = F.concat(
        F.substring(F.col(column), 1, 1),
        F.repeat("*", email_star_count),
        F.lit("@"),
        domain_part
    )

    # For Phone or Resident ID
    num_star_count = F.greatest(F.lit(0), F.length(F.col(column)) - 7)
    phone_masked = F.concat(
        F.substring(F.col(column), 1, 3),
        F.repeat("*", num_star_count),
        F.substring(F.col(column), -4, 4)
    )

    return df.withColumn(
        column,
        F.when(F.col(column).like("%@%"), email_masked) \
            .otherwise(
                F.when(F.length(F.col(column)) >= 6, phone_masked)
                    .otherwise(F.lit("[INVALID_DATA]"))
        )
    )








