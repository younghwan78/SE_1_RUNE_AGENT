"""Tests for deterministic SoC fixture-backed query service."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.soc_service import answer_soc_query, classify_soc_slice


class SingleArtifactRetrievalBackend:
    backend_name = "postgres_hybrid"

    def __init__(self) -> None:
        self.calls: list[SocSlice] = []

    def retrieve(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        limit: int = 50,
    ) -> list[RawSourceArtifact]:
        self.calls.append(query_slice)
        return [
            RawSourceArtifact(
                external_id="SOC1-JIRA-999",
                source_type="jira",
                source_url="https://jira.example/browse/SOC1-JIRA-999",
                project_key="SOC-N-1",
                title="Injected storage-backed camera power row",
                body_text="Storage-backed retrieval supplied Camera Power evidence.",
                created_at="2026-02-01T00:00:00+00:00",
                updated_at="2026-02-02T00:00:00+00:00",
                labels=["jira", "level/L2", "concern/power", "component/camera"],
                metadata={
                    "soc_axes": {
                        "v_level": "L2",
                        "concerns": ["Power"],
                        "components": ["Camera"],
                    }
                },
            )
        ]


def test_slice_classifier_routes_topic_intersection_from_natural_language() -> None:
    query_slice = classify_soc_slice("Camera shot 성능 이슈는 무엇이 있었나?")

    assert query_slice.pattern == "topic_intersection"
    assert query_slice.concerns == ["Performance"]
    assert query_slice.components == ["Camera"]
    assert "shot" in query_slice.keywords


def test_answer_concern_slice_returns_sourced_items() -> None:
    answer = answer_soc_query(
        user_query="이전 과제에서 power 관련 활동은?",
        user_id="architect_01",
        session_id="session_001",
    )

    assert answer.confidence == "high"
    assert answer.items
    assert {item.sources[0].type for item in answer.items} >= {"jira", "confluence", "email"}
    assert all(item.sources for item in answer.items)
    assert all(
        source.url.startswith("https://")
        for item in answer.items
        for source in item.sources
    )
    assert all("Power" in item.concern for item in answer.items)


def test_answer_lifecycle_trace_returns_timeline_for_artifact() -> None:
    answer = answer_soc_query(
        user_query="SOC1-JIRA-001 lifecycle를 보여줘",
        user_id="architect_01",
        session_id="session_001",
    )

    assert [item.sources[0].key for item in answer.items] == ["SOC1-JIRA-001"]
    assert [event.change_type for event in answer.timeline] == ["created", "updated"]
    assert all(event.entity_id == "SOC1-JIRA-001" for event in answer.timeline)


def test_answer_unknown_query_gracefully_returns_no_items() -> None:
    answer = answer_soc_query(
        user_query="Bluetooth 관련 이슈가 있었나?",
        user_id="architect_01",
        session_id="session_001",
    )

    assert answer.items == []
    assert answer.confidence == "low"
    assert "찾지 못함" in answer.summary
    assert "no_candidates" in answer.quality_signals


def test_answer_persists_reasoning_log_when_artifact_store_is_provided(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path)

    answer = answer_soc_query(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        query_id="soc_query_reasoning_001",
        artifact_store=store,
    )

    reasoning_log = store.read_json(answer.reasoning_log_ref)

    assert reasoning_log["query"]["query_id"] == "soc_query_reasoning_001"
    assert reasoning_log["slice"]["pattern"] == "topic_intersection"
    assert reasoning_log["retrieval"]["candidate_artifact_ids"]
    assert reasoning_log["answer"]["item_count"] == len(answer.items)
    assert reasoning_log["tool_trace"][0]["tool"] == "classify_soc_slice"


def test_answer_uses_injected_retrieval_backend_and_records_backend_name(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path)
    retrieval_backend = SingleArtifactRetrievalBackend()

    answer = answer_soc_query(
        user_query="Camera power 관련 storage-backed 항목은?",
        user_id="architect_01",
        session_id="session_001",
        query_id="soc_query_storage_backend_001",
        query_slice=SocSlice(
            pattern="topic_intersection",
            project_keys=["SOC-N-1"],
            concerns=["Power"],
            components=["Camera"],
        ),
        retrieval_backend=retrieval_backend,
        artifact_store=store,
    )

    reasoning_log = store.read_json(answer.reasoning_log_ref)

    assert [item.sources[0].key for item in answer.items] == ["SOC1-JIRA-999"]
    assert retrieval_backend.calls
    assert reasoning_log["retrieval"]["backend"] == "postgres_hybrid"


def test_answer_records_query_run_and_step_lineage() -> None:
    traces = InMemoryTraceRepository()

    answer = answer_soc_query(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        query_id="soc_query_trace_001",
        current_project="SOC-N-1",
        trace_repo=traces,
    )

    run = traces.runs["soc_query_trace_001"]
    assert run.run_type == "query"
    assert run.project_key == "SOC-N-1"
    assert run.triggered_by == "architect_01"
    assert run.status == "succeeded"
    assert {
        step.stage_name
        for step in traces.list_steps("soc_query_trace_001")
    } >= {
        "soc_query_received",
        "soc_slice_planning",
        "soc_seed_retrieval",
        "soc_answer_projection",
    }
    assert all(step.status == "succeeded" for step in traces.list_steps(answer.query_id))
