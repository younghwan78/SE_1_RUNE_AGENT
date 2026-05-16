"""Dummy model gateway tests."""

import pytest
from pydantic import BaseModel, Field

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.comparison import (
    ModelGatewayCandidate,
    compare_model_gateway_candidates,
)
from req_tracker.model_gateway.dummy_provider import DummyModelProvider, DummyModelTimeoutError
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.model_gateway.policy import ModelPolicyError


class NodeExtractionOutput(BaseModel):
    node_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)


class SequencedProvider:
    def __init__(self, outputs: list[dict[str, object]]) -> None:
        self.outputs = outputs
        self.calls = 0

    def complete(
        self,
        request: ModelRequest,
        active_profile: ModelProfile,
        active_prompt: PromptVersion,
    ) -> ModelResponse:
        output = self.outputs[self.calls]
        self.calls += 1
        response = DummyModelProvider(fixtures={"selected": output}).complete(
            request.model_copy(update={"payload": {"fixture_name": "selected"}}),
            active_profile,
            active_prompt,
        )
        return response.model_copy(
            update={"input_tokens": 11, "output_tokens": 5, "cost_usd": 0.0007}
        )


def profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="dummy-fast",
        provider="dummy",
        model_name="dummy-fast",
        endpoint_alias="dummy",
        allowed_data_classes=["public_internal", "restricted"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def prompt() -> PromptVersion:
    return PromptVersion(
        prompt_version_id="pv_node_v1",
        task_name="node_extraction",
        template="Extract nodes",
        schema_version_ref="node_extraction.v1",
        retrieval_policy_id="ret_default",
        created_by="tester",
    )


def test_dummy_gateway_validates_structured_output(tmp_path) -> None:  # type: ignore[no-untyped-def]
    traces = InMemoryTraceRepository()
    provider = DummyModelProvider(
        fixtures={"valid": {"node_id": "node_001", "confidence_score": 0.9}}
    )
    client = ModelGatewayClient(
        provider=provider,
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
        artifact_store=LocalArtifactStore(tmp_path),
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "valid"},
        data_classification="public_internal",
    )

    response, parsed, validation = client.complete(
        run_id="run_001",
        step_id="step_001",
        request=request,
        response_model=NodeExtractionOutput,
    )

    assert validation.status == "passed"
    assert parsed is not None
    assert parsed.node_id == "node_001"
    assert response.raw_response_ref is not None
    assert list(traces.llm_calls.values())[0].validation_status == "passed"


def test_gateway_records_usage_metadata_from_provider() -> None:
    traces = InMemoryTraceRepository()
    client = ModelGatewayClient(
        provider=SequencedProvider([{"node_id": "node_001", "confidence_score": 0.9}]),
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "unused"},
        data_classification="public_internal",
    )

    response, _parsed, validation = client.complete(
        run_id="run_usage",
        step_id="step_usage",
        request=request,
        response_model=NodeExtractionOutput,
    )

    trace = list(traces.llm_calls.values())[0]
    assert validation.status == "passed"
    assert response.input_tokens == 11
    assert response.output_tokens == 5
    assert response.cost_usd == 0.0007
    assert trace.input_tokens == 11
    assert trace.output_tokens == 5
    assert trace.cost_usd == 0.0007


def test_dummy_gateway_records_validation_failure() -> None:
    traces = InMemoryTraceRepository()
    provider = DummyModelProvider(fixtures={"invalid": {"node_id": "node_001"}})
    client = ModelGatewayClient(
        provider=provider,
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "invalid"},
        data_classification="public_internal",
    )

    _, parsed, validation = client.complete(
        run_id="run_001",
        step_id="step_001",
        request=request,
        response_model=NodeExtractionOutput,
    )

    assert parsed is None
    assert validation.status == "failed"
    assert list(traces.llm_calls.values())[0].validation_status == "failed"


def test_model_policy_blocks_disallowed_data_class() -> None:
    client = ModelGatewayClient(
        provider=DummyModelProvider(),
        profile=profile(),
        prompt=prompt(),
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "valid"},
        data_classification="no_external_llm",
    )

    with pytest.raises(ModelPolicyError):
        client.complete(run_id="run_001", step_id="step_001", request=request)


def test_model_policy_requires_masking_and_access_for_restricted_payloads() -> None:
    client = ModelGatewayClient(
        provider=DummyModelProvider(fixtures={"valid": {"node_id": "node_001"}}),
        profile=profile(),
        prompt=prompt(),
    )
    unmasked_request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "valid", "text": "restricted project source"},
        data_classification="restricted",
    )
    masked_without_access = unmasked_request.model_copy(update={"masking_applied": True})
    allowed_request = unmasked_request.model_copy(
        update={"masking_applied": True, "access_checked": True}
    )

    with pytest.raises(ModelPolicyError, match="requires masking"):
        client.complete(
            run_id="run_restricted",
            step_id="step_restricted",
            request=unmasked_request,
        )
    with pytest.raises(ModelPolicyError, match="requires access check"):
        client.complete(
            run_id="run_restricted",
            step_id="step_restricted",
            request=masked_without_access,
        )

    response, _parsed, validation = client.complete(
        run_id="run_restricted",
        step_id="step_restricted",
        request=allowed_request,
    )

    assert validation.status == "passed"
    assert response.output == {"node_id": "node_001"}


