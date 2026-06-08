from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from src.core.dtos.enums import (
    DetectionMethod,
    MaskingRule,
    SensitiveTag,
    SensitivityLevel,
    UserRole, RegexStatus,
)

# For table metadata
class TableMetadata(BaseModel):
    table_id: Optional[int] = None
    table_name: str = Field(..., description="Table name in Lakehouse")
    iceberg_path: str = Field(..., description="Iceberg path in Lakehouse")
    created_at: Optional[datetime] = None

class ColumnMetadata(BaseModel):
    column_id: Optional[int] = None
    table_id: int = Field(..., description="Table ID")
    column_name: str = Field(..., description="Column name in Lakehouse")
    data_type: str = Field(..., description="Data type of the column")
    sensitive_tag: SensitiveTag = Field(..., description="Sensitive tag of the column")
    sensitivity_level: SensitivityLevel = Field(..., description="Sensitivity level of the column")
    confidence_level: float = Field(..., description="Confidence level of the column")
    detection_method: DetectionMethod = Field(..., description="Detection method used to detect the column")
    updated_at: Optional[datetime] = None

class RoleMetadata(BaseModel):
    role_id: Optional[int] = None
    role_name: UserRole = Field(..., description="Role name in Lakehouse")
    role_description: str = Field(..., description="Description of the role")
    created_at: Optional[datetime] = None

class AccessPolicyMetadata(BaseModel):
    policy_id: Optional[int] = None
    role_id: int = Field(..., description="Role ID")
    sensitivity_level: SensitivityLevel = Field(..., description="Sensitivity level of the policy")
    masking_rule: MaskingRule = Field(..., description="Masking rule used to mask the column")

# For audit log
class GovernanceAuditLog(BaseModel):
    """
    Table audit log for PII detection
    """
    log_id: Optional[int] = None
    table_name: str = Field(..., description="Scanned table name in Lakehouse")
    column_name: str = Field(..., description="Column name that was detected")
    detection_method: DetectionMethod = Field(..., description="In REGEX, LLM, HYBRID")
    possible_sensitivity_tags: List[SensitiveTag] = Field(..., description="List of possible PII tags")
    sensitivity_tag: SensitiveTag = Field(..., description="Final PII tag after manual review")
    sensitivity_level: SensitivityLevel = Field(..., description="Sensitivty level of the column")
    confidence_score: float = Field(..., description="Confidence score of the detection")
    reason: Optional[str] = Field(None, description="From LLM or Regex or LLM return AMBIGUOUS and be chosen by confidence score from Regex")
    scanned_at: Optional[datetime] = None

# For LLM Input
class ColumnScanInput(BaseModel):
    column_name: str = Field(..., description="Exact column name from Iceberg table schema")
    regex_status: RegexStatus = Field(
        ...,
        description="SUCCESS (1 match), COLLISION (multiple matches), or UNDETERMINED (0 match)"
    )
    regex_candidates: List[SensitiveTag] = Field(
        default_factory=list,
        description="List of PII tags detected by Regex. Contains 1 item if SUCCESS, multiple if COLLISION, empty [] if UNDETERMINED"
    )
    raw_scores: dict = Field(
        default_factory=list,
        description="Raw scores for each PII tag detected by Regex. Keys are PII tags, values are confidence scores"
    )
    sample_data: List[str] = Field(
        default_factory=list,
        description="Top 20-30 raw sample rows extracted from this column"
    )


class TableLLMScanRequest(BaseModel):
    table_name: str = Field(..., description="Name of the Lakehouse table being scanned")
    determined_columns: List[ColumnScanInput] = Field(
        default_factory=list,
        description="Anchor points. Columns already 100% successfully classified by Regex."
    )
    undetermined_columns: List[ColumnScanInput] = Field(
        default_factory=list,
        description="Columns where Regex completely failed. Requires AI to perform 100% semantic deduction."
    )

# For LLM Output
class SingleColumnLLMOutput(BaseModel):
    column_name: str
    is_pii: bool
    suggested_tag: SensitiveTag
    sensitivity_level: SensitivityLevel
    confidence_score: float
    reason: str

class TableLLMScanResponse(BaseModel):
    table_name: str = Field(..., description="Scanned table name in Lakehouse")
    columns: List[SingleColumnLLMOutput] = Field(..., description="List of detected columns with tag")

# For Masking Policy
class MaskingPolicy(BaseModel):
    """
    Masking Policy for a single column with a user role
    """
    column_name: str = Field(..., description="Column name to be masked")
    masking_rule: MaskingRule = Field(..., description="Masking rule to be applied")

# For final output each column
class ColumnScanResult(BaseModel):
    column_name: str = Field(..., description="Column name")
    is_pii: bool = Field(..., description="True if the column contains PII")
    sensitivity_tag: SensitiveTag = Field(..., description="Suggested PII tag")
    sensitivity_level: SensitivityLevel = Field(..., description="Sensitivty level of the column")
    confidence_score: float = Field(..., description="Confidence score of the detection")
    detection_method: DetectionMethod = Field(..., description="Detection method used")
    reason: str = Field(..., description="Reason for the detection")