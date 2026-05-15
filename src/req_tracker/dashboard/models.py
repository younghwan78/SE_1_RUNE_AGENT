"""Production dashboard read-model contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "v1"

DashboardHealth = Literal["healthy", "attention_required", "blocked", "unknown"]
FreshnessStatus = Literal["fresh", "stale", "warning", "failed", "disabled", "unknown"]
QueueItemType = Literal[
    "finding",
    "approval",
    "source_warning",
    "failed_run",
    "eval_gate",
]
QueuePriority = Literal["critical", "high", "medium", "low", "info"]


class DashboardModel(BaseModel):
    """Base model for dashboard API contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DashboardLastRun(DashboardModel):
    """Latest run summary for first-viewport dashboard state."""

    run_id: str
    run_type: str
    status: str
    completed_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None


class DashboardCounts(DashboardModel):
    """Key counts needed by the dashboard first viewport."""

    total_nodes: int = Field(ge=0)
    approved_edges: int = Field(ge=0)
    pending_edges: int = Field(ge=0)
    orphan_nodes: int = Field(ge=0)
    open_findings: int = Field(ge=0)
    critical_findings: int = Field(ge=0)
    high_findings: int = Field(ge=0)
    pending_approvals: int = Field(ge=0)
    feedback_events: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    source_warnings: int = Field(ge=0)


class DashboardEvalGate(DashboardModel):
    """Sanitized eval gate summary."""

    status: str
    reason: str | None = None
    eval_run_id: str | None = None


class DashboardSchedule(DashboardModel):
    """Scheduler state for dashboard summary."""

    enabled: bool
    running: bool
    last_run_id: str | None = None
    next_run_at: datetime | None = None
    last_error: str | None = None


class DashboardSummary(DashboardModel):
    """First-viewport application dashboard summary."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    generated_at: datetime
    traceability_health: DashboardHealth
    last_run: DashboardLastRun | None = None
    counts: DashboardCounts
    source_freshness: dict[str, FreshnessStatus]
    eval_gate: DashboardEvalGate
    schedule: DashboardSchedule


class WorkQueueItem(DashboardModel):
    """One actionable dashboard work item."""

    queue_id: str
    item_type: QueueItemType
    priority: QueuePriority
    status: str
    title: str
    summary: str
    project_key: str
    source_type: str | None = None
    owner_role: str | None = None
    related_run_id: str | None = None
    related_node_ids: list[str] = Field(default_factory=list)
    related_edge_ids: list[str] = Field(default_factory=list)
    related_approval_id: str | None = None
    related_finding_id: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class WorkQueueCounts(DashboardModel):
    """Work queue counts by status, priority, and source category."""

    open: int = Field(ge=0)
    critical: int = Field(ge=0)
    high: int = Field(ge=0)
    approval: int = Field(ge=0)
    finding: int = Field(ge=0)
    source_warning: int = Field(ge=0)
    failed_run: int = Field(ge=0)
    eval_gate: int = Field(ge=0)


class WorkQueueResponse(DashboardModel):
    """Prioritized work queue response."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    items: list[WorkQueueItem]
    counts: WorkQueueCounts


class SourceHealthItem(DashboardModel):
    """Source sync health item for one source/scope."""

    source_type: str
    status: FreshnessStatus
    mode: str | None = None
    last_run_id: str | None = None
    cursor_id: str | None = None
    artifact_count: int = Field(default=0, ge=0)
    warning_count: int = Field(default=0, ge=0)
    last_success_at: datetime | None = None
    stale_after_seconds: int = Field(default=86400, ge=1)
    source_warnings: list[str] = Field(default_factory=list)


class SourceHealthResponse(DashboardModel):
    """Dashboard source-health response."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    sources: list[SourceHealthItem]


class RunHealthResponse(DashboardModel):
    """Dashboard run-health response."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    latest_run: DashboardLastRun | None = None
    total_runs: int = Field(ge=0)
    failed_runs: int = Field(ge=0)
    recent_runs: list[DashboardLastRun]


class RiskSummaryResponse(DashboardModel):
    """Dashboard risk and coverage summary."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    counts: DashboardCounts
    risk_by_severity: dict[str, int]
    top_findings: list[WorkQueueItem]


class RecentActivityItem(DashboardModel):
    """Sanitized recent operational activity item."""

    activity_id: str
    action: str
    outcome: str
    actor_id: str | None = None
    target_type: str
    target_id: str
    created_at: datetime
    summary: str


class RecentActivityResponse(DashboardModel):
    """Dashboard recent activity response."""

    schema_version: str = SCHEMA_VERSION
    project_key: str
    items: list[RecentActivityItem]
