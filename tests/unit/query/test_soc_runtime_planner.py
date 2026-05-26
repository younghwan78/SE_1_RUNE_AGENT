"""Runtime wiring tests for SoC query slice planners."""

from pathlib import Path

from req_tracker.config.settings import Settings
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.query.reranking import (
    CrossEncoderSocReranker,
    GatewaySocReranker,
    LexicalSocReranker,
)
from req_tracker.query.retrieval import PostgresHybridSocRetrievalBackend
from req_tracker.query.soc_orchestration import (
    GatewaySocAnswerAssembler,
    GatewaySocQueryToolPlanner,
)
from req_tracker.query.soc_planner import GatewaySocSlicePlanner
from req_tracker.query.soc_runtime import (
    create_soc_answer_assembler,
    create_soc_query_tool_planner,
    create_soc_reranker,
    create_soc_retrieval_backend,
    create_soc_slice_planner,
)


def test_soc_slice_planner_is_disabled_by_default(tmp_path: Path) -> None:
    planner = create_soc_slice_planner(
        settings=Settings(artifact_root=tmp_path / "artifacts"),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert planner is None


def test_soc_slice_planner_uses_model_registry_and_falls_back_to_rules(
    tmp_path: Path,
) -> None:
    traces = InMemoryTraceRepository()
    planner = create_soc_slice_planner(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_query_planner_mode="model_gateway",
            soc_query_planner_model_profile_id="dummy-local",
        ),
        traces=traces,
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(planner, GatewaySocSlicePlanner)

    query_slice = planner.plan(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        current_project="SOC-N-1",
    )

    assert query_slice.pattern == "topic_intersection"
    assert query_slice.concerns == ["Performance"]
    assert query_slice.components == ["Camera"]
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "soc_slice_planning"
    assert trace.model_profile_id == "dummy-local"
    assert trace.prompt_version_id == "pv_soc_slice_planning_v1"
    assert trace.validation_status == "failed"


def test_soc_query_tool_planner_is_disabled_by_default(tmp_path: Path) -> None:
    planner = create_soc_query_tool_planner(
        settings=Settings(artifact_root=tmp_path / "artifacts"),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert planner is None


def test_soc_query_tool_planner_uses_model_registry(tmp_path: Path) -> None:
    planner = create_soc_query_tool_planner(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_query_tool_planner_mode="model_gateway",
            soc_query_tool_planner_model_profile_id="dummy-local",
        ),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(planner, GatewaySocQueryToolPlanner)


def test_soc_answer_assembler_is_disabled_by_default(tmp_path: Path) -> None:
    assembler = create_soc_answer_assembler(
        settings=Settings(artifact_root=tmp_path / "artifacts"),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert assembler is None


def test_soc_answer_assembler_uses_model_registry(tmp_path: Path) -> None:
    assembler = create_soc_answer_assembler(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_answer_assembler_mode="model_gateway",
            soc_answer_assembler_model_profile_id="dummy-local",
        ),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(assembler, GatewaySocAnswerAssembler)


def test_soc_reranker_uses_lexical_seed_by_default(tmp_path: Path) -> None:
    reranker = create_soc_reranker(
        settings=Settings(artifact_root=tmp_path / "artifacts"),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(reranker, LexicalSocReranker)


def test_soc_reranker_uses_model_registry_when_enabled(tmp_path: Path) -> None:
    reranker = create_soc_reranker(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_reranker_mode="model_gateway",
            soc_reranker_model_profile_id="dummy-local",
        ),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(reranker, GatewaySocReranker)


def test_soc_reranker_uses_cross_encoder_when_enabled(tmp_path: Path) -> None:
    reranker = create_soc_reranker(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_reranker_mode="cross_encoder",
            soc_cross_encoder_model_name="BAAI/bge-reranker-v2-m3",
        ),
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path / "artifacts"),
    )

    assert isinstance(reranker, CrossEncoderSocReranker)
    assert reranker.model_name == "BAAI/bge-reranker-v2-m3"


def test_soc_retrieval_backend_uses_postgres_profile_when_enabled(tmp_path: Path) -> None:
    backend = create_soc_retrieval_backend(
        settings=Settings(
            artifact_root=tmp_path / "artifacts",
            soc_retrieval_backend="postgres_hybrid",
            postgres_dsn="postgresql://rune:secret@example.test/rune",
        )
    )

    assert isinstance(backend, PostgresHybridSocRetrievalBackend)
