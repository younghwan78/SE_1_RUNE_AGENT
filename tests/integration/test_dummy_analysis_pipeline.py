"""Dummy analysis pipeline integration tests."""

from req_tracker.approvals.models import ApprovalDecision
from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.vector.memory_backend import MemoryVectorBackend
from req_tracker.workflows.analysis_graph import LocalAnalysisWorkflow


def _workflow(tmp_path) -> tuple[LocalAnalysisWorkflow, MemoryGraphBackend, ApprovalService]:  # type: ignore[no-untyped-def]
    graph = MemoryGraphBackend()
    approvals = ApprovalService()
    workflow = LocalAnalysisWorkflow(
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path),
        graph=graph,
        vector=MemoryVectorBackend(),
        approvals=approvals,
    )
    return workflow, graph, approvals


def test_dummy_analysis_creates_findings_and_approvals(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workflow, graph, approvals = _workflow(tmp_path)
    result = workflow.run(run_id="run_it_001", project_key="RUNE_CAM_ALPHA")

    assert result.run.status == "succeeded"
    assert len(result.nodes) == 10
    assert len(result.candidate_edges) >= 6
    assert any(f.finding_type == "conflict" for f in result.findings)
    assert len(result.approvals) == len(result.candidate_edges)
    assert graph.approved_edges() == []
    assert result.run.model_profile_id == "dummy-local"
    assert result.run.prompt_version_ids == ["pv_edge_linking_v1"]
    assert len(result.run.input_snapshot_ids) == len(result.artifacts)
    assert result.run.input_snapshot_ids[0].startswith("src_")
    assert len(workflow.traces.llm_calls) == 1
    assert list(workflow.traces.llm_calls.values())[0].validation_status == "passed"

    first = result.approvals[0]
    approvals.decide(
        ApprovalDecision(
            approval_id=first.approval_id,
            action="approve",
            decided_by="reviewer",
        ),
        graph,
    )
    assert len(graph.approved_edges()) == 1


def test_multi_source_dummy_analysis_keeps_source_types(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workflow, _graph, _approvals = _workflow(tmp_path)

    result = workflow.run(
        run_id="run_it_multi_001",
        project_key="RUNE_CAM_ALPHA",
        scenario="RUNE_MULTI_SOURCE",
    )

    assert result.run.status == "succeeded"
    assert len(result.nodes) > 10
    assert {artifact.source_type for artifact in result.artifacts} >= {
        "confluence",
        "email",
        "decision_archive",
    }
