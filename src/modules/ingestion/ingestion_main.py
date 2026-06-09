import logging
import os

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc
from src.modules.ingestion.spark_loader import SparkLoader

setup_logging()
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Spark Load Pipeline...")

    # 1. Load config
    logger.info("Loading config...")
    try:
        config = load_config()
        logger.info("Config loaded successfully.")
    except Exception as e:
        logger.error("Failed to load config.", exc_info=True)
        return

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
    main()