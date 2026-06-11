import glob
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from src.config.loader import load_config
from src.config.logging import setup_logging
from src.core.dtos.enums import RegexStatus, SensitivityTag, DetectionMethod, DetectionReason
from src.core.dtos.models import TableLLMScanRequest, ColumnScanInput, SingleColumnLLMOutput, ColumnScanResult

setup_logging()
logger = logging.getLogger(__name__)
llm_logger = logging.getLogger("llm_io")
regex_logger = logging.getLogger("regex_output")
test_logger = logging.getLogger("test")

def get_all_table_name(config):
    """
    Get all CSV files in the specified folder
    """
    # Table name = CSV file name
    csv_folder = f"{config['spark']['csv_folder']}"
    # all_csv_files = glob.glob(csv_folder)
    container_name = config["spark"]["master_container_name"]

    # Exec spark container to get all CSV files name
    cmd = ["docker", "exec", container_name, "sh", "-c", f"ls {csv_folder}"]
    try:
        logger.info("Getting all CSV files in the specified folder...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stdout = result.stdout.strip()
        if not stdout:
            logger.error("No CSV files found in the specified folder.")
            return []
        all_csv_files = stdout.split('\n')
        logger.info(f"Found {len(all_csv_files)} CSV files in the specified folder.")
        table_names = [os.path.splitext(os.path.basename(f))[0] for f in all_csv_files]
        return table_names
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get all CSV files in the specified folder: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return []


def get_table_fqn(config, table_name):
    db_name = config["spark"]["iceberg_db_name"]
    full_table_path = f"{config['spark']['iceberg_catalog_name']}.{db_name}.{table_name}"
    return full_table_path

def get_all_table_fqn(config):
    """
    Get all table fully qualified names in the format of catalog.db.table
    """
    table_names = get_all_table_name(config)
    table_names = [Path(csv_path).stem.lower() for csv_path in table_names]

    full_table_paths = [get_table_fqn(config, table_name) for table_name in table_names]

    return full_table_paths

def build_llm_request_payload(
        table_name: str,
        regex_outputs: List[Dict[str, Any]],
) -> TableLLMScanRequest:
    """
    Create a TableLLMScanRequest object from Regex outputs to be sent to LLM
    """
    determined_list = []
    undetermined_list = []

    # Group columns by status
    for col in regex_outputs:
        col_input = ColumnScanInput(
            column_name=col["column_name"],
            regex_candidates=col["regex_candidates"],
            raw_scores=col["raw_scores"],
            sample_data=col["sample_data"],
            regex_status=col["regex_status"],
        )
        status = col["regex_status"]
        if status == RegexStatus.SUCCESS.value:
            determined_list.append(col_input)
        else:
            undetermined_list.append(col_input)

    return TableLLMScanRequest(
        table_name=table_name,
        determined_columns=determined_list,
        undetermined_columns=undetermined_list,
    )

def regex_reason(all_detected_tags: list):
    regex_tag_string = ""
    if all_detected_tags:
        regex_tag_string = " - Regex tags detection: " + ", ".join([f"{tag}:{score}" for tag, score in all_detected_tags])
    return regex_tag_string


def arbitrate_hybrid_results(
        column_name: str,
        regex_info: Dict[str, Any],
        llm_output: SingleColumnLLMOutput,
        confidence_score_threshold: float = 0.7
) -> ColumnScanResult:
    """
    Get a sensible tag for a column with confidence score < threshold from LLM output and Regex output
    """
    regex_candidates = regex_info["regex_candidates"]
    raw_scores = regex_info["raw_scores"]
    regex_status = regex_info["regex_status"]
    all_detected_tags = regex_info["all_detected_tags"]

    # Get the best tag from Regex
    best_regex_tag = regex_candidates[0] if regex_candidates else SensitivityTag.NONE
    best_regex_score = raw_scores.get(best_regex_tag, 0.0) if best_regex_tag != SensitivityTag.NONE else 0.0

    # Get tag from LLM output
    if llm_output:
        llm_tag = llm_output.suggested_tag
        llm_is_pii = llm_output.is_pii

    final_tag = SensitivityTag.NONE
    final_score = 0.0
    final_method = DetectionMethod.REGEX
    final_reason = DetectionReason.FULLY_NONE
    final_is_pii = False
    llm_reason = ""

    # If Regex returns a PII tag with a confidence score high enough, use it
    if regex_status == RegexStatus.SUCCESS.value:
        final_tag = best_regex_tag
        final_score = best_regex_score
        final_method = DetectionMethod.REGEX
        final_reason = DetectionReason.REGEX
        final_is_pii = True
    else:
        # Regex returns PII tag(s) with low confidence score, use LLM output if available
        if best_regex_tag != SensitivityTag.NONE:
            # LLM returns not PII, returns no PII tag
            if not llm_is_pii:
                final_tag = SensitivityTag.NONE
                final_score = llm_output.confidence_score
                final_method = DetectionMethod.HYBRID
                final_reason = DetectionReason.AMBIGUOUS_NONE
                final_is_pii = False
                llm_reason = " - LLM reason: " + llm_output.reason
            # If LLM returns PII, use Regex
            else:
                final_tag = best_regex_tag
                final_score = best_regex_score
                final_method = DetectionMethod.HYBRID
                final_reason = DetectionReason.AMBIGUOUS_PII
                final_is_pii = True
                llm_reason = " - LLM reason: " + llm_output.reason
        # Regex returns no PII tags
        else:
            if llm_is_pii and llm_tag != SensitivityTag.NONE:
                final_tag = llm_tag
                final_score = llm_output.confidence_score
                final_method = DetectionMethod.LLM
                final_reason = DetectionReason.LLM
                final_is_pii = True
                llm_reason = " - LLM reason: " + llm_output.reason
            else:
                final_tag = SensitivityTag.NONE
                final_score = 1.0
                final_method = DetectionMethod.HYBRID
                final_reason = DetectionReason.FULLY_NONE
                final_is_pii = False
                llm_reason = " - LLM reason: " + llm_output.reason

    final_reason = final_reason + regex_reason(all_detected_tags) + llm_reason
    final_level = final_tag.sensitivity_level

    test_logger.info("----------------------------------------")
    test_logger.info(f"Column: {column_name}, Final Tag: {final_tag}, Final Score: {final_score}, Final Method: {final_method}, Final Reason: {final_reason}")

    return ColumnScanResult(
        column_name = column_name,
        is_pii = final_is_pii,
        sensitivity_tag = final_tag,
        confidence_score = final_score,
        detection_method = final_method,
        reason = final_reason,
        sensitivity_level = final_level
    )



if __name__ == "__main__":
    config = load_config()
    get_all_table_name(config)


