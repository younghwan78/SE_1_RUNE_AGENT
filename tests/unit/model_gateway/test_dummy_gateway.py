"""Dummy model gateway tests."""

import pytest
from pydantic import BaseModel, Field

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.dummy_provider import DummyModelProvider, DummyModelTimeoutError
from req_tracker.model_gateway.models import ModelProfile, ModelRequest, PromptVersion
from req_tracker.model_gateway.policy import ModelPolicyError


class NodeExtractionOutput(BaseModel):
    node_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)


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

