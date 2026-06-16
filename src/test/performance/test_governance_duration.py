import logging
import time

from src.config.logging import setup_logging
from src.modules.ai_governance.ai_governance_main import ai_governance_main

setup_logging()
test_logger = logging.getLogger("test")

def test_ai_governance_pipeline_duration(test_config):
    test_data_config = test_config["test_suite"]
    table_name = test_data_config["table_name"]

    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + "[PERFORMANCE] Starting AI Governance Pipeline latency benchmark" + "-" * 25)
    test_logger.info(f"Target Table: {table_name}")

    max_duration_seconds = test_data_config["test_performance"]["ai_governance_pipeline_duration_seconds"]

    # Start timer
    start_perf_time = time.perf_counter()

    ai_governance_main(table_name, test_config)
    time.sleep(0.5)

    # End timer
    total_perf_time = time.perf_counter() - start_perf_time

    test_logger.info("\n" + "=" * 25 + " [PERFORMANCE] AI GOVERNANCE PIPELINE DURATION BENCHMARK RESULT " + "=" * 25)
    test_logger.info(f"   Target Table Name              : {table_name}")
    test_logger.info(f"   Measured Execution Pipeline Time: {total_perf_time:.4f} s")
    test_logger.info(f"   Required SLA Threshold Maximum  : {max_duration_seconds:.4f} s")
    test_logger.info("=" * 82 + "\n")

    assert total_perf_time <= max_duration_seconds, \
        f"AI Governance SLA breached. Pipeline took {total_perf_time:.4f}s, exceeding maximum allowed threshold of {max_duration_seconds:.4f}s"
