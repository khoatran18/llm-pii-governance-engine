import logging
import re

from pyspark import Row

from src.config.logging import setup_logging
from src.core.dtos.enums import MaskingRule, UserRole, SensitivityTag, SensitivityLevel
from src.modules.policy_engine.data_masker import DataMasker
from src.modules.policy_engine.pipeline import PolicyEngine

setup_logging()
test_logger = logging.getLogger("test")


def test_masking_function_correctness_isolation(spark_session):
    """
    Masking function correctness
    - Validates isolated structural output formats of the string mutation catalog
    """
    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + " [POLICY ENGINE] Starting Isolated Masking Function Correctness " + "-" * 25)

    masker = DataMasker()

    # Mock data
    raw_cccd = "023746352736"
    raw_phone = "0937463528"
    raw_email = "raw_test_email@gmail.com"
    raw_name = "Test Suite"

    raw_row = Row(cccd=raw_cccd, phone=raw_phone, email=raw_email, name=raw_name)
    df_mock = spark_session.createDataFrame([raw_row])

    # 1. Validate HASH_MASK (SHA-256)
    test_logger.info("[CORRECTNESS] Benchmarking HASH_MASK function accuracy")
    df_hash_1 = masker.apply_masking(df_mock, "cccd", MaskingRule.HASH_MASK)
    res_hash_1 = df_hash_1.first()["cccd"]
    df_hash_2 = masker.apply_masking(df_mock, "cccd", MaskingRule.HASH_MASK)
    res_hash_2 = df_hash_2.first()["cccd"]

    test_logger.info(f"   Original Input: '{raw_cccd}'")
    test_logger.info(f"   Hash Run 1    : '{res_hash_1}'")
    test_logger.info(f"   Hash Run 2    : '{res_hash_2}'")

    assert len(res_hash_1) == 64, f"SHA-256 output length mismatch. Expected 64, got {len(res_hash_1)}"

    assert res_hash_1 == res_hash_2, f"Same pipeline hash executions produced distinct hashes across runs."

    # 2. Validate REDACTED_MASK
    test_logger.info("[CORRECTNESS] Benchmarking REDACTED_MASK function accuracy")
    df_redact = masker.apply_masking(df_mock, "phone", MaskingRule.REDACTED_MASK)
    res_redact = df_redact.first()["phone"]
    test_logger.info(f"   Input Literal: '{raw_phone}' -> Mutated Redact Output: '{res_redact}'")
    assert res_redact == "REDACTED", f"REDACTED_MASK output contract broken. Got: {res_redact}"

    # 3. Validate NULLIFY_MASK
    test_logger.info("[CORRECTNESS] Benchmarking NULLIFY_MASK function accuracy")
    df_null = masker.apply_masking(df_mock, "email", MaskingRule.NULLIFY_MASK)
    res_null = df_null.first()["email"]
    test_logger.info(f"   Input Literal: '{raw_email}' -> Mutated Nullify Output: '{res_null}'")
    assert res_null is None, f"NULLIFY_MASK output contract broken. Got: {res_null}"

    # 4. Validate PARTIAL_MASK algorithms
    test_logger.info("[CORRECTNESS] Benchmarking PARTIAL_MASK core regex-conditional branches")
    df_partial = df_mock
    for col in ["cccd", "phone", "email", "name"]:
        df_partial = masker.apply_masking(df_partial, col, MaskingRule.PARTIAL_MASK)
    res_partial = df_partial.first()

    # Log individual evaluation traces for granular pattern monitoring
    test_logger.info(f"   Partial Email -> Input: '{raw_email}' | Masked: '{res_partial['email']}'")
    test_logger.info(f"   Partial Name  -> Input: '{raw_name}' | Masked: '{res_partial['name']}'")
    test_logger.info(f"   Partial CCCD  -> Input: '{raw_cccd}' | Masked: '{res_partial['cccd']}'")
    test_logger.info(f"   Partial Phone -> Input: '{raw_phone}' | Masked: '{res_partial['phone']}'")
    test_logger.info("=" * 82 + "\n")

    # Assert structural integrity per algorithm branch
    assert res_partial["email"] == "r*************@gmail.com", f"Partial Email mutation failed. Got: {res_partial['email']}"
    assert res_partial["name"] == "T*** S****", f"Partial Name token transformation failed. Got: {res_partial['name']}"
    assert re.match(r"^023\*{5}2736$", res_partial["cccd"]), f"Partial National ID format verification failed. Got: {res_partial['cccd']}"
    assert re.match(r"^093\*{3}3528$", res_partial["phone"]), f"Partial Mobile Phone string slice failed. Got: {res_partial['phone']}"