def test_dummy_gateway_records_timeout_failure() -> None:
    traces = InMemoryTraceRepository()
    client = ModelGatewayClient(
        provider=DummyModelProvider(),
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "timeout"},
        data_classification="public_internal",
    )

    with pytest.raises(DummyModelTimeoutError):
        client.complete(run_id="run_001", step_id="step_001", request=request)

    trace = list(traces.llm_calls.values())[0]
    assert trace.validation_status == "failed"
    assert "timeout" in (trace.error_message or "")


def test_gateway_retries_structured_validation_failure() -> None:
    traces = InMemoryTraceRepository()
    provider = SequencedProvider(
        [
            {"node_id": "node_001"},
            {"node_id": "node_001", "confidence_score": 0.95},
        ]
    )
    client = ModelGatewayClient(
        provider=provider,
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
        max_validation_retries=1,
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "unused"},
        data_classification="public_internal",
    )

    _response, parsed, validation = client.complete(
        run_id="run_retry",
        step_id="step_retry",
        request=request,
        response_model=NodeExtractionOutput,
    )

    trace_values = list(traces.llm_calls.values())
    assert parsed is not None
    assert validation.status == "passed"
    assert [trace.validation_status for trace in trace_values] == ["failed", "passed"]
    assert [trace.retry_count for trace in trace_values] == [0, 1]


def test_gateway_uses_fallback_provider_after_timeout() -> None:
    traces = InMemoryTraceRepository()
    fallback_profile = profile().model_copy(update={"model_profile_id": "dummy-fallback"})
    client = ModelGatewayClient(
        provider=DummyModelProvider(),
        profile=profile(),
        prompt=prompt(),
        trace_repo=traces,
        fallback_provider=SequencedProvider([{"node_id": "node_fb", "confidence_score": 0.8}]),
        fallback_profile=fallback_profile,
    )
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "timeout"},
        data_classification="public_internal",
    )

    _response, parsed, validation = client.complete(
        run_id="run_fallback",
        step_id="step_fallback",
        request=request,
        response_model=NodeExtractionOutput,
    )

    trace_values = list(traces.llm_calls.values())
    assert parsed is not None
    assert parsed.node_id == "node_fb"
    assert validation.status == "passed"
    assert [trace.model_profile_id for trace in trace_values] == ["dummy-fast", "dummy-fallback"]
    assert [trace.validation_status for trace in trace_values] == ["failed", "passed"]


def test_gateway_compares_same_request_across_dummy_profiles() -> None:
    traces = InMemoryTraceRepository()
    request = ModelRequest(
        model_profile_id="dummy-fast",
        prompt_version_id="pv_node_v1",
        payload={"fixture_name": "candidate"},
        data_classification="public_internal",
    )
    slow_profile = profile().model_copy(
        update={"model_profile_id": "dummy-slow", "model_name": "dummy-slow"}
    )

    report = compare_model_gateway_candidates(
        run_id="run_compare",
        step_id="step_compare",
        request=request,
        candidates=[
            ModelGatewayCandidate(
                provider=DummyModelProvider(
                    fixtures={
                        "candidate": {
                            "node_id": "node_001",
                            "confidence_score": 0.9,
                        }
                    }
                ),
                profile=profile(),
                prompt=prompt(),
            ),
            ModelGatewayCandidate(
                provider=DummyModelProvider(
                    fixtures={
                        "candidate": {
                            "node_id": "node_001",
                            "confidence_score": 0.72,
                        }
                    }
                ),
                profile=slow_profile,
                prompt=prompt().model_copy(update={"prompt_version_id": "pv_node_v1b"}),
            ),
        ],
        response_model=NodeExtractionOutput,
        trace_repo=traces,
    )

    assert report.compared_model_profile_ids == ["dummy-fast", "dummy-slow"]
    assert report.compared_prompt_version_ids == ["pv_node_v1", "pv_node_v1b"]
    assert report.validation_statuses == {
        "dummy-fast": "passed",
        "dummy-slow": "passed",
    }
    assert report.output_changed is True
    assert report.output_diff["changed"]["confidence_score"] == {
        "left": 0.9,
        "right": 0.72,
    }
    assert [trace.model_profile_id for trace in traces.llm_calls.values()] == [
        "dummy-fast",
        "dummy-slow",
    ]
