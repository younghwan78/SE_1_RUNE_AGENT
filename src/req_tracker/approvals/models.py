"""Approval and graph delta contracts."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

ProposalType = Literal["node", "edge", "finding", "graph_delta"]
ApprovalItemStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "modified_approved",
    "held",
    "stale",
]
RiskLevel = Literal["critical", "high", "medium", "low"]
DecisionAction = Literal["approve", "reject", "modify", "hold"]
GraphOperation = Literal["create_node", "update_node", "create_edge", "update_edge", "expire_edge"]


class ApprovalModel(BaseModel):
    """Base model for approval contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class GraphDeltaOperation(ApprovalModel):
    """One proposed graph mutation."""

    operation: GraphOperation
    target_id: str
    payload: dict[str, Any]
    schema_version: str = SCHEMA_VERSION


class GraphDelta(ApprovalModel):
    """Set of graph operations that must be approved before commit."""

    delta_id: str
    project_key: str
    operations: list[GraphDeltaOperation] = Field(default_factory=list)
    created_from_run_id: str
    created_from_step_id: str
    schema_version: str = SCHEMA_VERSION


class ApprovalItem(ApprovalModel):
    """Human approval queue item."""

    approval_id: str
    project_key: str
    proposal_type: ProposalType
    proposal_ref: str
    graph_delta_ref: str | None = None
    status: ApprovalItemStatus = "pending"
    risk_level: RiskLevel
    owner_role: str
    created_from_run_id: str
    created_from_step_id: str
    proposal_hash: str
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SCHEMA_VERSION


class ApprovalDecision(ApprovalModel):
    """Reviewer decision for an approval item."""

    approval_id: str
    action: DecisionAction
    decided_by: str
    expected_version: int | None = Field(default=None, ge=1)
    expected_proposal_hash: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correction_payload: dict[str, Any] | None = None
    reason_code: str | None = None
    schema_version: str = SCHEMA_VERSION
