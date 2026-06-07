from enum import Enum

class SensitivityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"
    # AMBIGUOUS = "AMBIGUOUS"

class SensitiveTag(str, Enum):
    RESIDENT_ID = "RESIDENT_ID"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    TAX_CODE = "TAX_CODE"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    SALARY = "SALARY"
    DOB = "DOB"
    WORKPLACE = "WORKPLACE"
    NONE = "NONE"
    # AMBIGUOUS = "AMBIGUOUS"

    @property
    def sensitivity_level(self) -> SensitivityLevel:
        tag_sensitivity_map = {
            # HIGH
            SensitiveTag.RESIDENT_ID: SensitivityLevel.HIGH,
            SensitiveTag.BANK_ACCOUNT: SensitivityLevel.HIGH,
            SensitiveTag.TAX_CODE: SensitivityLevel.HIGH,
            SensitiveTag.SALARY: SensitivityLevel.HIGH,
            # MEDIUM
            SensitiveTag.PHONE: SensitivityLevel.MEDIUM,
            SensitiveTag.EMAIL: SensitivityLevel.MEDIUM,
            SensitiveTag.NAME: SensitivityLevel.MEDIUM,
            # LOW
            SensitiveTag.ADDRESS: SensitivityLevel.LOW,
            SensitiveTag.DOB: SensitivityLevel.LOW,
            SensitiveTag.WORKPLACE: SensitivityLevel.LOW,
            # NONE & SPECIAL
            SensitiveTag.NONE: SensitivityLevel.NONE,
            # SensitiveTag.AMBIGUOUS: SensitivityLevel.NONE
        }
        return tag_sensitivity_map.get(self, SensitivityLevel.NONE)

    @property
    def severity_weight(self) -> int:
        weights = {
            SensitiveTag.RESIDENT_ID: 9,
            SensitiveTag.BANK_ACCOUNT: 8,
            SensitiveTag.TAX_CODE: 7,
            SensitiveTag.SALARY: 6,
            SensitiveTag.PHONE: 5,
            SensitiveTag.EMAIL: 4,
            SensitiveTag.NAME: 3,
            SensitiveTag.ADDRESS: 2,
            SensitiveTag.DOB: 1,
            SensitiveTag.WORKPLACE: 0,
            # SensitiveTag.AMBIGUOUS: -1,
            SensitiveTag.NONE: -2
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



