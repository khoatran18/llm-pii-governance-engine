import logging
import random
import re

import pytest

from src.config.logging import setup_logging
from src.core.dtos.enums import RegexStatus, SensitivityTag, DetectionMethod
from src.core.dtos.models import ColumnMetadata, TableLLMScanRequest, TableLLMScanResponse, SingleColumnLLMOutput
from src.modules.ai_governance.regex_scanner import calculate_regex_confidence_score, RegexPattern
from src.modules.ai_governance.table_sampler import IcebergTableSampler
from src.modules.ai_governance.utils import get_table_fqn, build_llm_request_payload

"""
If PII Column (Can be detected by Regex but not enough confidence score) have too much noise,
force sample data to have valid distribution >= threshold.
"""

setup_logging()
test_logger = logging.getLogger("test")

@pytest.mark.parametrize("run_attempt", [1, 2, 3])
def test_lm_scan(spark_session, test_config, llm_scanner, run_attempt):
    """
    Unit test for the LLM Semantic Scanner component.
    - Implements stratified sampling for hybrid columns to evaluate noisy environments.
    - Formulates complete structured semantic prompt context structures.
    - Validates the LLM classification results against target classifications.
    """
    test_data_config = test_config["test_suite"]
    table_name = test_data_config["table_name"]
    columns_config = test_data_config["columns_config"]
    total_rows = test_data_config["total_rows"]
    threshold = test_config["governance"]["confidence_threshold"]
    table_fqn = get_table_fqn(test_config, table_name)

    regex_patterns_map = {
        "RESIDENT_ID": RegexPattern.RESIDENT_ID,
        "PHONE": RegexPattern.PHONE,
        "EMAIL": RegexPattern.EMAIL,
        "HEALTH_INSURANCE_ID": RegexPattern.HEALTH_INSURANCE_ID
    }

    regex_sample_size = total_rows
    llm_sample_size = test_config["governance"]["llm_sample_size"]
    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + f"[SCANNER ISOLATION] Starting LLM Scanner verification sprint - Attempt {run_attempt}" + "-" * 25)
    test_logger.info(f"Target FQN: {table_fqn} | Regex Size: {regex_sample_size} | LLM Size: {llm_sample_size}")

    # 1. Extract data from Iceberg table
    sampler = IcebergTableSampler(spark_session, test_config)
    iceberg_table_regex = sampler.extract_table_schema_and_sampler(table_fqn, regex_sample_size)

    # 2. Stratified sampling for hybrid columns
    llm_sample_map = {}
    for col in iceberg_table_regex:
        col_name = col["column_name"]
        full_data = col["sample_data"]

        col_yaml_config = next((c for c in columns_config if c["column_name"] == col_name), {})
        expected_tag = col_yaml_config.get("sensitivity_tag", "NONE")
        detection_method = col_yaml_config.get("detection_method", "REGEX")

        if detection_method == DetectionMethod.HYBRID.value and expected_tag != SensitivityTag.NONE.value:
            pattern_str = regex_patterns_map[expected_tag]
            compiled_regex = re.compile(pattern_str)

            # Split into valid and invalid rows
            valid_rows = [row for row in full_data if compiled_regex.search(str(row).strip())]
            invalid_rows = [row for row in full_data if not compiled_regex.search(str(row).strip())]
            
            # Calculate valid and invalid counts
            target_valid_count = int(llm_sample_size * threshold)
            target_invalid_count = llm_sample_size - target_valid_count
            
            # Sample valid and invalid rows
            sample_valid_rows = random.sample(valid_rows, min(len(valid_rows), target_valid_count))
            sample_invalid_rows = random.sample(invalid_rows, min(len(invalid_rows), target_invalid_count))
            
            # Combine valid, invalid rows and shuffle
            final_col_samples = sample_valid_rows + sample_invalid_rows
            random.shuffle(final_col_samples)
            llm_sample_map[col_name] = final_col_samples

            test_logger.info(f"[Stratified Sample] Column '{col_name}' forced distribution: {len(sample_valid_rows)} valid rows, {len(sample_invalid_rows)} noise rows.")
        else:
            llm_sample_map[col_name] = random.sample(full_data, min(len(full_data), llm_sample_size))


    # 3. Run Regex Scan
    regex_processed_output = []

    for col in iceberg_table_regex:
        col_name = col["column_name"]
        regex_json = calculate_regex_confidence_score(col_name, col["sample_data"], threshold=threshold)
        regex_json["sample_data"] = llm_sample_map[col_name]
        regex_processed_output.append(regex_json)

    # 4. Create LLM Payload
    llm_request_payload: TableLLMScanRequest = build_llm_request_payload(
        table_name=table_name,
        regex_outputs=regex_processed_output,
    )
    assert isinstance(llm_request_payload, TableLLMScanRequest)
    assert len(llm_request_payload.determined_columns) + len(llm_request_payload.undetermined_columns) == len(columns_config)

    # 5. Run LLM Scan
    llm_response: TableLLMScanResponse = llm_scanner.scan_table(llm_request_payload)
    assert llm_response is not None, "LLM response is None"

    llm_map_by_column = {col.column_name: col for col in llm_response.columns}

    # 6. Verify LLM Scan Results
    for col in columns_config:
        col_name = col["column_name"]
        detection_method = col["detection_method"]

        if detection_method in [DetectionMethod.HYBRID.value, DetectionMethod.LLM.value]:
            corresponding_llm: SingleColumnLLMOutput = llm_map_by_column.get(col_name)
            assert corresponding_llm is not None, f"LLM response is missing column: {col_name}"

            actual_tag = SensitivityTag(corresponding_llm.suggested_tag)
            expected_tag = SensitivityTag(col["sensitivity_tag"])
            assert actual_tag == expected_tag, f"LLM tag mismatch for column: {col_name}, expected: {expected_tag}, actual: {actual_tag}, corresponding_llm: {corresponding_llm.reason}"

            if expected_tag != SensitivityTag.NONE:
                assert corresponding_llm.is_pii is True, f"Column {col_name} is PII, but is not detected by LLM"
            else:
                assert corresponding_llm.is_pii is False, f"Column {col_name} is not PII, but is detected PII by LLM"

    test_logger.info("\n" + "-" * 25 + f" [SCANNER ISOLATION] LLM SCAN ATTEMPT {run_attempt} METRICS REPORT " + "-" * 25)
    test_logger.info(f"Attempt Status                   : SUCCESS")
    test_logger.info(f"Evaluated Target FQN             : {table_fqn}")
    test_logger.info("-" * 90 + "\n")

    test_logger.info(f"Attempt {run_attempt} passed!")

# pytest src/test/scanner_isolation/test_llm_scanner.py -v -s






