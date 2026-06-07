# Get input, call LLM, parse JSON, retry
import json
import logging
from typing import Optional

from src.config.logging import setup_logging
from src.core.dtos.models import TableLLMScanRequest, TableLLMScanResponse
from src.llm.base import BaseLLMProvider
from src.llm.prompts import GovernanceLLMPrompts

setup_logging()
logger = logging.getLogger(__name__)

def parse_llm_response(raw_text: str) -> TableLLMScanResponse:
    if not raw_text:
        logger.error("LLM response is empty")
        raise ValueError("LLM response is empty")

    clean_text = raw_text.strip()

    logger.info("\n" + "=" * 40 + " [RAW LLM RESPONSE] " + "=" * 40)
    logger.info(clean_text)
    logger.info("=" * 100 + "\n")

    # If the response starts with ```json, remove the first line and the last line
    if clean_text.startswith("```"):
        # Remove the first line if it's just ```json'
        lines = clean_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's just ```'
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    # Start parsing
    try:
        parsed_dict = json.loads(clean_text)
        return TableLLMScanResponse(**parsed_dict)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing LLM response: {e}")
        raise ValueError("Error parsing LLM response")
    except Exception as e:
        logger.error(f"Unexpected error parsing LLM response: {e}")
        raise e

class LLMTableScanner:
    def __init__(self, llm_provider: BaseLLMProvider, max_retries: int = 3):
        self.llm_provider = llm_provider
        self.max_retries = max_retries

    def scan_table(self, request: TableLLMScanRequest):
        determined_json = json.dumps([c.model_dump() for c in request.determined_columns], ensure_ascii=False)
        undetermined_json = json.dumps([c.model_dump() for c in request.undetermined_columns], ensure_ascii=False)

        user_prompt = GovernanceLLMPrompts.BATCH_TABLE_SCAN_PROMPT.format(
            table_name=request.table_name,
            determined_json=determined_json,
            undetermined_json=undetermined_json
        )

        full_prompt = f"System: {GovernanceLLMPrompts.SYSTEM_ROLE}\n\nUser: {user_prompt}"

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"LLM Scan Attempt {attempt}...")
                response_llm = self.llm_provider.get_response(full_prompt)
                validated_response = parse_llm_response(response_llm)
                logger.info("LLM Scan Successful!")
                return validated_response

            except Exception as e:
                logger.error(f"LLM Scan Attempt {attempt} Failed: {e}")
                if attempt == self.max_retries:
                    raise e

        return None


