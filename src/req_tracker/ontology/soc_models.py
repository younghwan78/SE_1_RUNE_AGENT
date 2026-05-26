"""SoC Knowledge PoC contracts.

These models keep the SoC-specific slice-query layer separate from the approved
MBSE graph contracts while preserving run, step, source, and evidence lineage.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from req_tracker.ontology.models import SourceType

SOC_SCHEMA_VERSION = "soc-v0.1"

AxisType = Literal["project", "v_level", "concern", "component"]
ClassificationSource = Literal["rule", "claude", "manual", "fixture"]
ClassificationStatus = Literal["baseline", "pending", "approved", "rejected"]
SocEntityType = Literal["Artifact", "Person"]
SocRelationType = Literal["mentions", "authoredBy"]
RerankSource = Literal["rule", "cross_encoder", "claude", "fixture"]
VModelLevel = Literal["L0", "L1", "L2", "L3", "L4", "L5"]
SocSlicePattern = Literal[
    "concern_slice",
    "topic_intersection",
    "timeline_slice",
    "lifecycle_trace",
    "unknown",
]
SocAnswerConfidence = Literal["low", "medium", "high"]
SocQueryToolName = Literal[
    "fixture_axis_filter",
    "keyword_search",
    "event_log",
    "get_artifact",
    "answer_projection",
    "graph_query",
    "vector_search",
    "rerank",
]


class SocContractModel(BaseModel):
    """Base model for strict SoC PoC contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SocAxisClassification(SocContractModel):
    """One Project/V-Level/Concern/Component classification for an artifact."""

    classification_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    axis: AxisType
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    source: ClassificationSource
    status: ClassificationStatus
    evidence_ref: str | None = None
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SOC_SCHEMA_VERSION


class SocAxisClassificationSuggestion(SocContractModel):
    """Model-proposed SoC axis classification before approval or baseline use."""

    entity_id: str = Field(min_length=1)
    axis: AxisType
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ref: str | None = None


class SocAxisClassificationBatch(SocContractModel):
    """Structured model-gateway output for classifier enrichment."""

    classifications: list[SocAxisClassificationSuggestion] = Field(default_factory=list)


class SocLifecycleEvent(SocContractModel):
    """Append-only lifecycle event extracted from JIRA, Confluence, or Email evidence."""

    event_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    timestamp: datetime
    change_type: str = Field(min_length=1)
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    source: str = Field(min_length=1)
    source_url: str | None = None
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    schema_version: str = SOC_SCHEMA_VERSION


class SocExtractedEntity(SocContractModel):
    """Side-car entity extracted from a SoC artifact without committing graph truth."""

    entity_id: str = Field(min_length=1)
    entity_type: SocEntityType
    value: str = Field(min_length=1)
    source_artifact_id: str = Field(min_length=1)
    evidence_ref: str = Field(min_length=1)
    source: ClassificationSource
    status: ClassificationStatus
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SOC_SCHEMA_VERSION


class SocSemanticRelation(SocContractModel):
    """Side-car semantic relation candidate derived from deterministic evidence."""

    relation_id: str = Field(min_length=1)
    relation_type: SocRelationType
    source_entity_id: str = Field(min_length=1)
    target_entity_id: str = Field(min_length=1)
    source_entity_type: SocEntityType
    target_entity_type: SocEntityType
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_ref: str = Field(min_length=1)
    source: ClassificationSource
    status: ClassificationStatus
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: str = SOC_SCHEMA_VERSION


class SocSlice(SocContractModel):
    """Structured slice plan produced from a natural-language SoC knowledge query."""

    pattern: SocSlicePattern
    project_keys: list[str] = Field(default_factory=list)
    v_levels: list[VModelLevel] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
    lifecycle_states: list[str] = Field(default_factory=list)
    artifact_id: str | None = None
    keywords: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_selector(self) -> "SocSlice":
        """Reject empty slice plans unless they are explicitly unknown."""
        if self.pattern == "unknown":
            return self
        if (
            self.project_keys
            or self.v_levels
            or self.concerns
            or self.components
            or self.lifecycle_states
            or self.artifact_id
            or self.keywords
        ):
            return self
        raise ValueError("SoC slice requires at least one selector")


