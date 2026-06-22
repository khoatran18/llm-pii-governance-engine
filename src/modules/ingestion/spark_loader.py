import glob
import logging
from pathlib import Path

from src.config.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

class SparkLoader:
    def __init__(self, spark_session, config: dict):
        self.spark = spark_session
        self.config = config

    def ingest_single_csv_to_iceberg(self, csv_path: str):
        logger.info(
            f"Ingesting CSV file: {csv_path} ..."
        )

        # Check if the file exists
        path_obj = Path(csv_path)
        if not path_obj.exists():
            logger.error(f"File not found: {csv_path}")
            return

        # Get table name from the file path
        table_name = path_obj.stem.lower()

        try:
            # Load data csv
            logger.info(f"Loading data into Iceberg table: {table_name} ...")
            df = self.spark.read \
                    .format("csv") \
                    .option("header", True) \
                    .option("inferSchema", False) \
                    .load(csv_path)

            # Get full table path
            catalog_name = self.config["spark"]["iceberg_catalog_name"]
            db_name = self.config["spark"]["iceberg_db_name"]
            full_table_path = f"{self.config['spark']['iceberg_catalog_name']}.{db_name}.{table_name}"

            logger.info(f"Ensuring namespace exists: {catalog_name}.{db_name}")
            self.spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog_name}.{db_name}")

            # table_exists = self.spark.catalog.tableExists(full_table_path)
            #
            # if not table_exists:
            #     df.writeTo(full_table_path) \
            #         .tableProperty("write.format.default", "parquet") \
            #         .tableProperty("write.parquet.compression-codec", "snappy") \
            #         .create()
            #
            #     # Debug ngay sau khi tạo
            #     logger.info("=== TABLE PROPERTIES AFTER CREATE ===")
            #     self.spark.sql(f"SHOW TBLPROPERTIES {full_table_path}").show(truncate=False)
            #
            #     logger.info("=== TABLE FILES FORMAT ===")
            #     self.spark.sql(f"SELECT file_format, count(*) FROM {full_table_path}.files GROUP BY file_format").show()
            #
            # else:
            #     logger.info(f"Table {full_table_path} already exists. Checking current properties...")
            #
            #     props = self.spark.sql(f"SHOW TBLPROPERTIES {full_table_path}")
            #     props.show(truncate=False)
            #
            #     logger.info(f"Enforcing Parquet properties before overwrite...")
            #     self.spark.sql(f"""
            #         ALTER TABLE {full_table_path}
            #         SET TBLPROPERTIES (
            #             'write.format.default'='parquet',
            #             'write.parquet.compression-codec'='snappy'
            #         )
            #     """)
            #
            #     logger.info(f"Overwriting data in table {full_table_path}...")
            #     df.writeTo(full_table_path).overwritePartitions()
            #     logger.info(f"Table {full_table_path} overwritten successfully.")

            # Write data to Iceberg table
            df.write \
                .format("iceberg") \
                .mode("overwrite") \
                .saveAsTable(full_table_path)

            logger.info(f"Data loaded successfully into Iceberg table: {table_name}")



            # Ghi đè (Overwrite) dữ liệu bằng API V2
            # df.writeTo(full_table_path).overwrite()

        except Exception as e:
            logger.error(f"Error loading data into Iceberg table: {table_name}", exc_info=True)


    def dynamic_ingestion(self):
        logger.info("Starting dynamic ingestion job...")

        csv_folder = f"{self.config['spark']['csv_folder']}"
        all_csv_files = glob.glob(csv_folder)
        # all_csv_files = get_all_table_name(self.config)

        if not all_csv_files:
            logger.error(f"No CSV files found in the specified folder {csv_folder}.")
            return
        else:
            logger.info(f"Found {len(all_csv_files)} CSV files to ingest: {', '.join(all_csv_files)}")
            for csv_file in all_csv_files:
                self.ingest_single_csv_to_iceberg(csv_file)

            print("Dynamic ingestion job completed successfully.")

# if __name__ == "__main__":
#     dynamic_ingestion()