def test_dynamic_masking_compliance(spark_session, pg_client, test_config):
    """
    Verification of Dynamic Masking compliance
    - Masking Compliance Rate (Target 100%)
    - No Over-masking Rate (Target 100%)
    """
    test_suite_config = test_config["test_suite"]
    table_name = test_suite_config["table_name"]
    columns_config = test_suite_config["columns_config"]
    masking_policies = test_suite_config["masking_policies"]

    test_logger.info("\n" + "=" * 500)
    test_logger.info("-" * 25 + " [POLICY ENGINE] Starting Dynamic Masking Compliance Test " + "-" * 25)
    test_logger.info(f"Target Table: {table_name}")

    data_masker = DataMasker()
    pipeline = PolicyEngine(spark_session, pg_client, data_masker, test_config)

    total_sensitive_checks = 0
    successful_sensitive_masks = 0
    total_non_sensitive_checks = 0
    successful_non_sensitive_masks = 0

    # Mapper
    tag_to_level_map = {
        SensitivityTag.RESIDENT_ID: SensitivityLevel.HIGH,
        SensitivityTag.HEALTH_INSURANCE_ID: SensitivityLevel.HIGH,
        SensitivityTag.SALARY: SensitivityLevel.HIGH,
        SensitivityTag.PHONE: SensitivityLevel.MEDIUM,
        SensitivityTag.EMAIL: SensitivityLevel.MEDIUM,
        SensitivityTag.NAME: SensitivityLevel.MEDIUM,
        SensitivityTag.ADDRESS: SensitivityLevel.LOW,
        SensitivityTag.DOB: SensitivityLevel.LOW,
        SensitivityTag.NONE: SensitivityLevel.NONE
    }

    # Validator function
    mask_validators = {
        MaskingRule.HASH_MASK: lambda val, col: val is not None and len(str(val)) == 64,
        MaskingRule.NULLIFY_MASK: lambda val, col: val is None,
        MaskingRule.REDACTED_MASK: lambda val, col: val == "REDACTED",
        MaskingRule.PARTIAL_MASK: lambda val, col: (
                "*" in str(val) and (
                ("@" in str(val) if "email" in col else True) and
                (" " in str(val) if "c03" in col or "name" in col else True)
        )
        )
    }

    roles = [UserRole.ADMIN, UserRole.ANALYST, UserRole.AUDITOR]
    # Test all roles
    for role in roles:
        role_str = role.name
        test_logger.info(f"Evaluating data access matrices vertical slice for User Role: {role}")

        # Get DataFrame from dynamic masking
        secured_dfs = pipeline.execute_secure_pipeline(
            table_name=table_name,
            selected_columns=[],
            user_role=role,
        )

        assert len(secured_dfs) > 0, f"Data asset isolation failure: Secure pipeline returned empty dataset for {table_name} under role {role_str}"

        # Get sample row
        df_secure = secured_dfs[0]
        sample_secure_row = df_secure.first()

        # Check each column
        for col_info in columns_config:
            # Only check column have 100% valid data (if not, row to check can have invalid data)
            if col_info["match_percentage"] != 100:
                continue

            col_name = col_info["column_name"]
            sens_tag = col_info["sensitivity_tag"]

            level_tier = tag_to_level_map.get(sens_tag, SensitivityLevel.NONE)
            expected_rule_str = masking_policies[role][level_tier]
            expected_rule_enum = MaskingRule(expected_rule_str)

            actual_value = sample_secure_row[col_name]

            # Evaluate Masking Compliance Rate
            if sens_tag != "NONE" and expected_rule_str != "CLEAR_TEXT":
                total_sensitive_checks += 1

                validator_func = mask_validators.get(expected_rule_enum)
                if validator_func and validator_func(actual_value, col_name):
                    successful_sensitive_masks += 1
                else:
                    test_logger.error(
                        f"[SECURITY BREACH] Compliance failure on Table '{table_name}' | "
                        f"Role: '{role_str}' | Column: '{col_name}' | Tag: '{sens_tag}' | "
                        f"Expected Rule: '{expected_rule_enum.name}' | Actual Spark Value: '{actual_value}'"
                    )

            # Evaluate No Over-masking Rate
            else:
                total_non_sensitive_checks += 1
                if actual_value is not None and actual_value != "REDACTED" and "*" not in str(actual_value):
                    successful_non_sensitive_masks += 1
                else:
                    test_logger.error(
                        f"[OVER-MASKING VIOLATION] Unnecessary obfuscation on Table '{table_name}' | "
                        f"Role: '{role_str}' | Column: '{col_name}' | Tag: '{sens_tag}' | "
                        f"Expected Rule: '{expected_rule_enum.name}' | Actual Spark Value: '{actual_value}'"
                    )

    # Metrics report
    masking_compliance_rate = (successful_sensitive_masks / total_sensitive_checks) * 100 if total_sensitive_checks > 0 else 100.0
    no_over_masking_rate = (successful_non_sensitive_masks / total_non_sensitive_checks) * 100 if total_non_sensitive_checks > 0 else 100.0

    test_logger.info("\n" + "=" * 22 + " [POLICY ENGINE] ACCESS CONTROL COMPLIANCE AUDIT MATRIX " + "=" * 22)
    test_logger.info(f"   Target Lakehouse Asset Table   : {table_name}")
    test_logger.info(f"   Calculated Masking Compliance  : {masking_compliance_rate:.2f}% with {successful_sensitive_masks}/{total_sensitive_checks} columns (Target: 100.00%)")
    test_logger.info(f"   Calculated No Over-masking Rate: {no_over_masking_rate:.2f}% with {successful_non_sensitive_masks}/{total_non_sensitive_checks} columns (Target: 100.00%)")
    test_logger.info("=" * 82 + "\n")

    # Enforce strict compliance barriers
    assert masking_compliance_rate == 100.0, \
        f"Security Breach Detected: Masking Compliance is {masking_compliance_rate:.2f}%, sensitive assets are leaking clear text."
    assert no_over_masking_rate == 100.0, \
        f"Data Over-masking Violation: Over-masking rate is {no_over_masking_rate:.2f}%, non-sensitive records are mistakenly obfuscated."







