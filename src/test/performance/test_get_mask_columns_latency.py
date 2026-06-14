import logging
import time
import random
import pytest

from src.core.dtos.enums import UserRole
from src.core.postgres.postgres_client import PostgresClient
from src.modules.ai_governance.utils import get_table_fqn
from src.modules.policy_engine.pipeline import PolicyEngine
from src.modules.policy_engine.data_masker import DataMasker

test_logger = logging.getLogger("test")

def test_policy_determination_latency(spark_session, pg_client, test_config):
    """
    Measure policy determination lookup latency.
    - Dynamically extracts columns using Spark BEFORE starting the execution timer.
    - Strictly measures only the database policy lookup and metadata rules mapping.
    - Completely excludes Spark metadata/catalog parsing duration from the SLA metric.
    """
    test_data_config = test_config["data_test"]
    table_name = test_data_config["table_name"]
    table_fqn = get_table_fqn(test_config, table_name)

    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + f"[PERFORMANCE] Starting Get Mask Columns latency benchmark" + "-" * 25)

    max_latency_ms = float(test_config["test_info"]["test_performance"]["get_mask_columns_latency_ms"])
    NUM_CYCLES = 5

    # Initialize production component instances without modifying their source code
    data_masker = DataMasker()
    pipeline = PolicyEngine(spark_session, pg_client, data_masker, test_config)

    # Storage for raw latency metrics
    latency_records_by_role = {
        UserRole.ADMIN: [],
        UserRole.ANALYST: [],
        UserRole.AUDITOR: []
    }

    warmup_metrics = {}

    # Encapsulated latency determination block
    def calculate_determination_time(role: UserRole, current_cycle=0, step=0, warm_up=False):
        # 1. Fetch table columns via Spark
        df_lazy = spark_session.read.format("iceberg").option("inferSchema", "false").load(table_fqn)
        actual_columns = df_lazy.columns

        # 2. Start timer (not include Spark Load)
        start_time = time.perf_counter()

        # 3. Force new connection
        fresh_pg_client = PostgresClient(test_config)
        transient_pipeline = PolicyEngine(spark_session, fresh_pg_client, data_masker, test_config)

        # 4. Call the production function to fetch raw rules from Postgres
        policies = transient_pipeline._get_masking_policies(
            table_name=table_name,
            user_role=role,
            target_columns=actual_columns
        )

        # 4. Construct the final matrix map within the application memory
        policy_map = {row['column_name']: row['masking_rule'] for row in policies}

        schema_policy_matrix = {}
        for col in actual_columns:
            rule = policy_map.get(col, "NONE")
            schema_policy_matrix[col] = rule if rule and rule != "NONE" else "CLEAR_TEXT"

        # End timer and calculate latency
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Explicitly close or dispose of the fresh client to clean up system sockets
        fresh_pg_client.disconnect()

        if current_cycle == 1 and step == 1 and not warm_up:
            test_logger.info(f"   [Schema Policy Matrix Sample for {role.name}]: {schema_policy_matrix}")
        if not warm_up:
            latency_records_by_role[role].append(elapsed_ms)

        return elapsed_ms

    # Warm up
    test_logger.info("Starting database driver warm-up phase...")
    for role in [UserRole.ANALYST, UserRole.AUDITOR, UserRole.ADMIN]:
        dur_w = calculate_determination_time(role, warm_up=True)
        warmup_metrics["DRIVER_WARMUP"] = dur_w
        test_logger.info(f"[Warm Up] Driver initialization complete. Latency: {dur_w:.2f} ms")

    # Main measure logic
    test_logger.info(f"Starting shuffled policy engine latency benchmark across {NUM_CYCLES} cycles...")

    for cycle in range(1, NUM_CYCLES + 1):
        test_logger.info(f"\n" + "=" * 20 + f" LATENCY CYCLE {cycle}/{NUM_CYCLES} " + "=" * 20)

        role_pool = [UserRole.ANALYST, UserRole.AUDITOR, UserRole.ADMIN]
        random.shuffle(role_pool)

        sequence_names = [role.name for role in role_pool]
        test_logger.info(f"Execution order sequence for Cycle {cycle}: {' -> '.join(sequence_names)}")

        for step_idx, role in enumerate(role_pool, start=1):
            test_logger.info(f"[Cycle {cycle} - Step {step_idx}/3] Evaluating latency for role: {role.name}")
            dur_ms = calculate_determination_time(role, current_cycle=cycle, step=step_idx)
            test_logger.info(f"   Result: Strict Policy determination took {dur_ms:.2f} ms")
            time.sleep(0.1)

    # Metrics report
    test_logger.info("\n" + "-" * 25 + " WARM-UP LATENCY METRICS " + "-" * 25)
    for role_key, latency_val in warmup_metrics.items():
        test_logger.info(f"Warm-up Target: {role_key:<15} | Latency: {latency_val:.2f} ms")
    test_logger.info("-" * 77)

    test_logger.info("\n" + "-" * 25 + " DETAILED RUN-BY-RUN LATENCY " + "-" * 25)
    test_logger.info(f"{'Iteration':<10} | {'Admin Latency':<18} | {'Analyst Latency':<18} | {'Auditor Latency':<18}")
    test_logger.info("-" * 72)
    for idx in range(NUM_CYCLES):
        test_logger.info(
            f"Run {idx + 1:<6} | "
            f"{latency_records_by_role[UserRole.ADMIN][idx]:<15.2f} ms | "
            f"{latency_records_by_role[UserRole.ANALYST][idx]:<15.2f} ms | "
            f"{latency_records_by_role[UserRole.AUDITOR][idx]:<15.2f} ms"
        )
    test_logger.info("-" * 72)

    # Gather all runs to calculate the global average latency
    all_latency_runs = []
    for role in [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]:
        all_latency_runs.extend(latency_records_by_role[role])
    avg_all_roles_latency = sum(all_latency_runs) / len(all_latency_runs)

    test_logger.info("\n" + "=" * 25 + " [PERFORMANCE] GET MASK COLUMNS LATENCY MATRIX " + "=" * 25)
    test_logger.info(f"Required Threshold Maximum  : {max_latency_ms:.2f} ms")
    test_logger.info(f"Global Aggregated Policy Latency: {avg_all_roles_latency:.2f} ms (All 15 runs total)")

    for role in [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]:
        role_records = latency_records_by_role[role]
        avg_latency_ms = sum(role_records) / len(role_records)

        test_logger.info("-" * 79)
        test_logger.info(f"Role Targeted Assessment         : {role.name}")
        test_logger.info(f"   Average Policy Lookup Latency : {avg_latency_ms:.2f} ms")

        assert avg_latency_ms < max_latency_ms, \
            f"SLA 3 breached for role {role.name}. Average lookup latency {avg_latency_ms:.2f} ms exceeded threshold {max_latency_ms} ms"

    test_logger.info("=" * 79 + "\n")