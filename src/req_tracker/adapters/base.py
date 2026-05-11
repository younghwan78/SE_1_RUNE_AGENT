"""Source adapter contracts."""

from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.ontology.models import DataClassification, SourceType


class AdapterModel(BaseModel):
    """Base model for source adapter contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SourceScope(AdapterModel):
    """Scope for a source fetch."""

    project_key: str
    scenario: str = "RUNE_CAM_ALPHA"
    limit: int = Field(default=100, gt=0)


class SyncCursor(AdapterModel):
    """Incremental sync cursor."""

    offset: int = Field(default=0, ge=0)
    content_hash: str | None = None


class SourceSyncCursorState(AdapterModel):
    """Persisted source sync cursor snapshot for incremental sync debugging."""

    cursor_id: str
    source_type: SourceType
    project_key: str
    scenario: str
    run_id: str
    stage_name: str = "source_fetch"
    initial_cursor: SyncCursor | None = None
    completed_cursor: SyncCursor | None = None
    next_cursor: SyncCursor | None = None
    artifact_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    content_hash: str
    source_warnings: list[str] = Field(default_factory=list)
    partial_failure: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = "v1"


def source_sync_cursor_id(
    *,
    source_type: SourceType,
    project_key: str,
    scenario: str,
) -> str:
    """Return a stable source sync cursor id for one source/scope pair."""
    return f"src_cursor_{source_type}_{project_key}_{scenario}"


class RawSourceArtifact(AdapterModel):
    """Source-shaped artifact before normalization."""

    external_id: str
    source_type: SourceType
    source_url: str
    project_key: str
    title: str
    body_text: str
    author_id: str | None = None
    created_at: str
    updated_at: str
    labels: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    parent_id: str | None = None
    child_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    access_scope: list[str] = Field(default_factory=list)
    data_classification: DataClassification = "public_internal"


class SourceFetchResult(AdapterModel):
    """Source fetch output."""

    artifacts: list[RawSourceArtifact]
    next_cursor: SyncCursor | None
    initial_cursor: SyncCursor | None = None
    completed_cursor: SyncCursor | None = None
    page_count: int = Field(default=1, ge=0)
    source_warnings: list[str] = Field(default_factory=list)
    partial_failure: bool = False


class SourceAdapterRequestError(Exception):
    """Transport-level source request failure normalized for adapter retry policy."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
        code: str = "request_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        self.code = code

    @property
    def status_label(self) -> str:
        """Compact status/code label for warnings."""
        return str(self.status_code) if self.status_code is not None else self.code

    @property
    def is_permission_denied(self) -> bool:
        """Whether the source denied access to the requested scope."""
        return self.status_code in {401, 403}

    @property
    def is_retryable(self) -> bool:
        """Whether the request should be retried by source adapters."""
        if self.status_code in {408, 409, 425, 429}:
            return True
        if self.status_code is not None and 500 <= self.status_code <= 599:
            return True
        return self.code in {"network_error", "timeout"}


class SourceAdapter(Protocol):
    """Source adapter protocol."""

    source_type: SourceType

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch source artifacts incrementally."""
