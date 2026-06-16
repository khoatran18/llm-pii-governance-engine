import logging
import time
from src.config.logging import setup_logging
from src.modules.ai_governance.utils import get_table_fqn

setup_logging()
test_logger = logging.getLogger("test")


def test_pure_spark_iceberg_cold_start_latency(spark_session, test_config):
    """
    PERFORMANCE BENCHMARK: Measures pure Spark + Iceberg + MinIO I/O latency.
    This test completely bypasses the Policy Engine and DataMasker to isolate
    the baseline Cold Start infrastructure overhead.
    """
    test_suite_cfg = test_config["test_suite"]
    table_name = test_suite_cfg["table_name"]

    test_logger.info("\n" + "=" * 80)
    test_logger.info("-" * 20 + " [BENCHMARK] Starting Pure Spark Iceberg Read Test " + "-" * 20)
    test_logger.info(f"Target Table: {table_name}")

    # Resolve the fully qualified name (e.g., iceberg.iceberg_data.test_suite)
    table_fqn = get_table_fqn(test_config, table_name)

    # START TIMER: Measures pure infrastructure initialization and data pull
    start_time = time.perf_counter()

    # Pure Spark read execution context without any dataframe transformations
    df_pure = spark_session.read.format("iceberg").load(table_fqn)

    # Trigger an action to force physical file scanning and HTTP handshake with MinIO
    df_pure.show(truncate=False)

    # STOP TIMER
    execution_duration = time.perf_counter() - start_time
    first_row = df_pure.first()

    test_logger.info("\n" + "=" * 24 + " [BENCHMARK] PURE SPARK ICEBERG LATENCY RESULT " + "=" * 24)
    test_logger.info(f"   Target Table FQN            : {table_fqn}")
    test_logger.info(f"   Pure Read Execution Duration: {execution_duration:.4f} s")
    test_logger.info("=" * 82 + "\n")

    # Basic assertion just to verify data is readable
    assert first_row is not None, "Infrastructure Error: Failed to read raw data from Lakehouse."