import logging
import os
import sys

from src.core.postgres.postgres_client import PostgresClient
from src.llm.factory import LLMFactory
from src.modules.ai_governance.llm_scanner import LLMTableScanner
from src.modules.ai_governance.table_sampler import IcebergTableSampler
from src.modules.ai_governance.utils import get_table_fqn, get_all_table_fqn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc

from src.modules.ai_governance.pipeline import AIGovernancePipeline

setup_logging()
logger = logging.getLogger(__name__)

def main(target_table: str = ""):
    logger.info("Starting AI Governance Pipeline...")

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
    pg_client = PostgresClient(config)
    spark_session = get_spark_iceberg_jdbc(config)
    logger.info("Infrastructure connected successfully.")

    logger.info("Initializing AI Governance Pipeline...")
    iceberg_sampler = IcebergTableSampler(spark_session)
    llm_provider = LLMFactory.get_llm_provider(config)
    llm_scanner = LLMTableScanner(llm_provider, max_retries=config["llm"]["max_retries"])
    pipeline = AIGovernancePipeline(
        iceberg_sampler=iceberg_sampler,
        llm_scanner=llm_scanner,
        pg_client=pg_client,
        config=config,
    )
    logger.info("AI Governance Pipeline initialized successfully.")

    # 3. Execute AI Governance Pipeline
    logger.info("Starting AI Governance Pipeline...")
    if target_table:
        logger.info(f"Executing AI Governance pipeline for table: {target_table} ...")
        table_fqn = get_table_fqn(config, target_table)
        pipeline.execute_pipeline(target_table, table_fqn)
        logger.info(f"AI Governance pipeline for table: {target_table} completed.")
    else:
        logger.info(f"Executing AI Governance pipeline for all tables ...")
        tables_fqn = get_all_table_fqn(config)
        for table_fqn in tables_fqn:
            logger.info(f"Executing AI Governance pipeline for table: {table_fqn.split('.')[-1]} ...")
            pipeline.execute_pipeline(table_fqn.split(".")[-1], table_fqn)
        logger.info(
            f"AI Governance pipeline for all tables completed."
        )



if __name__ == "__main__":
    main(target_table="administrative_records")







