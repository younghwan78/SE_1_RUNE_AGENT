"""Dummy analysis pipeline integration tests."""

import pytest

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult, SourceScope, SyncCursor
from req_tracker.approvals.models import ApprovalDecision
from req_tracker.approvals.service import ApprovalService
from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.graph.memory_backend import MemoryGraphBackend
from req_tracker.ingestion.masking import MaskingPolicyViolationError
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
    assert {approval.risk_level for approval in result.approvals} <= {
        "low",
        "medium",
        "high",
        "critical",
    }
    assert graph.approved_edges() == []
    assert result.run.model_profile_id == "dummy-local"
    assert result.run.prompt_version_ids == [
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    ]
    assert len(result.run.input_snapshot_ids) == len(result.artifacts)
    assert result.run.input_snapshot_ids[0].startswith("src_")
    assert len(workflow.traces.llm_calls) == 3
    assert {call.prompt_version_id for call in workflow.traces.llm_calls.values()} == {
        "pv_node_extraction_v1",
        "pv_edge_linking_v1",
        "pv_finding_reasoning_v1",
    }
    assert {
        call.validation_status for call in workflow.traces.llm_calls.values()
    } == {"passed"}
    llm_step = next(
        step for step in result.steps if step.stage_name == "llm_assisted_reasoning"
    )
    assert llm_step.validation_result["status"] == "passed"

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


def test_confluence_version_change_is_routed_to_stale_finding(tmp_path) -> None:  # type: ignore[no-untyped-def]
    graph = MemoryGraphBackend()
    approvals = ApprovalService()
    workflow = LocalAnalysisWorkflow(
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path),
        graph=graph,
        vector=MemoryVectorBackend(),
        approvals=approvals,
        source_adapter=_ChangedConfluenceAdapter(),
    )

    result = workflow.run(run_id="run_it_conf_stale", project_key="RUNE_CAM_ALPHA")

    stale = [
        finding
        for finding in result.findings
        if finding.rule_id == "CONFLUENCE_PAGE_VERSION_CHANGED"
    ]
    assert len(stale) == 1
    assert stale[0].finding_type == "stale_trace"
    assert stale[0].affected_node_ids == ["node_RUNE_CAM_ALPHA_CONF_STALE_1"]
    assert "version 3 to 4" in stale[0].description


def test_masking_policy_violation_blocks_analysis_and_routes_security_review(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    graph = MemoryGraphBackend()
    workflow = LocalAnalysisWorkflow(
        traces=InMemoryTraceRepository(),
        artifact_store=LocalArtifactStore(tmp_path),
        graph=graph,
        vector=MemoryVectorBackend(),
        approvals=ApprovalService(),
        source_adapter=_ForbiddenPatternAdapter(),
    )

    with pytest.raises(MaskingPolicyViolationError, match="MASKING_POLICY_VIOLATION"):
        workflow.run(run_id="run_it_masking_violation", project_key="RUNE_CAM_ALPHA")

    run = workflow.traces.runs["run_it_masking_violation"]
    assert run.status == "failed"
    assert run.failure_code == "MASKING_POLICY_VIOLATION"
    assert run.failure_message is not None
    assert "security review" in run.failure_message
    steps = {step.stage_name: step for step in workflow.traces.list_steps(run.run_id)}
    assert steps["mask_chunk"].status == "failed"
    assert steps["mask_chunk"].validation_status == "failed"
    assert steps["mask_chunk"].validation_result["security_review_required"] is True
    assert "extract_nodes" not in steps
    assert graph.nodes == {}


class _ChangedConfluenceAdapter:
    source_type = "confluence"

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        if cursor is not None:
            return SourceFetchResult(artifacts=[], next_cursor=None)
        return SourceFetchResult(
            artifacts=[
                RawSourceArtifact(
                    external_id="CONF-STALE-1",
                    source_type="confluence",
                    source_url="https://confluence.example.com/wiki/pages/CONF-STALE-1",
                    project_key=scope.project_key,
                    title="Camera Architecture",
                    body_text="Design page changed from version 3 to 4.",
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-04T00:00:00Z",
                    metadata={
                        "mbse_type": "Design_Spec",
                        "version_number": 4,
                        "previous_version_number": 3,
                    },
                )
            ],
            next_cursor=None,
        )


class _ForbiddenPatternAdapter:
    source_type = "dummy"

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        if cursor is not None:
            return SourceFetchResult(artifacts=[], next_cursor=None)
        return SourceFetchResult(
            artifacts=[
                RawSourceArtifact(
                    external_id="SEC-BLOCK-1",
                    source_type="dummy",
                    source_url="dummy://security/SEC-BLOCK-1",
                    project_key=scope.project_key,
                    title="Unmasked source-specific secret",
                    body_text="Requirement text includes PROJECT-SECRET-123 before review.",
                    created_at="2026-01-01T00:00:00Z",
                    updated_at="2026-01-02T00:00:00Z",
                    metadata={
                        "mbse_type": "Requirement",
                        "forbidden_patterns": [r"PROJECT-SECRET-\d+"],
                    },
                )
            ],
            next_cursor=None,
        )
