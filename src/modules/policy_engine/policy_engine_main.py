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

    # ---------------------------------------------------------------------------
    # CASE 1: Data Analyst (ANALYST) queries the table WITHOUT passing columns
    # System must automatically discover all columns and apply the vertical masking matrix [cite: 2, 44]
    # ---------------------------------------------------------------------------
    analyst_role = UserRole.AUDITOR

    policy_engine_logger.info(
        f"\n>>> [CASE 1] Executing automated column query for {analyst_role.name} on table '{test_table}'")
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

    # ---------------------------------------------------------------------------
    # CASE 2: Information Security Auditor (AUDITOR) scans the entire Data Lakehouse [cite: 6, 92]
    # Passing table_name="" triggers multi-table orchestration via Metadata Store
    # All columns from discovered tables are automatically fetched and masked [cite: 44, 92]
    # ---------------------------------------------------------------------------
    # auditor_role = UserRole.AUDITOR
    #
    # policy_engine_logger.info(f"\n>>> [CASE 2] Executing FULL LAKEHOUSE SCAN for Role: {auditor_role.name}")
    # secure_dfs_case2 = main(
    #     table_name="",
    #     selected_columns=["*"],  # Fetch all available columns across discovered tables
    #     user_role=auditor_role
    # )
    #
    # if secure_dfs_case2:
    #     print(
    #         f"\n[CASE 2 RESULT] Total data assets successfully secured for Auditor: {len(secure_dfs_case2)} table(s).")
    #     for idx, df in enumerate(secure_dfs_case2):
    #         print(f"\n--> Displaying sample secure data for Table #{idx + 1}:")
    #         # Preview a small sample batch of rows for compliance validation
    #         df.show(5, truncate=False)
    # else:
    #     policy_engine_logger.warning("Case 2 failed to discover any tables or Metadata Store catalog is empty.")
    #
    # # ---------------------------------------------------------------------------
    # # CASE 3: Super Administrator (ADMIN) queries the table WITHOUT passing columns
    # # Admin must bypass all masking rules to view raw ground-truth clear text data [cite: 148]
    # # ---------------------------------------------------------------------------
    # admin_role = UserRole.ADMIN
    #
    # policy_engine_logger.info(
    #     f"\n>>> [CASE 3] Executing automated column query for {admin_role.name} on table '{test_table}'")
    # secure_dfs_case3 = main(
    #     table_name=test_table,
    #     selected_columns=None,  # Passing None also triggers automated full-column fetch
    #     user_role=admin_role
    # )
    #
    # if secure_dfs_case3 and len(secure_dfs_case3) > 0:
    #     # Admin bypasses masking rules to view raw ground-truth data for governance control [cite: 148]
    #     print(f"\n[CASE 3 RESULT] Raw data visible to Administrator {admin_role.name} (Clear Text expected):")
    #     secure_dfs_case3[0].show(truncate=False)