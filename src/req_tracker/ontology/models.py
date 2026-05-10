"""Core ontology and source data contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

SCHEMA_VERSION = "v1"

SourceType = Literal["jira", "confluence", "email", "decision_archive", "dummy"]
DataClassification = Literal["public_internal", "restricted", "confidential", "no_external_llm"]
NodeType = Literal[
    "Requirement",
    "Architecture_Block",
    "Design_Spec",
    "Verification",
    "Issue",
    "Decision",
    "Component",
    "Risk",
]
LifecycleState = Literal["draft", "active", "deprecated", "superseded"]
CreatedBy = Literal["source", "ai", "human"]
EdgeRelation = Literal[
    "satisfies",
    "verifies",
    "derives",
    "implements",
    "affects",
    "blocks",
    "conflicts_with",
    "supersedes",
    "decides",
]
ApprovalStatus = Literal["pending", "approved", "rejected", "modified", "expired"]
FindingType = Literal[
    "orphan_node",
    "missing_verification",
    "missing_implementation",
    "conflict",
    "cross_domain_hidden",
    "stale_trace",
    "weak_evidence",
    "policy_violation",
]
Severity = Literal["critical", "high", "medium", "low"]
DetectionMethod = Literal["rule", "llm", "hybrid"]
FindingStatus = Literal["open", "acknowledged", "resolved", "dismissed"]


class ContractModel(BaseModel):
    """Base model for strict-ish API contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class EvidenceSpan(ContractModel):
    """Traceable source evidence span."""

    artifact_id: str
    source_url: str | HttpUrl
    quote_hash: str
    extracted_text_preview: str = Field(min_length=1, max_length=500)
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    section_path: str | None = None
    table_cell_ref: str | None = None
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_offsets(self) -> "EvidenceSpan":
        """Require ordered offsets when both are present."""
        if (
            self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset < self.start_offset
        ):
            raise ValueError("end_offset must be greater than or equal to start_offset")
        return self


class SourceArtifact(ContractModel):
    """Normalized source artifact from JIRA, Confluence, Email, or dummy fixtures."""

    artifact_id: str
    source_type: SourceType
    source_url: str | HttpUrl
    external_id: str
    project_key: str
    title: str = Field(min_length=1)
    body_text_ref: str
    author_id: str | None = None
    created_at: datetime
    updated_at: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str
    access_scope: list[str] = Field(default_factory=list)
    data_classification: DataClassification = "public_internal"
    schema_version: str = SCHEMA_VERSION


class ArtifactChunk(ContractModel):
    """Chunk produced from a source artifact."""

    chunk_id: str
    artifact_id: str
    project_key: str
    text: str = Field(min_length=1)
    index: int = Field(ge=0)
    evidence: EvidenceSpan
    content_hash: str
    metadata: dict[str, str] = Field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION


class OntologyNode(ContractModel):
    """Traceability graph node."""

    node_id: str
    node_type: NodeType
    name: str = Field(min_length=1)
    description: str
    project_key: str
    domain: str | None = None
    lifecycle_state: LifecycleState = "active"
    source_artifact_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceSpan] = Field(min_length=1)
    created_by: CreatedBy
    confidence_score: float = Field(ge=0.0, le=1.0)
    version: int = Field(default=1, ge=1)
    schema_version: str = SCHEMA_VERSION


class TraceabilityEdge(ContractModel):
    """Traceability graph relation or pending relation proposal."""

    edge_id: str
    source_node_id: str
    target_node_id: str
    relation: EdgeRelation
    reasoning: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(min_length=1)
    is_inferred: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    approval_status: ApprovalStatus = "pending"
    approved_by: str | None = None
    approved_at: datetime | None = None
    version: int = Field(default=1, ge=1)
    schema_version: str = SCHEMA_VERSION

    @model_validator(mode="after")
    def validate_approval_fields(self) -> "TraceabilityEdge":
        """Require approver metadata only for approved edges."""
        if self.approval_status == "approved" and not self.approved_by:
            raise ValueError("approved edges require approved_by")
        return self


class Finding(ContractModel):
    """Gap, conflict, policy, or traceability finding."""

    finding_id: str
    finding_type: FindingType
    severity: Severity
    affected_node_ids: list[str] = Field(default_factory=list)
    affected_edge_ids: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)
    suggested_action: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    detection_method: DetectionMethod
    approval_status: FindingStatus = "open"
    rule_id: str | None = None
    schema_version: str = SCHEMA_VERSION

    @field_validator("affected_edge_ids", "affected_node_ids")
    @classmethod
    def require_some_affected_item(cls, value: list[str]) -> list[str]:
        """Keep list values normalized."""
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def validate_affected_items(self) -> "Finding":
        """Require at least one affected node or edge."""
        if not self.affected_node_ids and not self.affected_edge_ids:
            raise ValueError("finding requires at least one affected node or edge")
        return self

