"""Source adapter contracts."""

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
    source_warnings: list[str] = Field(default_factory=list)
    partial_failure: bool = False


class SourceAdapter(Protocol):
    """Source adapter protocol."""

    source_type: SourceType

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch source artifacts incrementally."""

