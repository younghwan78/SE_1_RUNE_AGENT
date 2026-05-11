"""Contract tests for core Pydantic models."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from req_tracker.approvals.models import ApprovalItem, GraphDelta, GraphDeltaOperation
from req_tracker.debug.models import AgentRun, AgentStepTrace, LLMCallTrace
from req_tracker.feedback.models import FeedbackEvent, ImprovementCandidate
from req_tracker.model_gateway.models import ModelProfile, PromptVersion
from req_tracker.ontology.models import (
    ArtifactChunk,
    EvidenceSpan,
    Finding,
    OntologyNode,
    SourceArtifact,
    TraceabilityEdge,
)


def evidence() -> EvidenceSpan:
    return EvidenceSpan(
        artifact_id="src_dummy_cam_req_001",
        source_url="dummy://jira/CAM-REQ-001",
        quote_hash="hash_quote",
        extracted_text_preview="Camera shall support 4K60 latency below 100 ms.",
        start_offset=0,
        end_offset=52,
    )


def test_source_artifact_round_trip() -> None:
    artifact = SourceArtifact(
        artifact_id="src_dummy_cam_req_001",
        source_type="dummy",
        source_url="dummy://jira/CAM-REQ-001",
        external_id="CAM-REQ-001",
        project_key="RUNE_CAM_ALPHA",
        title="4K60 latency requirement",
        body_text_ref="artifact://body/CAM-REQ-001",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        content_hash="hash_body",
        access_scope=["project:RUNE_CAM_ALPHA"],
    )
    dumped = artifact.model_dump(mode="json")
    assert SourceArtifact.model_validate(dumped).artifact_id == artifact.artifact_id


def test_ontology_node_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        OntologyNode(
            node_id="node_RUNE_CAM_ALPHA_CAM_REQ_001",
            node_type="Requirement",
            name="4K60 latency",
            description="Latency requirement",
            project_key="RUNE_CAM_ALPHA",
            evidence=[],
            created_by="source",
            confidence_score=0.9,
        )


def test_core_contracts_are_serializable() -> None:
    ev = evidence()
    chunk = ArtifactChunk(
        chunk_id="chk_src_dummy_cam_req_001_0",
        artifact_id=ev.artifact_id,
        project_key="RUNE_CAM_ALPHA",
        text="Camera shall support 4K60 latency below 100 ms.",
        index=0,
        evidence=ev,
        content_hash="hash_chunk",
    )
    node = OntologyNode(
        node_id="node_RUNE_CAM_ALPHA_CAM_REQ_001",
        node_type="Requirement",
        name="4K60 latency",
        description="Latency requirement",
        project_key="RUNE_CAM_ALPHA",
        source_artifact_ids=[ev.artifact_id],
        evidence=[ev],
        created_by="source",
        confidence_score=0.95,
    )
    edge = TraceabilityEdge(
        edge_id="edge_arch_satisfies_req",
        source_node_id="node_arch",
        target_node_id=node.node_id,
        relation="satisfies",
        reasoning="Architecture satisfies the latency requirement.",
        evidence=[ev],
        is_inferred=False,
        confidence_score=0.8,
    )
    finding = Finding(
        finding_id="fdg_missing_verification",
        finding_type="missing_verification",
        severity="high",
        affected_node_ids=[node.node_id],
        affected_edge_ids=[],
        description="Requirement has no verification.",
        suggested_action="Create a verification plan.",
        evidence=[ev],
        detection_method="rule",
        rule_id="REQ_WITHOUT_VERIFICATION",
    )
    assert chunk.model_dump(mode="json")
    assert node.model_dump(mode="json")
    assert edge.model_dump(mode="json")
    assert finding.model_dump(mode="json")


def test_debug_gateway_approval_feedback_contracts() -> None:
    run = AgentRun(
        run_id="run_001",
        run_type="analysis",
        project_key="RUNE_CAM_ALPHA",
        triggered_by="tester",
        trigger_source="manual",
    )
    step = AgentStepTrace(
        step_id="step_001",
        run_id=run.run_id,
        stage_name="extract_nodes",
        status="running",
        input_hash="hash_in",
    )
    llm = LLMCallTrace(
        llm_call_id="llm_001",
        run_id=run.run_id,
        step_id=step.step_id,
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        request_hash="hash_req",
        masked_payload_ref="artifact://masked",
        latency_ms=10,
        validation_status="passed",
    )
    model = ModelProfile(
        model_profile_id="dummy-fast",
        provider="dummy",
        model_name="dummy-fast",
        endpoint_alias="dummy",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=30,
    )
    prompt = PromptVersion(
        prompt_version_id="pv_node_v1",
        task_name="node_extraction",
        template="Extract nodes",
        schema_version_ref="ontology.v1",
        retrieval_policy_id="ret_default",
        created_by="tester",
    )
    delta = GraphDelta(
        delta_id="delta_001",
        project_key="RUNE_CAM_ALPHA",
        operations=[
            GraphDeltaOperation(
                operation="create_node",
                target_id="node_001",
                payload={"node_id": "node_001"},
            )
        ],
        created_from_run_id=run.run_id,
        created_from_step_id=step.step_id,
    )
    approval = ApprovalItem(
        approval_id="apv_001",
        project_key="RUNE_CAM_ALPHA",
        proposal_type="graph_delta",
        proposal_ref="artifact://proposal",
        graph_delta_ref=delta.delta_id,
        risk_level="medium",
        owner_role="System Architect",
        created_from_run_id=run.run_id,
        created_from_step_id=step.step_id,
        proposal_hash="hash_proposal",
    )
    feedback = FeedbackEvent(
        feedback_id="fb_001",
        target_type="edge",
        target_id="edge_001",
        action="rejected",
        user_id="reviewer",
        user_role="System Architect",
        reason_code="wrong_relation",
        model_profile_id=model.model_profile_id,
        prompt_version_id=prompt.prompt_version_id,
    )
    for item in (run, step, llm, model, prompt, delta, approval, feedback):
        assert item.model_dump(mode="json")


def test_feedback_accepts_command_style_taxonomy_aliases() -> None:
    feedback = FeedbackEvent(
        feedback_id="fb_alias_001",
        target_type="edge",
        target_id="edge_alias_001",
        action="mark low quality",
        user_id="reviewer",
        user_role="System Architect",
        reason_code="security concern",
    )

    assert feedback.action == "marked_low_quality"
    assert feedback.reason_code == "security_concern"


def test_improvement_candidate_accepts_planned_candidate_types() -> None:
    prompt_example = ImprovementCandidate(
        candidate_id="imp_few_shot_001",
        candidate_type="few_shot_example",
        source_feedback_ids=["fb_001"],
        proposed_change_summary="Add a reviewed edge-linking example to the eval set.",
        before_version_id="local_active",
        after_version_ref="draft://few_shot_example/wrong_relation/001",
    )
    ontology = ImprovementCandidate(
        candidate_id="imp_ontology_001",
        candidate_type="ontology_normalization",
        source_feedback_ids=["fb_002"],
        proposed_change_summary="Normalize recurring node type corrections.",
        before_version_id="local_active",
        after_version_ref="draft://ontology_normalization/wrong_node_type/001",
    )

    assert prompt_example.candidate_type == "few_shot_example"
    assert ontology.candidate_type == "ontology_normalization"


def test_invalid_confidence_is_rejected() -> None:
    with pytest.raises(ValidationError):
        OntologyNode(
            node_id="node_bad",
            node_type="Requirement",
            name="Bad confidence",
            description="Invalid confidence",
            project_key="RUNE_CAM_ALPHA",
            evidence=[evidence()],
            created_by="source",
            confidence_score=1.5,
        )
