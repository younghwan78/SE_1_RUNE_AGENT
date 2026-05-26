"""Tests for rule-only SoC axis classification."""

from collections import defaultdict
from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.fixtures.soc_knowledge import (
    load_soc_ground_truth_classifications,
    load_soc_seed_artifacts,
)
from req_tracker.ingestion.soc_classification import GatewaySocAxisClassifier, classify_soc_axes
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)


class CapturingProvider:
    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.requests: list[ModelRequest] = []

    def complete(
        self,
        request: ModelRequest,
        active_profile: ModelProfile,
        active_prompt: PromptVersion,
    ) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(
            model_profile_id=active_profile.model_profile_id,
            prompt_version_id=active_prompt.prompt_version_id,
            output=self.output,
            input_tokens=21,
            output_tokens=13,
            latency_ms=18,
        )


def test_rule_classifier_extracts_project_v_level_concern_and_component() -> None:
    artifact = RawSourceArtifact(
        external_id="SOC1-JIRA-001",
        source_type="jira",
        source_url="https://jira.example/browse/SOC1-JIRA-001",
        project_key="SOC-N-1",
        title="Camera DVFS reduces power in architecture",
        body_text="Architecture page notes camera power consumption improvement.",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        labels=["level/L2", "concern/power", "component/camera"],
        metadata={"soc_fixture_seed": True},
    )

    classifications = classify_soc_axes(
        artifact,
        run_id="run_soc_cls_001",
        step_id="step_soc_cls_001",
    )
    values_by_axis = defaultdict(set)
    for classification in classifications:
        values_by_axis[classification.axis].add(classification.value)

    assert values_by_axis["project"] == {"SOC-N-1"}
    assert values_by_axis["v_level"] == {"L2"}
    assert values_by_axis["concern"] == {"Power"}
    assert values_by_axis["component"] == {"Camera"}
    assert all(classification.source == "rule" for classification in classifications)
    assert all(classification.status == "baseline" for classification in classifications)


def test_rule_classifier_handles_memory_as_concern_and_component() -> None:
    artifact = RawSourceArtifact(
        external_id="SOC2-JIRA-006",
        source_type="jira",
        source_url="https://jira.example/browse/SOC2-JIRA-006",
        project_key="SOC-N-2",
        title="Memory subsystem footprint request",
        body_text="Customer asks to reduce memory usage in the memory subsystem.",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        labels=["level/L1", "concern/memory", "component/memory_subsystem"],
        metadata={"soc_fixture_seed": True},
    )

    classifications = classify_soc_axes(
        artifact,
        run_id="run_soc_cls_001",
        step_id="step_soc_cls_001",
    )
    values_by_axis = defaultdict(set)
    for classification in classifications:
        values_by_axis[classification.axis].add(classification.value)

    assert "Memory" in values_by_axis["concern"]
    assert "MemorySubsystem" in values_by_axis["component"]


def test_rule_classifier_matches_seed_fixture_ground_truth_above_stage_c_threshold() -> None:
    artifacts = load_soc_seed_artifacts()
    expected = {
        (classification.entity_id, classification.axis, classification.value)
        for classification in load_soc_ground_truth_classifications()
    }
    actual = {
        (classification.entity_id, classification.axis, classification.value)
        for artifact in artifacts
        for classification in classify_soc_axes(
            artifact,
            run_id="run_soc_cls_seed",
            step_id="step_soc_cls_seed",
        )
    }

    recall = len(expected & actual) / len(expected)

    assert recall >= 0.85


def test_gateway_classifier_enrichment_returns_pending_claude_proposals() -> None:
    traces = InMemoryTraceRepository()
    provider = CapturingProvider(
        {
            "classifications": [
                {
                    "entity_id": "SOC1-JIRA-001",
                    "axis": "concern",
                    "value": "Performance",
                    "confidence": 0.72,
                    "evidence_ref": "body:latency",
                }
            ]
        }
    )
    artifact = RawSourceArtifact(
        external_id="SOC1-JIRA-001",
        source_type="jira",
        source_url="https://jira.example/browse/SOC1-JIRA-001",
        project_key="SOC-N-1",
        title="Camera latency follow-up",
        body_text="Claude should review whether camera latency indicates Performance.",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        labels=["level/L3", "component/camera"],
        metadata={"soc_fixture_seed": True},
    )
    baseline = classify_soc_axes(
        artifact,
        run_id="run_soc_cls_001",
        step_id="rule_step",
    )
    classifier = GatewaySocAxisClassifier(
        client=ModelGatewayClient(
            provider=provider,
            profile=_profile(),
            prompt=_prompt(),
            trace_repo=traces,
        ),
        model_profile_id="dummy-soc-classifier",
        prompt_version_id="pv_soc_axis_classification_v1",
    )

    proposals = classifier.enrich_artifact(
        artifact,
        baseline_classifications=baseline,
        run_id="run_soc_cls_001",
        step_id="claude_enrichment_step",
    )

    assert len(proposals) == 1
    assert proposals[0].source == "claude"
    assert proposals[0].status == "pending"
    assert proposals[0].axis == "concern"
    assert proposals[0].value == "Performance"
    assert proposals[0].classification_id.startswith("soc_cls_")
    assert provider.requests[0].model_profile_id == "dummy-soc-classifier"
    assert provider.requests[0].prompt_version_id == "pv_soc_axis_classification_v1"
    assert provider.requests[0].payload["task"] == "soc_axis_classification"
    assert provider.requests[0].payload["artifact"]["source_url"] == artifact.source_url
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "claude_enrichment_step"
    assert trace.validation_status == "passed"


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="dummy-soc-classifier",
        provider="dummy",
        model_name="dummy-soc-classifier",
        endpoint_alias="dummy",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def _prompt() -> PromptVersion:
    return PromptVersion(
        prompt_version_id="pv_soc_axis_classification_v1",
        task_name="soc_axis_classification",
        template="Review SoC axis classifications and return pending proposals.",
        schema_version_ref="soc.v0_1.axis_classification_batch",
        retrieval_policy_id="soc_seed",
        created_by="tester",
        status="active",
    )
