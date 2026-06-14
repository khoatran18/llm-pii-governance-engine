import argparse
import logging
import os
import sys

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc
from src.modules.ingestion.spark_loader import SparkLoader

setup_logging()
logger = logging.getLogger(__name__)

def ingestion_main(csv_folder: str = None, config: dict = None):
    logger.info("Starting Spark Load Pipeline...")

    # 1. Load config
    logger.info("Loading config...")
    if not config:
        try:
            config = load_config()
            logger.info("Config loaded successfully.")
        except Exception as e:
            logger.error("Failed to load config.", exc_info=True)
            return

    if csv_folder:
        logger.info(f"Overriding CSV folder with: {csv_folder}")
        config["spark"]["csv_folder"] = csv_folder

    os.environ["AWS_REGION"] = config["storage"]["minio"]["region"]

    # 2. Init infrastructure
    logger.info("Connecting to infrastructure...")
    spark_session = get_spark_iceberg_jdbc(config)
    logger.info("Infrastructure connected successfully.")

    logger.info("Initializing Spark Loader Pipeline...")
    pipeline = SparkLoader(spark_session, config)
    logger.info("Spark Loader Pipeline initialized successfully.")

    # 3. Execute Spark Loader Pipeline
    logger.info("Starting Spark Loader Pipeline...")
    try:
        pipeline.dynamic_ingestion()
        logger.info("Spark Loader Pipeline completed successfully.")
    except Exception as e:
        logger.error("Spark Loader Pipeline failed.", exc_info=True)
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingestion Main")
    parser.add_argument("--csv_folder", type=str, default=None, help="Path to the CSV folder")

    args = parser.parse_args()
    ingestion_main(csv_folder=args.csv_folder)