class SocQueryToolCall(SocContractModel):
    """One whitelisted retrieval or answer tool call in a SoC query plan."""

    call_id: str = Field(min_length=1)
    tool: SocQueryToolName
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_raw_queries(self) -> "SocQueryToolCall":
        """Keep model-generated plans away from executable SQL/Cypher strings."""
        forbidden = _find_forbidden_query_key(self.arguments)
        if forbidden is not None:
            raise ValueError(f"raw query argument is not allowed: {forbidden}")
        return self


class SocQueryPlan(SocContractModel):
    """Typed plan from a natural-language SoC slice to whitelisted tool calls."""

    plan_id: str = Field(min_length=1)
    pattern: SocSlicePattern
    slice: SocSlice
    tool_calls: list[SocQueryToolCall] = Field(default_factory=list)
    rationale: str = ""
    schema_version: str = SOC_SCHEMA_VERSION

    @model_validator(mode="after")
    def require_answer_projection_for_known_slice(self) -> "SocQueryPlan":
        """Known queries should finish with an answer projection step."""
        if self.pattern != "unknown" and not any(
            call.tool == "answer_projection" for call in self.tool_calls
        ):
            raise ValueError("known SoC query plan requires answer_projection")
        return self


class SocRerankItem(SocContractModel):
    """One candidate score produced by a SoC reranker."""

    artifact_id: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    source: RerankSource
    rationale: str = ""


class SocRerankResult(SocContractModel):
    """Structured rerank output for query candidate ordering."""

    query_id: str = Field(min_length=1)
    ranked_items: list[SocRerankItem] = Field(default_factory=list)
    schema_version: str = SOC_SCHEMA_VERSION

    @model_validator(mode="after")
    def require_unique_candidate_ids(self) -> "SocRerankResult":
        """Avoid ambiguous duplicate candidate scores."""
        seen: set[str] = set()
        for item in self.ranked_items:
            if item.artifact_id in seen:
                raise ValueError(f"duplicate rerank candidate: {item.artifact_id}")
            seen.add(item.artifact_id)
        return self


class SocQueryRequest(SocContractModel):
    """User-facing SoC knowledge query request."""

    query_id: str = Field(min_length=1)
    user_query: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    current_project: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)
    slice: SocSlice | None = None
    schema_version: str = SOC_SCHEMA_VERSION


def _find_forbidden_query_key(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {"sql", "cypher", "raw_query"}:
                return normalized_key
            nested = _find_forbidden_query_key(item)
            if nested is not None:
                return nested
    if isinstance(value, list):
        for item in value:
            nested = _find_forbidden_query_key(item)
            if nested is not None:
                return nested
    return None


class SocAnswerSource(SocContractModel):
    """Source link attached to every answer item."""

    type: SourceType
    key: str | None = None
    url: str = Field(min_length=1)


class SocAnswerItem(SocContractModel):
    """One sourced item in a SoC knowledge answer."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    sources: list[SocAnswerSource] = Field(min_length=1)
    level: VModelLevel | None = None
    concern: list[str] = Field(default_factory=list)
    component: list[str] = Field(default_factory=list)


class SocAnswer(SocContractModel):
    """Structured SoC query answer returned to UI clients."""

    query_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    items: list[SocAnswerItem]
    timeline: list[SocLifecycleEvent] = Field(default_factory=list)
    confidence: SocAnswerConfidence
    reasoning_log_ref: str = Field(min_length=1)
    quality_signals: list[str] = Field(default_factory=list)
    schema_version: str = SOC_SCHEMA_VERSION


class SocGroundTruthQuery(SocContractModel):
    """Ground-truth query case for fixture-first SoC query evaluation."""

    q_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    slice: SocSlice
    expected_artifact_ids: list[str] = Field(default_factory=list)
    expected_source_urls: list[str] = Field(default_factory=list)
    schema_version: str = SOC_SCHEMA_VERSION
