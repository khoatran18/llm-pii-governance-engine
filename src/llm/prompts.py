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
    Analyze the Lakehouse table named [{table_name}] based on the provided structural schema and raw sample data partitioned into 2 semantic categories.

    =====================================================================
    [CATEGORY 1: DETERMINED COLUMNS (HIGH CONFIDENCE REGEX MATCHES)]
    These columns are verified. Use them as anchor points and business context to understand the table's domain:
    {determined_json}

    =====================================================================
    [CATEGORY 2: UNDETERMINED COLUMNS (AMBIGUOUS OR LOW CONFIDENCE REGEX MATCHES)]
    These columns either failed physical patterns or scored below the threshold. Read the Vietnamese data semantics carefully:
    {undetermined_json}

    =====================================================================
    [CRITICAL BUSINESS RULES FOR AI SEMANTIC DEDUCTION]
    1. Full-Table Context: Review Category 1 to perform a process of elimination on Category 2.
    2. Mandatory Classification: For columns in Category 2, use your linguistic capability to deduce the single best-fitting PII tag from the allowed list. If the column is genuinely public data, return "NONE".
    3. Finality Principle: You must make a clear decision for every column. Do not use generic placeholders.

    =====================================================================
    CRITICAL CONSTRAINTS:
    1. The "reason" field MUST be extremely concise (strictly under 15 words). Do not write long explanations.
    2. Example of a good reason: "Translates to full name, contains Vietnamese personal names."
    3. Do not include markdown code blocks (like ```json) in your response, return pure JSON string only.

    =====================================================================
    [REQUIRED OUTPUT FORMAT (STRUCTURAL JSON)]
    Return a single valid JSON object matching the schema below. No markdown wrappers (do NOT wrap in ```json).
    {{
        "table_name": "{table_name}",
        "columns": [
            {{
                "column_name": "exact_column_name_from_input",
                "is_pii": true,
                "suggested_tag": "Must be one of: [RESIDENT_ID, PHONE, EMAIL, TAX_CODE, BANK_ACCOUNT, NAME, ADDRESS, SALARY, DOB, WORKPLACE, NONE]",
                "sensitivity_level": "Must be one of: [HIGH, MEDIUM, LOW, NONE]",
                "confidence_score": 0.95,
                "reason": "Concise reasoning in English detailing your full-table deduction logic."
            }}
        ]
    }}
    """