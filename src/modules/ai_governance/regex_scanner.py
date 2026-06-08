import logging
import re
from typing import List, Any, Dict

from src.config.logging import setup_logging
from src.core.dtos.enums import SensitiveTag, RegexStatus

setup_logging()
logger = logging.getLogger(__name__)
regex_logger = logging.getLogger("regex_output")

class RegexPattern:
    RESIDENT_ID = r"^0\d{11}%"

    PHONE = r"^(03|05|07|08|09)\d{8}$"

    EMAIL = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    TAX_CODE = r"^0\d{11}$"

    BANK_ACCOUNT = r"^\d{9,16}$"

def match_regex(value: str) -> List[SensitiveTag]:
    """
    Return all matched tags.
    """
    if not value or not isinstance(value, str):
        return [SensitiveTag.NONE]

    value = value.strip()
    matched_tags = []

    if re.match(RegexPattern.RESIDENT_ID, value):
        matched_tags.append(SensitiveTag.RESIDENT_ID)
    if re.match(RegexPattern.PHONE, value):
        matched_tags.append(SensitiveTag.PHONE)
    if re.match(RegexPattern.EMAIL, value):
        matched_tags.append(SensitiveTag.EMAIL)
    if re.match(RegexPattern.TAX_CODE, value):
        matched_tags.append(SensitiveTag.TAX_CODE)
    if re.match(RegexPattern.BANK_ACCOUNT, value):
        matched_tags.append(SensitiveTag.BANK_ACCOUNT)

    if not matched_tags:
        return [SensitiveTag.NONE]

    return matched_tags

def calculate_regex_confidence_score(
        column_name: str,
        sample_data: List[str],
        threshold: float = 0.7
) -> Dict[str, Any]:
    """
    Calculate confidence score for each regex tag and return the best match.
    """
    if not sample_data:
        return {
            "column_name": column_name,
            "regex_status": RegexStatus.UNDETERMINED,
            "regex_candidates": [],
            "raw_score": {}
        }

    # Init
    total_samples = len(sample_data)
    tag_counts = {
        SensitiveTag.RESIDENT_ID: 0,
        SensitiveTag.PHONE: 0,
        SensitiveTag.EMAIL: 0,
        SensitiveTag.TAX_CODE: 0,
        SensitiveTag.BANK_ACCOUNT: 0,
    }

    # Get Score
    for sample in sample_data:
        matched_regex_tags = match_regex(sample)
        for tag in matched_regex_tags:
            if tag in tag_counts:
                tag_counts[tag] += 1

    raw_scores = {
        tag: count / total_samples for tag, count in tag_counts.items()
    }

    # Check Confidence
    high_confidence_tags = [(tag, score) for tag, score in raw_scores.items() if score >= threshold]

    final_candidates = []
    status = RegexStatus.UNDETERMINED

    # Sort by confidence score and severity weight if confidence score is high enough
    if high_confidence_tags:
        high_confidence_tags.sort(key=lambda x: (x[1], x[0].severity_weight), reverse=True)
        best_tag, best_score = high_confidence_tags[0]
        status = RegexStatus.SUCCESS
        final_candidates.append(best_tag)
    else:
        status = RegexStatus.UNDETERMINED
        final_candidates = [tag for tag, score in sorted(raw_scores.items(), key=lambda x:x[1], reverse=True) if score > 0.0]
    all_detected_tags = [(tag, score) for tag, score in raw_scores.items() if score > 0.0]

    regex_logger.info("----------------------------------------")
    regex_logger.info(f"Regex scan for column {column_name}:")
    regex_logger.info(f"Regex status: {status.value}")
    regex_logger.info(f"All detected tags: {all_detected_tags}")
    regex_logger.info(f"Regex candidates: {final_candidates}")
    regex_logger.info(f"Raw scores: {raw_scores}")
    regex_logger.info(f"----------------------------------------")

    return {
        "column_name": column_name,
        "regex_status": status.value,
        "regex_candidates": final_candidates,
        "all_detected_tags": all_detected_tags,
        "raw_scores": raw_scores
    }


