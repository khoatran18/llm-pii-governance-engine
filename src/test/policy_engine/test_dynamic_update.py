import logging
import time

from src.config.logging import setup_logging
from src.core.dtos.enums import UserRole, SensitivityLevel
from src.modules.policy_engine.data_masker import DataMasker
from src.modules.policy_engine.pipeline import PolicyEngine

setup_logging()
test_logger = logging.getLogger("test")

def test_dynamic_update(spark_session, pg_client, test_config):
    """
    Verification of Dynamic Policy Update Responsiveness
    - Test on column 'email_clean', with role ANALYST
    - First, 'email_clean' level is MEDIUM - NULLIFY_MASK
    - Then, updates 'email_clean' level to HIGH - HASH_MASK
    - Verify transition enforcement to HASH_MASK string format
    - Restore the original preserved metadata state after completion
    """
    test_suite_cfg = test_config["test_suite"]
    table_name = test_suite_cfg["table_name"]
    columns_config = test_suite_cfg["columns_config"]

    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + " [POLICY ENGINE] Starting Dynamic Policy Update Test " + "-" * 25)
    test_logger.info(f"Target Table: {table_name}")

    target_column = "email_clean"
    target_role = UserRole.ANALYST

    # Table need to be registered in Metadata Store
    sql_get_table_id = "SELECT table_id FROM tables_metadata WHERE table_name = :table_name;"
    table_rows = pg_client.execute_query(sql_get_table_id, {"table_name": table_name})
    assert len(table_rows) > 0, f"Infrastructure Error: Table '{table_name}' not registered in Metadata Store."
    table_id = table_rows[0]["table_id"]

    # Initialize
    spark_session.range(1, 10).repartition(1).count()
    data_masker = DataMasker()
    pipeline = PolicyEngine(spark_session, pg_client, data_masker, test_config)
    column_names_extract = [col_info["column_name"] for col_info in columns_config]

    # 1. Get initial state of column
    sql_get_original_state = """
        SELECT sensitivity_level FROM columns_metadata
        WHERE table_id = :table_id AND column_name = :column_name;
    """
    original_state_rows = pg_client.execute_query(sql_get_original_state, {
        "table_id": table_id, "column_name": target_column
    })
    assert len(original_state_rows) > 0, f"Infrastructure Error: Column '{target_column}' not found in Metadata Store."
    original_sensitivity_level = original_state_rows[0]["sensitivity_level"]
    test_logger.info(f"Initial metadata state: '{original_sensitivity_level}'")

    try:
        # 2. Set Column 'email_clean' to MEDIUM - NULLIFY_MASK
        test_logger.info("Setting baseline column metadata : EMAIL -> MEDIUM...")
        sql_set_level = """
                        UPDATE columns_metadata
                        SET sensitivity_level = :level
                        WHERE table_id = :table_id \
                          AND column_name = :column_name; \
                        """
        pg_client.execute_non_query(sql_set_level, {
            "level": SensitivityLevel.MEDIUM.value,
            "table_id": table_id,
            "column_name": target_column
        })

        df_baseline = pipeline.execute_secure_pipeline(
            table_name=table_name,
            selected_columns=column_names_extract,
            user_role=target_role
        )[0]
        baseline_value = df_baseline.first()[target_column]

        test_logger.info(f"   [BASELINE Check] Role: {target_role.name} | Column: '{target_column}' | Expected Rule: NULLIFY_MASK")
        test_logger.info(f"   [BASELINE Value] Actual Spark Value: {baseline_value}")
        assert baseline_value is None, f"Baseline Setup Failure: Expected NULL value, but got '{baseline_value}'"

        # spark_session.catalog.clearCache()
        # 3. Update Column 'email_clean' to HIGH - HASH_MASK
        test_logger.info("Updating column metadata: EMAIL -> HIGH...")

        # Latency from Metadata Store update to the next Policy Engine Query
        start_perf_time = time.perf_counter()

        pg_client.execute_non_query(sql_set_level, {
            "level": SensitivityLevel.HIGH.value,
            "table_id": table_id,
            "column_name": target_column
        })

        df_escalated = pipeline.execute_secure_pipeline(
            table_name=table_name,
            selected_columns=[],
            user_role=target_role
        )[0]
        df_escalated.show(truncate=False)


        total_latency_seconds = time.perf_counter() - start_perf_time
        escalated_row = df_escalated.first()
        escalated_value = escalated_row[target_column]

        test_logger.info(f"   [Update Check] Role: {target_role.name} | Column: '{target_column}' | Expected Rule: HASH_MASK")
        test_logger.info(f"   [Update Value] Actual Spark Value: {escalated_value}")

        # 4. Metrics report
        test_logger.info("\n" + "=" * 23 + " [POLICY ENGINE] DYNAMIC POLICY PROPAGATION BENCHMARK " + "=" * 23)
        test_logger.info(f"   Target Audit Column            : {target_column}")
        test_logger.info(f"   Transition Path Enforcement   : {SensitivityLevel.MEDIUM.value} (NULLIFY) -> {SensitivityLevel.HIGH.value} (HASH)")
        test_logger.info(f"   Measured Policy Latency Window : {total_latency_seconds:.4f} s (Target: < 1.0s)")
        test_logger.info("=" * 82 + "\n")

        assert total_latency_seconds < 1.0, \
            f"Latency: Hot policy update propagation took {total_latency_seconds:.4f}s, exceeding maximum 1.0s barrier."

        assert escalated_value is not None, \
            f"Policy Sync Failure: Engine still enforcing stale baseline rule (NULLIFY_MASK) after hot update."
        assert len(str(escalated_value)) == 64, \
            f"Format Mismatch: Policy updated but value is not a valid SHA-256 hash array. Got: {escalated_value}"

    finally:
        test_logger.info(f"Restoring original metadata state: '{original_sensitivity_level}'...")
        sql_restore_state = """
                            UPDATE columns_metadata
                            SET sensitivity_level = :level
                            WHERE table_id = :table_id \
                              AND column_name = :column_name; \
                            """
        pg_client.execute_non_query(sql_restore_state, {
            "level": original_sensitivity_level,
            "table_id": table_id,
            "column_name": target_column
        })
        spark_session.catalog.clearCache()
        test_logger.info("Restore initial state of database successfully.")





