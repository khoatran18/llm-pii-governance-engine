import logging
import random
import time

import pytest

from src.config.logging import setup_logging
from src.core.dtos.enums import UserRole
from src.core.spark.spark_builder import get_spark_iceberg_jdbc
from src.modules.ai_governance.utils import get_table_fqn
from src.modules.policy_engine.policy_engine_main import policy_engine_main
from src.test.conftest import spark_session

setup_logging()
test_logger = logging.getLogger("test")

def test_policy_engine_overhead(test_config):
    """
    Measure the performance overhead of the Policy Engine.
    Evaluates the full end-to-end lifecycle including config parsing, database connection, and SparkSession instantiation.
    Supports 4 dynamic execution strategies to manipulate caching advantages and analyze OS Page Cache impact.
    """

    # 1. "NORMAL_FIRST_POLICY_SHUFFLE"  : Normal runs first, then the 3 roles are shuffled.
    # 2. "POLICY_SHUFFLE_NORMAL_LAST"   : The 3 roles are shuffled first, then Normal runs last.
    # 3. "PURE_SHUFFLE_ALL"             : All 4 execution types are completely shuffled together.
    # 4. "EXPLICIT_MANUAL_ORDER"        : Follows a rigid custom sequence defined in MANUAL_SEQUENCE.
    EXECUTION_STRATEGY = "NORMAL_FIRST_POLICY_SHUFFLE"

    # Only applicable if EXECUTION_STRATEGY is EXPLICIT_MANUAL_ORDER
    MANUAL_SEQUENCE = ["NORMAL", "ANALYST", "AUDITOR", "ADMIN"]

    test_data_config = test_config["test_suite"]
    table_name = test_data_config["table_name"]
    table_fqn = get_table_fqn(test_config, table_name)
    max_overhead_percentages = test_data_config["test_performance"]["policy_engine_overhead_percentages"]

    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + f"[PERFORMANCE] Starting Policy Engine overhead benchmark with strategy: {EXECUTION_STRATEGY}" + "-" * 25)

    # Storage for raw latency execution metrics
    normal_durations = []
    secure_durations_by_role = {
        UserRole.ADMIN: [],
        UserRole.ANALYST: [],
        UserRole.AUDITOR: []
    }

    warmup_metrics = {}
    NUM_CYCLES = 5

    # Encapsulated logic for executing standard, unmasked queries
    def run_normal_select(warm_up=False):
        start_normal = time.perf_counter()
        spark_session = get_spark_iceberg_jdbc(test_config)
        df_normal = spark_session.read.format("iceberg").option("inferSchema", "false").load(table_fqn)
        _ = df_normal.count()
        dur_normal = time.perf_counter() - start_normal
        if not warm_up:
            normal_durations.append(dur_normal)
        spark_session.stop()
        time.sleep(0.5)
        return dur_normal

    # Encapsulated logic for executing role-based, dynamically masked queries
    def run_secure_select(role: UserRole, warm_up=False):
        start_secure = time.perf_counter()
        df_policy_engine = policy_engine_main(table_name, None, role, test_config)
        _ = df_policy_engine[0].count()
        dur_secure = time.perf_counter() - start_secure
        if not warm_up:
            secure_durations_by_role[role].append(dur_secure)
        if df_policy_engine and len(df_policy_engine) > 0:
            df_policy_engine[0].sparkSession.stop()
        time.sleep(0.5)
        return dur_secure

    # Warm up phase
    test_logger.info("Starting infrastructure warm-up phase...")

    dur_w_normal = run_normal_select(warm_up=True)
    warmup_metrics["NORMAL"] = dur_w_normal
    test_logger.info(f"[Warm Up] Normal Select complete. Latency: {dur_w_normal:.4f} seconds")

    for role in [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]:
        dur_w_role = run_secure_select(role, warm_up=True)
        warmup_metrics[role.name] = dur_w_role
        test_logger.info(f"[Warm Up] Policy Engine ({role.name}) complete. Latency: {dur_w_role:.4f} seconds")

    # Main execution phase
    test_logger.info(f"Starting lifecycle benchmark across {NUM_CYCLES} cycles...")

    for cycle in range(1, NUM_CYCLES + 1):
        test_logger.info(f"\n" + "=" * 20 + f" MATRIX CYCLE {cycle}/{NUM_CYCLES} " + "=" * 20)

        # Base tasks declaration
        normal_task = {"type": "NORMAL", "target": None}
        policy_tasks = [
            {"type": "SECURE", "target": UserRole.ADMIN},
            {"type": "SECURE", "target": UserRole.ANALYST},
            {"type": "SECURE", "target": UserRole.AUDITOR}
        ]

        execution_pool = []

        # Strategy 1: Normal execution dons the cold-start, followed by a randomized role execution path
        if EXECUTION_STRATEGY == "NORMAL_FIRST_POLICY_SHUFFLE":
            random.shuffle(policy_tasks)
            execution_pool = [normal_task] + policy_tasks

        # Strategy 2: Randomized role pool triggers first, forcing Normal select to pull from cache last
        elif EXECUTION_STRATEGY == "POLICY_SHUFFLE_NORMAL_LAST":
            random.shuffle(policy_tasks)
            execution_pool = policy_tasks + [normal_task]

        # Strategy 3: Complete pool randomization across all four baseline platforms
        elif EXECUTION_STRATEGY == "PURE_SHUFFLE_ALL":
            execution_pool = [normal_task] + policy_tasks
            random.shuffle(execution_pool)

        # Strategy 4: Explicit hard-coded sequence execution based on string matching arrays
        elif EXECUTION_STRATEGY == "EXPLICIT_MANUAL_ORDER":
            all_tasks_map = {
                "NORMAL": normal_task,
                "ADMIN": policy_tasks[0],
                "ANALYST": policy_tasks[1],
                "AUDITOR": policy_tasks[2]
            }
            if len(MANUAL_SEQUENCE) != 4 or set(MANUAL_SEQUENCE) != set(all_tasks_map.keys()):
                pytest.fail("Explicit sequence pool matrix must contain exactly 4 distinct valid targets.")
            execution_pool = [all_tasks_map[key] for key in MANUAL_SEQUENCE]

        else:
            pytest.fail(f"Invalid benchmark strategy plan configuration declared: {EXECUTION_STRATEGY}")

        # Log out the evaluation sequence for audit trails
        sequence_names = [task["type"] if task["type"] == "NORMAL" else f"SECURE({task['target'].name})" for task in
                          execution_pool]
        test_logger.info(f"Execution order sequence for Cycle {cycle}: {' -> '.join(sequence_names)}")

        # Execute targets sequentially based on the designated strategy execution sequence
        for step_idx, task in enumerate(execution_pool, start=1):
            if task["type"] == "NORMAL":
                test_logger.info(f"[Cycle {cycle} - Step {step_idx}/4] Normal select processing...")
                dur = run_normal_select()
                test_logger.info(f"   Result: Normal select took {dur:.4f} seconds")
            else:
                target_role = task["target"]
                test_logger.info(
                    f"[Cycle {cycle} - Step {step_idx}/4] Policy Engine ({target_role.name}) processing...")
                dur = run_secure_select(target_role)
                test_logger.info(f"   Result: Policy Engine ({target_role.name}) took {dur:.4f} seconds")

    # Metrics report
    avg_normal = sum(normal_durations) / len(normal_durations)

    # Output raw warm-up metrics
    test_logger.info("\n" + "-" * 25 + " WARM-UP EXECUTION METRICS " + "-" * 25)
    for engine_key, duration_val in warmup_metrics.items():
        test_logger.info(f"Warm-up Target: {engine_key:<15} | Latency: {duration_val:.4f} s")
    test_logger.info("-" * 77)

    # Output detailed run-by-run execution matrix
    test_logger.info("\n" + "-" * 25 + " DETAILED RUN-BY-RUN MATRIX " + "-" * 25)
    test_logger.info(
        f"{'Iteration':<10} | {'Normal Duration':<18} | {'Admin Duration':<18} | {'Analyst Duration':<18} | {'Auditor Duration':<18}")
    test_logger.info("-" * 96)

    for idx in range(NUM_CYCLES):
        test_logger.info(
            f"Run {idx + 1:<6} | "
            f"{normal_durations[idx]:<16.4f} s | "
            f"{secure_durations_by_role[UserRole.ADMIN][idx]:<16.4f} s | "
            f"{secure_durations_by_role[UserRole.ANALYST][idx]:<16.4f} s | "
            f"{secure_durations_by_role[UserRole.AUDITOR][idx]:<16.4f} s"
        )
    test_logger.info("-" * 96)

    # 1. Gather all secure durations across all 3 roles to compute the total global average (15 runs)
    all_secure_runs = []
    for role in [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]:
        all_secure_runs.extend(secure_durations_by_role[role])
    avg_secure_all_roles = sum(all_secure_runs) / len(all_secure_runs)
    total_global_overhead = (avg_secure_all_roles - avg_normal) / avg_normal * 100.0

    # Compute and assert final SLA parameters
    test_logger.info("\n" + "=" * 25 + " [PERFORMANCE] SPRINT POLICY ENGINE MATRIX " + "=" * 25)
    test_logger.info(f"Selected Strategy Strategy Plan   : {EXECUTION_STRATEGY}")
    test_logger.info(f"Baseline Normal Select Average   : {avg_normal:.4f} s")
    test_logger.info(f"Global Combined Secure Average   : {avg_secure_all_roles:.4f} s (All 15 secure runs total)")
    test_logger.info(f"Global Combined System Overhead  : {total_global_overhead:.2f}% (Threshold: < {max_overhead_percentages}%)")

    for role in [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]:
        role_durations = secure_durations_by_role[role]
        avg_secure_role = sum(role_durations) / len(role_durations)
        role_overhead = (avg_secure_role - avg_normal) / avg_normal * 100.0

        test_logger.info("-" * 87)
        test_logger.info(f"Role Targeted Assessment         : {role.name}")
        test_logger.info(f"   Average Secure Duration       : {avg_secure_role:.4f} s")
        test_logger.info(
            f"   Computed System Overhead Cost : {role_overhead:.2f}% (Threshold: < {max_overhead_percentages}%)")

        assert role_overhead < max_overhead_percentages, \
            f"Performance breached for role {role.name}. Calculated overhead {role_overhead:.2f}% exceeded threshold {max_overhead_percentages}%"

    test_logger.info("=" * 87 + "\n")