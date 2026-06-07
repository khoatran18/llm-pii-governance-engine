# File: modules/ai_governance/llm_scanner/prompts.py

class GovernanceLLMPrompts:
    """
    Centralized system and user prompts for AI Governance PII Scanner.
    Prompts are written in English to optimize LLM reasoning and structured JSON output.
    """

    SYSTEM_ROLE = """
    You are an expert Data Governance and Information Security Officer.
    Your task is to analyze table metadata, column names, and sample data to accurately identify and tag Personally Identifiable Information (PII).
    """

    BATCH_TABLE_SCAN_PROMPT = """
        Analyze the Lakehouse table named [{table_name}] based on the provided structural schema and raw sample data partitioned into 3 semantic categories.

        =====================================================================
        [CATEGORY 1: DETERMINED COLUMNS (SUCCESSFULLY CLASSIFIED BY REGEX)]
        These columns are verified. Use them as anchor points and context for the table's domain:
        {determined_json}

        =====================================================================
        [CATEGORY 2: COLLISION COLUMNS (MULTIPLE REGEX PATTERNS MATCHED)]
        These columns have physical format conflicts. Use cross-column reasoning to pick the single correct tag:
        {collision_json}

        =====================================================================
        [CATEGORY 3: UNDETERMINED COLUMNS (REGEX COMPLETELY FAILED)]
        These columns have completely obfuscated names or unrecognized data patterns. Read the Vietnamese data semantics carefully:
        {undetermined_json}

        =====================================================================
        [CRITICAL BUSINESS RULES FOR AI SEMANTIC DEDUCTION]
        1. Full-Table Context: Analyze all categories holistically. Use Category 1 to perform a process of elimination on Category 2 and 3.
        2. Conflict Resolution (For Category 2): If a column is in `collision_columns` and you cannot confidently differentiate between the tags (e.g., a 10-digit number being PHONE vs BANK_ACCOUNT), you may set "suggested_tag" to "AMBIGUOUS" and list them in "possible_tags".
        3. Mandatory Guessing (For Category 3 - CRITICAL): If a column is in `undetermined_columns`, you ARE NOT ALLOWED to return "AMBIGUOUS". Since Regex found nothing, you must use your full linguistic capability to deduce the single best-fitting PII tag (or return "NONE" if it is genuinely public data). "AMBIGUOUS" is strictly forbidden for Category 3.

        =====================================================================
        [REQUIRED OUTPUT FORMAT (STRUCTURAL JSON)]
        Return a single valid JSON object matching the schema below. No markdown wrappers.
        {{
            "table_name": "{table_name}",
            "columns_scanned": [
                {{
                    "column_name": "exact_column_name_from_input",
                    "is_pii": true,
                    "suggested_tag": "Must be one of: [CCCD, PHONE, EMAIL, TAX_CODE, BANK_ACCOUNT, NAME, ADDRESS, AMBIGUOUS]",
                    "sensitivity_level": "HIGH",
                    "confidence_score": 0.95,
                    "reason": "Concise reasoning in English detailing your full-table deduction logic."
                }}
            ]
        }}
        """