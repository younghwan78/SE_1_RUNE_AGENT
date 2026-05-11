"""Audit event contracts."""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

AuditAction = Literal[
    "run_started",
    "run_completed",
    "approval_decided",
    "feedback_recorded",
    "finding_status_changed",
    "model_profile_activated",
    "prompt_version_activated",
    "debug_artifact_read",
    "schedule_configured",
    "schedule_run_now",
    "audit_archive_pruned",
]
AuditOutcome = Literal["succeeded", "failed", "blocked"]


class AuditEvent(BaseModel):
    """Immutable audit event for operator and compliance review."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    audit_id: str
    action: AuditAction
    actor_id: str
    actor_role: str | None = None
    project_key: str | None = None
    target_type: str
    target_id: str
    outcome: AuditOutcome = "succeeded"
    reason_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SCHEMA_VERSION


class AuditRetentionPolicy(BaseModel):
    """Retention policy for local and production audit stores."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    retention_days: int = Field(default=365, ge=1)
    max_events: int = Field(default=100_000, ge=1)
    schema_version: str = SCHEMA_VERSION
