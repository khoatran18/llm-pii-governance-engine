from enum import Enum

class SensitivityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
    # AMBIGUOUS = "AMBIGUOUS"

class SensitivityTag(str, Enum):
    RESIDENT_ID = "RESIDENT_ID"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    # TAX_CODE = "TAX_CODE"
    # BANK_ACCOUNT = "BANK_ACCOUNT"
    HEALTH_INSURANCE_ID = "HEALTH_INSURANCE_ID"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    SALARY = "SALARY"
    DOB = "DOB"
    # WORKPLACE = "WORKPLACE"
    NONE = "NONE"
    # AMBIGUOUS = "AMBIGUOUS"

    @property
    def sensitivity_level(self) -> SensitivityLevel:
        tag_sensitivity_map = {
            # HIGH
            SensitivityTag.RESIDENT_ID: SensitivityLevel.HIGH,
            # SensitiveTag.BANK_ACCOUNT: SensitivityLevel.HIGH,
            # SensitiveTag.TAX_CODE: SensitivityLevel.HIGH,
            SensitivityTag.SALARY: SensitivityLevel.HIGH,
            SensitivityTag.HEALTH_INSURANCE_ID: SensitivityLevel.HIGH,
            # MEDIUM
            SensitivityTag.PHONE: SensitivityLevel.MEDIUM,
            SensitivityTag.EMAIL: SensitivityLevel.MEDIUM,
            SensitivityTag.NAME: SensitivityLevel.MEDIUM,
            # LOW
            SensitivityTag.ADDRESS: SensitivityLevel.LOW,
            SensitivityTag.DOB: SensitivityLevel.LOW,
            # SensitiveTag.WORKPLACE: SensitivityLevel.LOW,
            # NONE & SPECIAL
            SensitivityTag.NONE: SensitivityLevel.NONE,
            # SensitiveTag.AMBIGUOUS: SensitivityLevel.NONE
        }
        return tag_sensitivity_map.get(self, SensitivityLevel.NONE)

    @property
    def severity_weight(self) -> int:
        weights = {
            SensitivityTag.RESIDENT_ID: 9,
            # SensitiveTag.BANK_ACCOUNT: 8,
            # SensitiveTag.TAX_CODE: 7,
            SensitivityTag.HEALTH_INSURANCE_ID: 7,
            SensitivityTag.SALARY: 6,
            SensitivityTag.PHONE: 5,
            SensitivityTag.EMAIL: 4,
            SensitivityTag.NAME: 3,
            SensitivityTag.ADDRESS: 2,
            SensitivityTag.DOB: 1,
            # SensitiveTag.WORKPLACE: 0,
            # SensitiveTag.AMBIGUOUS: -1,
            SensitivityTag.NONE: -2
        }
        return weights.get(self, -2)

class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    MASK = "MASK"    # Hash or partial
    DENY = "DENY"    # Redact or nullify

class MaskingRule(str, Enum):
    HASH_MASK = "HASH_MASK"
    REDACTED_MASK = "REDACTED_MASK"
    NULLIFY_MASK = "NULLIFY_MASK"
    PARTIAL_MASK = "PARTIAL_MASK"
    CLEAR_TEXT = "CLEAR_TEXT"

class DetectionMethod(str, Enum):
    LLM = "LLM"
    REGEX = "REGEX"
    HYBRID = "HYBRID"

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"    # Partial mask or hash
    AUDITOR = "AUDITOR"    # Redacted mask or nullify

class RegexStatus(str, Enum):
    SUCCESS = "SUCCESS"
    UNDETERMINED = "UNDETERMINED" # All tags detected have low confidence score

class DetectionReason(str, Enum):
    REGEX = "Detected PII fully by Regex"
    LLM = "Detected PII fully by LLM"
    AMBIGUOUS_PII = "Detected PII by LLM and Regex, finally chosen by Regex"
    AMBIGUOUS_NONE = "Regex detected PII but LLM did not detect any"
    FULLY_NONE = "No PII detected by Regex or LLM"



