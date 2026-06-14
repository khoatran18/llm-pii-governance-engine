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
    [PII Tag & FLEXIBLE SEMANTIC SPECIFICATIONS & MULTILINGUAL]
    CRITICAL: Column names and data content can be in either English, Vietnamese, or a hybrid/abbreviated mix (e.g., 'ngay_sinh' vs 'dob', 'stk' vs 'bank_acc').

    The Cues and Patterns listed below are non-exhaustive guidelines for REFERENCE ONLY. They are relative indicators, not strict structural requirements. Focus on the core semantic intent rather than an exact physical match.

    1. RESIDENT_ID (Sensitivity: HIGH)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: National identification numbers, identity cards, or passport numbers.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'cccd', 'cmnd', 'can_cuoc', 'id_card', 'passport', 'pid', 'ref_id', 'code_x'.
       - Sample Data Patterns: Exactly 12 consecutive digits, purely numeric — no letters, no spaces, no separators of any kind (e.g., 001099012345). ANY value containing alphabetic characters, slashes, hyphens, or any non-digit character is DISQUALIFIED from this tag regardless of column name.

    2. HEALTH_INSURANCE_ID (Sensitivity: HIGH)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: National health insurance card numbers issued by the Vietnam Social Security (BHXH).
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'ma_so_bhyt', 'so_bhyt', 'health_insurance_id', 'health_insurance_no', 'bhyt_no', 'hi_number'.
       - Sample Data Patterns: Alphanumeric strings exactly 15 characters long, starting with 2 uppercase letters representing the target group (e.g., DN, HC, GD, HS, SV, HT, TE, QN, CN, HN) followed by exactly 13 digits (e.g., DN4010123456789).

    3. SALARY (Sensitivity: HIGH)
       - Description: Financial compensation, income, or monetary transaction values linked to a person.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'luong', 'thu_nhap', 'salary', 'income', 'm_val', 'compensation'.
       - Sample Data Patterns: High-value numbers or integers (e.g., 5000000, 15500000), often ending in multiple zeros.

    4. PHONE (Sensitivity: MEDIUM)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Primary or secondary telephone/mobile numbers.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'sdt', 'dien_thoai', 'phone', 'mobile', 'tel', 'so_phu', 'val_02'.
       - Sample Data Patterns: 10-digit strings starting with Vietnamese mobile prefixes (e.g., 03, 05, 07, 08, 09), sometimes formatted with dots or hyphens.

    5. EMAIL (Sensitivity: MEDIUM)
       - NOTE: This tag is almost exclusively detected by upstream regex with near-perfect accuracy. Its appearance in CATEGORY 2 (undetermined) is extremely rare and statistically unlikely. Be highly skeptical before assigning this tag — the burden of proof is on the data, not the column name.
       - Description: Personal or corporate email addresses.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'email', 'mail', 'work_email', 'personal_email', 'ref_ext', 'notify_ref'.
       - Sample Data Patterns: Alphanumeric strings containing '@' and domain extensions (e.g., gmail.com, yahoo.com, outlook.com, viettel.com.vn).

    6. NAME (Sensitivity: MEDIUM)
       - Description: Full names, first names, or last names of individuals. This also includes columns that store the name of a person identified by their role or occupation (e.g., a teacher's name, a student's name, a doctor's name) — the column does not need to say "name" explicitly; any column whose data contains actual personal names qualifies.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues (explicit name fields): 'ten', 'ho_va_ten', 'ho_ten', 'fullname', 'name', 'chu_ho_so', 'sender', 'receiver'
         — OR — (role/occupation nouns whose values are personal names): 'giao_vien', 'hoc_sinh', 'bac_si', 'benh_nhan', 'nhan_vien', 'khach_hang', 'nguoi_dung', or any similar role noun where the stored value is a personal name rather than a category label or ID.
       - Sample Data Patterns: Text strings containing capitalized Vietnamese personal names, often composed of 2 to 4 words (e.g., "Nguyễn Văn An", "Trần Minh Khoa"). CRITICAL: the actual cell values must be personal names — if the column stores role labels or codes (e.g., "Giáo viên", "HS001") instead of names, classify as NONE.

    7. ADDRESS (Sensitivity: LOW)
       - Description: Physical residential addresses, permanent, or temporary locations. Can range from a full hierarchical address to just a province or city name.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'dia_chi', 'address', 'cu_tru', 'thuong_tru', 'res_data', 'meta_addr'.
       - Sample Data Patterns: Text strings containing geographic location information at any level of detail — from a full hierarchical address (street, ward, district, province) down to just a district or province name (e.g., "123 Đường Lê Lợi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh"; "Quận Cầu Giấy, Hà Nội"; "Tỉnh Nghệ An"; "Bình Dương").
    
    8. DOB (Sensitivity: LOW)
       - Description: Date of birth or other sensitive personal dates.
       - DATA-FIRST WARNING: Column names for this tag can be obfuscated or generic. You MUST base your decision primarily on the actual sample data pattern, not the column name alone.
       - Column Name Cues: 'ngay_sinh', 'dob', 'birth', 'date_of_birth', 'd_entry' (when sample data indicates a historical birth date).
       - Sample Data Patterns: Dates or strings with delimiters like '/', '-', or '.' (e.g., 18/12/2004, 1995-05-20, 2001.01.30). Year values are typically historical (e.g., 1960 to 2005).

    9. NONE (Sensitivity: NONE)
        - Description: Non-PII columns, operational data, structural metadata, system statuses, or public generic records.
        - Column Name Cues: 'status', 'created_at', 'txn_id', 'loai_giao_dich', 'trang_thai', 'batch_id', 'phi_giao_dich'.
        - Sample Data Patterns: System IDs, operational logs, flags, categories, or currency codes (e.g., "VND", "Thành công").

    =====================================================================
    [CRITICAL BUSINESS RULES FOR AI SEMANTIC DEDUCTION]
    1. Full-Table Context: Review Category 1 to perform a process of elimination on Category 2.
    2. Data Over Name Rule (Anti-Misleading): Column names can be highly misleading, obfuscated, or completely generic (e.g., 'c01', 'c03', 'hhd', 'val_02', 'm_val'). You MUST prioritize the semantic meaning and patterns of the actual sample data over the literal column name. If the column name says one thing but the data clearly represents another PII type, classify based on the DATA.
    3. Conservative Classification: For columns in CATEGORY 2, default assumption is NONE unless sample data provides clear, unambiguous evidence of a PII type. Do NOT attempt to find a tag — let the data speak for itself. NONE is a valid and preferred outcome when evidence is weak or ambiguous.
    4. Majority Vote Rule: If LESS THAN 50% of the sample data rows match the expected pattern of a PII type, you MUST return NONE — regardless of how strongly the column name implies that PII type. A partial match is treated as NO match.
    5. Target Isolation Principle: Your final JSON output MUST ONLY contain the columns listed in CATEGORY 2 (UNDETERMINED COLUMNS). Do not re-evaluate or include columns from CATEGORY 1 in the final output object.
    6. Strict Format Validation Rule: Even if a column name strongly implies a PII type, if the actual sample data format does NOT match the expected pattern for that PII type, you MUST classify it as "NONE". Do not force-fit data into a PII tag just because the column name suggests it.
    7. Confidence Threshold Gate: You MUST assign a PII tag ONLY IF your internal confidence_score is strictly greater than 0.7. If your confidence is 0.7 or below — due to ambiguous data, mixed patterns, weak column name signal, or any other uncertainty — you MUST fall back to "NONE" with "is_pii": false, regardless of how plausible the tag may seem. When in doubt, always default to NONE.

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
                "suggested_tag": "Must be one of: [RESIDENT_ID, HEALTH_INSURANCE_ID, PHONE, EMAIL, NAME, ADDRESS, SALARY, DOB, NONE]",
                "sensitivity_level": "Must be one of: [HIGH, MEDIUM, LOW, NONE]",
                "confidence_score": 0.95,
                "reason": "Concise reasoning in English detailing your full-table deduction logic."
            }}
        ]
    }}
    """