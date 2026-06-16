import logging
import os
import sys

from src.core.dtos.enums import UserRole
from src.core.postgres.postgres_client import PostgresClient
from src.modules.policy_engine.data_masker import DataMasker
from src.modules.policy_engine.pipeline import PolicyEngine

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.spark.spark_builder import get_spark_iceberg_jdbc


setup_logging()
logger = logging.getLogger(__name__)
policy_engine_logger = logging.getLogger("policy_engine")

def policy_engine_main(table_name: str, selected_columns: list, user_role: UserRole, config: dict = None):
    policy_engine_logger.info("Starting Policy Engine Pipeline...")

    # 1. Load config
    policy_engine_logger.info("Loading config...")
    if not config:
        try:
            config = load_config()
            policy_engine_logger.info("Config loaded successfully.")
        except Exception as e:
            policy_engine_logger.error("Failed to load config.", exc_info=True)
            return

    os.environ["AWS_REGION"] = config["storage"]["minio"]["region"]

    # 2. Init infrastructure
    logger.info("Connecting to infrastructure...")
    pg_client = PostgresClient(config)
    spark_session = get_spark_iceberg_jdbc(config)
    logger.info("Infrastructure connected successfully.")

    logger.info("Initializing Policy Engine Pipeline...")
    data_masker = DataMasker()
    pipeline = PolicyEngine(spark_session, pg_client, data_masker, config)
    logger.info("Policy Engine Pipeline initialized successfully.")

    # 3. Execute Policy Engine Pipeline
    logger.info("Starting Policy Engine Pipeline...")
    all_secure_dfs = pipeline.execute_secure_pipeline(table_name, selected_columns, user_role)
    logger.info("Policy Engine Pipeline completed.")

    return all_secure_dfs


if __name__ == "__main__":
    policy_engine_logger.info("=== POLICY ENGINE DYNAMIC TESTING SYSTEM ===")

    test_table = "citizen_info"

    analyst_role = UserRole.AUDITOR

    policy_engine_logger.info(f"Executing automated column query for {analyst_role.name} on table '{test_table}'")
    secure_dfs_case1 = policy_engine_main(
        table_name=None,
        selected_columns=[],
        user_role=analyst_role
    )

    if secure_dfs_case1 and len(secure_dfs_case1) > 0:
        for i in range(len(secure_dfs_case1)):
            secure_dfs_case1[i].show(truncate=False)
        print(f"\n[CASE 1 RESULT] All columns fetched & dynamically secured for Role {analyst_role.name}:")
    else:
        policy_engine_logger.warning("Case 1 returned no data or an unexpected error occurred.")
