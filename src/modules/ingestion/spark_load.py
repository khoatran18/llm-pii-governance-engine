import glob
import logging
from pathlib import Path

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc

setup_logging()
logger = logging.getLogger(__name__)

def ingest_single_csv_to_iceberg(spark, config, csv_path: str):
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
        df = spark.read \
                .format("csv") \
                .option("header", True) \
                .option("inferSchema", False) \
                .load(csv_path)

        # Get full table path
        catalog_name = config["spark"]["iceberg_catalog_name"]
        db_name = config["spark"]["iceberg_db_name"]
        full_table_path = f"{config['spark']['iceberg_catalog_name']}.{db_name}.{table_name}"

        logger.info(f"Ensuring namespace exists: {catalog_name}.{db_name}")
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {catalog_name}.{db_name}")

        # Write data to Iceberg table
        df.write \
            .format("iceberg") \
            .mode("overwrite") \
            .saveAsTable(full_table_path)

        logger.info(f"Data loaded successfully into Iceberg table: {table_name}")

    except Exception as e:
        logger.error(f"Error loading data into Iceberg table: {table_name}", exc_info=True)


def dynamic_ingestion():
    logger.info("Starting dynamic ingestion job...")
    config = load_config()
    spark = get_spark_iceberg_jdbc(config)

    csv_folder = f"{config['spark']['csv_folder']}"
    all_csv_files = glob.glob(csv_folder)

    if not all_csv_files:
        logger.error(f"No CSV files found in the specified folder {csv_folder}.")
        return
    else:
        logger.info(f"Found {len(all_csv_files)} CSV files to ingest.")
        for csv_file in all_csv_files:
            ingest_single_csv_to_iceberg(spark, config, csv_file)

        print("Dynamic ingestion job completed successfully.")

if __name__ == "__main__":
    dynamic_ingestion()