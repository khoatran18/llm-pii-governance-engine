class GovernanceLLMPrompts:
    """
    Centralized system and user prompts for AI Governance PII Scanner.
    Prompts are written in English to optimize LLM reasoning and structured JSON output.
    """

    SYSTEM_ROLE = """
    You are an expert Data Governance and Information Security Officer.
    Your task is to analyze table metadata, column names, and sample data to accurately identify and tag Personally Identifiable Information (PII).
    """

    BATCH_TABLE_SCAN_PROMPT_V2 = """
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
    [PII Tag & FLEXIBLE SEMANTIC SPECIFICATIONS & MULTILINGUAL]
    CRITICAL: Column names and data content can be in either English, Vietnamese, or a hybrid/abbreviated mix (e.g., 'ngay_sinh' vs 'dob', 'stk' vs 'bank_acc').
    
    The Cues and Patterns listed below are non-exhaustive guidelines for REFERENCE ONLY. They are relative indicators, not strict structural requirements. Focus on the core semantic intent rather than an exact physical match.

    1. SALARY (Sensitivity: HIGH)
       - Description: Financial compensation, income, or monetary transaction values linked to a person.
       - Column Name Cues: 'luong', 'thu_nhap', 'salary', 'income', 'm_val', 'compensation'.
       - Sample Data Patterns: High-value numbers or integers (e.g., 5000000, 15500000), often ending in multiple zeros.

    2. NAME (Sensitivity: MEDIUM)
       - Description: Full names, first names, or last names of individuals.
       - Column Name Cues: 'ten', 'ho_va_ten',' 'ho_ten', 'fullname', 'name', 'chu_ho_so', 'sender', 'receiver'.
       - Sample Data Patterns: Text strings containing capitalized Vietnamese names, often composed of 2 to 4 words (e.g., "Nguyễn Văn Văn", "Trần Minh Khoa").

    3. ADDRESS (Sensitivity: LOW)
       - Description: Physical residential addresses, permanent, or temporary locations.
       - Column Name Cues: 'dia_chi', 'address', 'cu_tru', 'thuong_tru', 'res_data', 'meta_addr'.
       - Sample Data Patterns: Long text strings containing hierarchical geographic components like street, ward, district, province (e.g., "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh").

    4. DOB (Sensitivity: LOW)
       - Description: Date of birth or other sensitive personal dates.
       - Column Name Cues: 'ngay_sinh', 'dob', 'birth', 'date_of_birth', 'd_entry' (when sample data indicates a historical birth date).
       - Sample Data Patterns: Dates or strings with delimiters like '/', '-', or '.' (e.g., 18/12/2004, 1995-05-20, 2001.01.30). Year values are typically historical (e.g., 1960 to 2005).

    5. WORKPLACE (Sensitivity: LOW)
        - Description: Specific office locations, assigned provinces of work, or corporate branches.
        - Column Name Cues: 'noi_lam_viec', 'workplace', 'branch', 'office_loc'.
        - Sample Data Patterns: Plain text indicating a city or province (e.g., "Hà Nội", "TP. Hồ Chí Minh").

    6. NONE (Sensitivity: NONE)
        - Description: Non-PII columns, operational data, structural metadata, system statuses, or public generic records.
        - Column Name Cues: 'status', 'created_at', 'txn_id', 'loai_giao_dich', 'trang_thai', 'batch_id', 'phi_giao_dich'.
        - Sample Data Patterns: System IDs, operational logs, flags, categories, or currency codes (e.g., "VND", "Thành công").

    =====================================================================
    [CRITICAL BUSINESS RULES FOR AI SEMANTIC DEDUCTION]
    1. Full-Table Context: Review Category 1 to perform a process of elimination on Category 2.
    2. Data Over Name Rule (Anti-Misleading): Column names can be highly misleading, obfuscated, or completely generic (e.g., 'c01', 'c03', 'hhd', 'val_02', 'm_val'). You MUST prioritize the semantic meaning and patterns of the actual sample data over the literal column name. If the column name says one thing but the data clearly represents another PII type, classify based on the DATA.
    3. Mandatory Classification: For columns in Category 2, use your linguistic capability to deduce the single best-fitting PII tag from the allowed list. If the column is genuinely public data, return "NONE".
    4. Target Isolation Principle: Your final JSON output MUST ONLY contain the columns listed in CATEGORY 2 (UNDETERMINED COLUMNS). Do not re-evaluate or include columns from CATEGORY 1 in the final output object.
    5. Strict Format Validation Rule: Even if a column name strongly implies a PII type, if the actual sample data format does NOT match the expected pattern for that PII type, you MUST classify it as "NONE". Do not force-fit data into a PII tag just because the column name suggests it.
   
    =====================================================================
    [CRITICAL CONSTRAINTS]
    1. The "reason" field MUST be extremely concise (strictly under 15 words). Do not write long explanations.
    2. Example of a good reason: "Translates to full name, contains Vietnamese personal names."
    3. Do not include markdown code blocks (like ```json) in your response, return pure JSON string only.

    =====================================================================
    [REQUIRED OUTPUT FORMAT (STRUCTURAL JSON)]
    Return a single valid JSON object matching the schema below. No markdown wrappers (do NOT wrap in ```json).
    CRITICAL: The "columns" array MUST contain ONLY the columns evaluated from CATEGORY 2.
    
    {{
        "table_name": "{table_name}",
        "columns": [
            {{
                "column_name": "exact_column_name_from_category_2_only",
                "is_pii": true,
                "suggested_tag": "Must be one of: [NAME, ADDRESS, SALARY, DOB, WORKPLACE, NONE]",
                "sensitivity_level": "Must be one of: [HIGH, MEDIUM, LOW, NONE]",
                "confidence_score": 0.95,
                "reason": "Concise reasoning in English detailing your full-table deduction logic."
            }}
        ]
    }}
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
    [PII Tag & FLEXIBLE SEMANTIC SPECIFICATIONS & MULTILINGUAL]
    CRITICAL: Column names and data content can be in either English, Vietnamese, or a hybrid/abbreviated mix (e.g., 'ngay_sinh' vs 'dob', 'stk' vs 'bank_acc').
    
    The Cues and Patterns listed below are non-exhaustive guidelines for REFERENCE ONLY. They are relative indicators, not strict structural requirements. Focus on the core semantic intent rather than an exact physical match.
    
    1. RESIDENT_ID (Sensitivity: HIGH)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: National identification numbers, identity cards, or passport numbers.
       - Column Name Cues: 'cccd', 'cmnd', 'can_cuoc', 'id_card', 'passport', 'pid', 'ref_id', 'code_x'.
       - Sample Data Patterns: 12-digit numbers (modern CCCD). ANY other format (e.g.,alphanumeric, slash-separated) is DISQUALIFIED from this tag regardless of column name.

    2. BANK_ACCOUNT (Sensitivity: HIGH)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Financial account numbers used for banking, salaries, or transactions.
       - Column Name Cues: 'stk', 'tai_khoan', 'acct', 'account_no', 'bank_acc', 'stk_ngan_hang'.
       - Sample Data Patterns: Numeric strings typically ranging from 9 to 16 digits.

    3. TAX_CODE (Sensitivity: HIGH)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Personal or corporate tax identification numbers.
       - Column Name Cues: 'mst', 'ma_so_thue', 'tax_code', 'tax_id', 't_code'.
       - Sample Data Patterns: 10-digit numerical strings (or 13-digit for branches).

    4. SALARY (Sensitivity: HIGH)
       - Description: Financial compensation, income, or monetary transaction values linked to a person.
       - Column Name Cues: 'luong', 'thu_nhap', 'salary', 'income', 'm_val', 'compensation'.
       - Sample Data Patterns: High-value numbers or integers (e.g., 5000000, 15500000), often ending in multiple zeros.

    5. PHONE (Sensitivity: MEDIUM)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Primary or secondary telephone/mobile numbers.
       - Column Name Cues: 'sdt', 'dien_thoai', 'phone', 'mobile', 'tel', 'so_phu', 'val_02'.
       - Sample Data Patterns: 10-digit strings starting with Vietnamese mobile prefixes (e.g., 03, 05, 07, 08, 09), sometimes formatted with dots or hyphens.

    6. EMAIL (Sensitivity: MEDIUM)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Personal or corporate email addresses.
       - Column Name Cues: 'email', 'mail', 'work_email', 'personal_email', 'ref_ext', 'notify_ref'.
       - Sample Data Patterns: Alphanumeric strings containing '@' and domain extensions (e.g., gmail.com, yahoo.com, outlook.com, viettel.com.vn).

    7. NAME (Sensitivity: MEDIUM)
       - Description: Full names, first names, or last names of individuals.
       - Column Name Cues: 'ten', 'ho_va_ten',' 'ho_ten', 'fullname', 'name', 'chu_ho_so', 'sender', 'receiver'.
       - Sample Data Patterns: Text strings containing capitalized Vietnamese names, often composed of 2 to 4 words (e.g., "Nguyễn Văn Văn", "Trần Minh Khoa").

    8. ADDRESS (Sensitivity: LOW)
       - Description: Physical residential addresses, permanent, or temporary locations.
       - Column Name Cues: 'dia_chi', 'address', 'cu_tru', 'thuong_tru', 'res_data', 'meta_addr'.
       - Sample Data Patterns: Long text strings containing hierarchical geographic components like street, ward, district, province (e.g., "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh").

    9. DOB (Sensitivity: LOW)
       - Description: Date of birth or other sensitive personal dates.
       - Column Name Cues: 'ngay_sinh', 'dob', 'birth', 'date_of_birth', 'd_entry' (when sample data indicates a historical birth date).
       - Sample Data Patterns: Dates or strings with delimiters like '/', '-', or '.' (e.g., 18/12/2004, 1995-05-20, 2001.01.30). Year values are typically historical (e.g., 1960 to 2005).

    10. WORKPLACE (Sensitivity: LOW)
        - Description: Specific office locations, assigned provinces of work, or corporate branches.
        - Column Name Cues: 'noi_lam_viec', 'workplace', 'branch', 'office_loc'.
        - Sample Data Patterns: Plain text indicating a city or province (e.g., "Hà Nội", "TP. Hồ Chí Minh").

    11. NONE (Sensitivity: NONE)
        - Description: Non-PII columns, operational data, structural metadata, system statuses, or public generic records.
        - Column Name Cues: 'status', 'created_at', 'txn_id', 'loai_giao_dich', 'trang_thai', 'batch_id', 'phi_giao_dich'.
        - Sample Data Patterns: System IDs, operational logs, flags, categories, or currency codes (e.g., "VND", "Thành công").

    =====================================================================
    [CRITICAL BUSINESS RULES FOR AI SEMANTIC DEDUCTION]
    1. Full-Table Context: Review Category 1 to perform a process of elimination on Category 2.
    2. Data Over Name Rule (Anti-Misleading): Column names can be highly misleading, obfuscated, or completely generic (e.g., 'c01', 'c03', 'hhd', 'val_02', 'm_val'). You MUST prioritize the semantic meaning and patterns of the actual sample data over the literal column name. If the column name says one thing but the data clearly represents another PII type, classify based on the DATA.
    3. Conservative Classification: For columns in CATEGORY 2, default assumption is NONE unless sample data provides clear, unambiguous evidence of a PII type. Do NOT attempt to find a tag — let the data speak for itself. NONE is a valid and preferred outcome when evidence is weak or ambiguous.
    4. Majority Vote Rule: If LESS THAN 60% of the sample data rows match the expected pattern of a PII type, you MUST return NONE — regardless of how strongly the column name implies that PII type. A partial match is treated as NO match.
    5. Target Isolation Principle: Your final JSON output MUST ONLY contain the columns listed in CATEGORY 2 (UNDETERMINED COLUMNS). Do not re-evaluate or include columns from CATEGORY 1 in the final output object.
    6. Strict Format Validation Rule: Even if a column name strongly implies a PII type, if the actual sample data format does NOT match the expected pattern for that PII type, you MUST classify it as "NONE". Do not force-fit data into a PII tag just because the column name suggests it.
   
    =====================================================================
    [CRITICAL CONSTRAINTS]
    1. The "reason" field MUST be extremely concise (strictly under 15 words). Do not write long explanations.
    2. Example of a good reason: "Translates to full name, contains Vietnamese personal names."
    3. Do not include markdown code blocks (like ```json) in your response, return pure JSON string only.

    =====================================================================
    [REQUIRED OUTPUT FORMAT (STRUCTURAL JSON)]
    Return a single valid JSON object matching the schema below. No markdown wrappers (do NOT wrap in ```json).
    CRITICAL: The "columns" array MUST contain ONLY the columns evaluated from CATEGORY 2.
    
    {{
        "table_name": "{table_name}",
        "columns": [
            {{
                "column_name": "exact_column_name_from_category_2_only",
                "is_pii": true,
                "suggested_tag": "Must be one of: [RESIDENT_ID, PHONE, EMAIL, TAX_CODE, BANK_ACCOUNT, NAME, ADDRESS, SALARY, DOB, WORKPLACE, NONE]",
                "sensitivity_level": "Must be one of: [HIGH, MEDIUM, LOW, NONE]",
                "confidence_score": 0.95,
                "reason": "Concise reasoning in English detailing your full-table deduction logic."
            }}
        ]
    }}
    """