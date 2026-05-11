"""Feedback and improvement contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "v1"

FeedbackTargetType = Literal["node", "edge", "finding", "answer", "run_step"]
FeedbackAction = Literal["approved", "rejected", "modified", "commented", "marked_low_quality"]
FeedbackReasonCode = Literal[
    "wrong_relation",
    "weak_evidence",
    "wrong_node_type",
    "duplicate",
    "missing_context",
    "wrong_severity",
    "security_concern",
    "other",
]
_ACTION_ALIASES = {
    "approve": "approved",
    "approved": "approved",
    "reject": "rejected",
    "rejected": "rejected",
    "modify": "modified",
    "modified": "modified",
    "comment": "commented",
    "commented": "commented",
    "mark_low_quality": "marked_low_quality",
    "marked_low_quality": "marked_low_quality",
}
_REASON_ALIASES = {
    "wrong_relation": "wrong_relation",
    "weak_evidence": "weak_evidence",
    "wrong_node_type": "wrong_node_type",
    "duplicate": "duplicate",
    "missing_context": "missing_context",
    "wrong_severity": "wrong_severity",
    "security_concern": "security_concern",
    "other": "other",
}
ImprovementType = Literal[
    "prompt",
    "rule",
    "retrieval_policy",
    "scoring_threshold",
    "model_profile",
]
ImprovementStatus = Literal[
    "draft",
    "eval_running",
    "review_ready",
    "approved",
    "rejected",
    "canary",
    "active",
    "rolled_back",
]


class FeedbackModel(BaseModel):
    """Base model for feedback contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class FeedbackEvent(FeedbackModel):
    """User feedback event used for evaluation and improvement."""

    feedback_id: str
    target_type: FeedbackTargetType
    target_id: str
    action: FeedbackAction
    user_id: str
    user_role: str
    reason_code: FeedbackReasonCode | None = None
    correction_text: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model_profile_id: str | None = None
    prompt_version_id: str | None = None
    schema_version: str = SCHEMA_VERSION

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, value: object) -> object:
        """Accept command-style API feedback actions while storing canonical values."""
        if not isinstance(value, str):
            return value
        normalized = _normalize_taxonomy_value(value)
        return _ACTION_ALIASES.get(normalized, value)

    @field_validator("reason_code", mode="before")
    @classmethod
    def normalize_reason_code(cls, value: object) -> object:
        """Accept human-readable reason-code aliases while storing canonical values."""
        if value is None or not isinstance(value, str):
            return value
        normalized = _normalize_taxonomy_value(value)
        return _REASON_ALIASES.get(normalized, value)


class ImprovementCandidate(FeedbackModel):
    """Controlled improvement candidate generated from feedback clusters."""

    candidate_id: str
    candidate_type: ImprovementType
    source_feedback_ids: list[str] = Field(default_factory=list)
    proposed_change_summary: str
    before_version_id: str
    after_version_ref: str
    eval_run_id: str | None = None
    status: ImprovementStatus = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    reviewed_by: str | None = None
    schema_version: str = SCHEMA_VERSION


def _normalize_taxonomy_value(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")
