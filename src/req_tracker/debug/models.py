"""Debug and trace data contracts."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

RunType = Literal["ingestion", "analysis", "approval_commit", "eval", "replay", "improvement"]
TriggerSource = Literal["manual", "schedule", "api", "system"]
RunStatus = Literal["queued", "running", "succeeded", "failed", "cancelled", "partial"]
StepStatus = Literal["running", "succeeded", "failed", "skipped"]
ValidationStatus = Literal["not_applicable", "passed", "failed", "repaired"]


class DebugModel(BaseModel):
    """Base model for debug contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class StageArtifactRef(DebugModel):
    """Reference to a persisted stage artifact."""

    artifact_ref: str
    content_hash: str
    media_type: str = "application/json"
    schema_version: str = SCHEMA_VERSION


class AgentRun(DebugModel):
    """Agent workflow run metadata."""

    run_id: str
    run_type: RunType
    project_key: str
    triggered_by: str
    trigger_source: TriggerSource
    status: RunStatus = "queued"
    model_profile_id: str | None = None
    prompt_version_ids: list[str] = Field(default_factory=list)
    input_snapshot_ids: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    schema_version: str = SCHEMA_VERSION


class AgentStepTrace(DebugModel):
    """Trace for one workflow stage."""

    step_id: str
    run_id: str
    stage_name: str
    status: StepStatus
    input_hash: str
    output_hash: str | None = None
    output_ref: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    retry_count: int = Field(default=0, ge=0)
    error_class: str | None = None
    error_message: str | None = None
    schema_version: str = SCHEMA_VERSION


class LLMCallTrace(DebugModel):
    """Trace for one model gateway call."""

    llm_call_id: str
    run_id: str
    step_id: str
    model_profile_id: str
    prompt_version_id: str
    request_hash: str
    response_hash: str | None = None
    masked_payload_ref: str
    raw_response_ref: str | None = None
    parsed_output_ref: str | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0.0)
    latency_ms: int = Field(ge=0)
    validation_status: ValidationStatus
    retry_count: int = Field(default=0, ge=0)
    error_message: str | None = None
    schema_version: str = SCHEMA_VERSION


class ReplayRun(DebugModel):
    """Replay run metadata."""

    replay_id: str
    source_run_id: str
    replay_mode: str
    status: RunStatus = "queued"
    diff_ref: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SCHEMA_VERSION


class ReplayDiff(DebugModel):
    """Object-level replay diff summary."""

    replay_id: str
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    changed: list[str] = Field(default_factory=list)
    schema_version: str = SCHEMA_VERSION
