"""Scheduler contracts."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"


class ScheduleConfig(BaseModel):
    """Periodic analysis schedule configuration."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    enabled: bool = False
    interval_seconds: int = Field(default=3600, ge=1)
    project_key: str = "RUNE_CAM_ALPHA"
    scenario: str = "RUNE_MULTI_SOURCE"
    run_id_prefix: str = "sched"
    lease_name: str = "rune-periodic-analysis"
    lease_ttl_seconds: int = Field(default=300, ge=30)
    schema_version: str = SCHEMA_VERSION


class ScheduleStatus(BaseModel):
    """Current scheduler status."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    running: bool
    interval_seconds: int
    project_key: str
    scenario: str
    last_run_id: str | None = None
    last_started_at: datetime | None = None
    last_completed_at: datetime | None = None
    last_error: str | None = None
    next_run_at: datetime | None = None
    runs_started: int = Field(default=0, ge=0)
    lease_name: str
    lease_owner_id: str
    lease_enabled: bool
    lease_skips: int = Field(default=0, ge=0)
    schema_version: str = SCHEMA_VERSION


class ScheduledRunResult(BaseModel):
    """Result of a scheduler-triggered run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    error: str | None = None
    schema_version: str = SCHEMA_VERSION
