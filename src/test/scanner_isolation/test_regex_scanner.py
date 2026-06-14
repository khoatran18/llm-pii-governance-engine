import logging
import os

import pytest

from src.config.logging import setup_logging
from src.core.dtos.enums import SensitivityTag, DetectionMethod, RegexStatus
from src.modules.ai_governance.regex_scanner import calculate_regex_confidence_score
from src.modules.ai_governance.table_sampler import IcebergTableSampler
from src.modules.ai_governance.utils import get_table_fqn

setup_logging()
test_logger = logging.getLogger("test")

def test_regex_scanner(spark_session, test_config):
    """
    Unit test for the Regex Scanner component.
    - Extracts sampled data from Iceberg tables using the Spark sampler.
    - Computes regex patterns compliance and confidence metrics.
    - Validates calculated confidence scores against deterministic thresholds.
    """
    test_data_config = test_config["data_test"]
    table_name = test_data_config["table_name"]
    columns_config = test_data_config["columns_config"]
    total_rows = test_data_config["total_rows"]

    threshold = test_config["governance"]["confidence_threshold"]
    table_fqn = get_table_fqn(test_config, table_name)
    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + f"[SCANNER ISOLATION] Starting Regex Scanner validation suite" + "-" * 25)
    test_logger.info(f"Table FQN: {table_fqn}, threshold: {threshold}, total_rows: {total_rows}")

    # 1. Extract data from Iceberg table
    sampler = IcebergTableSampler(spark_session, test_config)
    try:
        extracted_data = sampler.extract_table_schema_and_sampler(table_fqn, sample_size=total_rows)
    except Exception as e:
        pytest.fail(f"Failed to extract data from table: {table_fqn} by Sparksampler.")

    # 2. Map data to column names
    spark_data_map = {col["column_name"]: col["sample_data"] for col in extracted_data}

    # 3. Iter through config and validate regex confidence scores
    for col in columns_config:
        col_name = col["column_name"]
        expected_tag = col["sensitivity_tag"]
        expected_regex_status = col["regex_status"]
        expected_regex_score = col["expected_regex_score"]

        sample_data = spark_data_map[col_name]

        # 4. Compute Regex Confidence Score
        result = calculate_regex_confidence_score(
            column_name=col_name,
            sample_data=sample_data,
            threshold=threshold
        )

        actual_status = result["regex_status"]
        raw_scores = result["raw_scores"]
        actual_candidates = result["regex_candidates"]

        if expected_tag != SensitivityTag.NONE:
            actual_score = raw_scores.get(expected_tag, 0.0)

        test_logger.info(f"[Verify] Field: {col_name:32s} | Target PII: {expected_tag:20s} | Expected Status: {expected_regex_status:15s} | Actual: {actual_status}")

        # 5. Assert
        # Regex Status
        assert actual_status == expected_regex_status, f"Regex status for column {col_name} is incorrect: expected {expected_regex_status}, got {actual_status}"

        # Regex Confidence Score
        assert actual_score == expected_regex_score, f"Regex confidence score for column {col_name} is incorrect: expected {expected_regex_score}, got {actual_score}"

        # Regex Tag if regex_status is SUCCESS
        if expected_regex_status == RegexStatus.SUCCESS:
            assert expected_tag in actual_candidates, f"Regex tag for column {col_name} is incorrect: expected {expected_tag}, got {actual_candidates}"

    test_logger.info("\n" + "-" * 25 + " [SCANNER ISOLATION] REGEX SCANNER SUMMARY REPORT " + "-" * 25)
    test_logger.info(f"Target Table Checked             : {table_name}")
    test_logger.info(f"Total Columns Verified           : {len(columns_config)}")
    test_logger.info("-" * 80 + "\n")

    test_logger.info("All tests passed!")

# pytest src/test/unit/test_regex_scanner.py -v -s

