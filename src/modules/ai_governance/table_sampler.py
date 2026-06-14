# Call Trino or Spark to get schema and sample data
import logging
import os
from typing import List, Dict, Any
from pyspark.sql import SparkSession
import pyspark.sql.functions as F

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc

setup_logging()
logger = logging.getLogger(__name__)

class IcebergTableSampler:
    def __init__(self, spark: SparkSession, config: dict):
        self.spark = spark
        self.config = config

    def extract_table_schema_and_sampler(self, table_fqn: str, sample_size: int = 30):
        """
        Retrieve the schema and sample data for a given Iceberg table.

        :param table_fqn: Fully Qualified Name of Iceberg table (Eg: 'iceberg.db.fact_user_profiles')
        :param sample_size: Size of sample data to extract (Default: 30)
        :return: Return list of dicts containing schema and sample data for each column.
                 [
                    {
                        "column_name": "c01",
                        "data_type": "string",
                        "sample_data": ["0912345678", "0987654321", ...]
                    },
                    ...
                 ]
        """
        try:
            logger.info(f"Extracting schema and sample data for table: {table_fqn} with sample size: {sample_size} ...")
            df = self.spark.read.format("iceberg").option("inferSchema", "false").load(table_fqn)
            spark_schema = df.schema

            raw_fraction = (sample_size * 5) / df.count()
            calculated_fraction = min(raw_fraction, 1.0)
            sample_df = df.sample(withReplacement=False, fraction=calculated_fraction).limit(sample_size * 3)
            # sample_df = df.sample(withReplacement=False, fraction=sample_size * 5 / df.count()).limit(sample_size * 3)
            extracted_columns_metadata = []

            # Extract schema and sample data for each column
            for field in spark_schema.fields:
                col_name = field.name
                data_type = str(field.dataType).lower()

                col_samples_df = (
                    sample_df.select(col_name)
                    .filter(F.col(col_name).isNotNull())
                    .filter((F.trim(F.col(col_name)) != "") | (F.col(col_name) == None))
                )
                raw_rows = col_samples_df.limit(sample_size).collect()

                # Convert Spark row objects to Python data
                clean_sample_list = [str(row[col_name]) for row in raw_rows]

                column_payload = {
                    "column_name": col_name,
                    "sample_data": clean_sample_list
                }

                extracted_columns_metadata.append(column_payload)
            logger.info(f"Schema and sample data extracted for table: {table_fqn}")
            return extracted_columns_metadata
        except Exception as e:
            logger.error(f"Error extracting schema and sample data for table: {table_fqn}", exc_info=True)
            raise e


if __name__ == "__main__":
    config = load_config()
    os.environ["AWS_REGION"] = config["storage"]["minio"]["region"]
    # Check /etc/hosts to see if the host is in there: 127.0.0.1 minio postgres spark-master
    spark = get_spark_iceberg_jdbc(config)

    catalog_name = config["spark"]["iceberg_catalog_name"]
    db_name = config["spark"]["iceberg_db_name"]
    full_table_path = f"{config['spark']['iceberg_catalog_name']}.{db_name}.hr_employees"

    sampler = IcebergTableSampler(spark, config)
    sample_data = sampler.extract_table_schema_and_sampler(full_table_path, sample_size=10)

    print("Sample Data:")
    print(sample_data)


