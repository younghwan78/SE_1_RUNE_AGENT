"""Tests for optional model-gateway-backed SoC query planning."""

from typing import Any

from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.model_gateway.providers import ModelProviderError
from req_tracker.ontology.soc_models import SocSlice
from req_tracker.query.soc_planner import GatewaySocSlicePlanner
from req_tracker.query.soc_service import answer_soc_query


class CapturingProvider:
    def __init__(
        self,
        output: dict[str, Any] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.output = output or {}
        self.exc = exc
        self.requests: list[ModelRequest] = []

    def complete(
        self,
        request: ModelRequest,
        active_profile: ModelProfile,
        active_prompt: PromptVersion,
    ) -> ModelResponse:
        self.requests.append(request)
        if self.exc is not None:
            raise self.exc
        return ModelResponse(
            model_profile_id=active_profile.model_profile_id,
            prompt_version_id=active_prompt.prompt_version_id,
            output=self.output,
            input_tokens=17,
            output_tokens=9,
            latency_ms=12,
        )


class FakePlanner:
    def __init__(self, query_slice: SocSlice) -> None:
        self.query_slice = query_slice
        self.calls: list[dict[str, object | None]] = []

    def plan(
        self,
        *,
        user_query: str,
        user_id: str,
        session_id: str,
        current_project: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        run_id: str | None = None,
        step_id: str = "soc_slice_planning",
    ) -> SocSlice:
        self.calls.append(
            {
                "user_query": user_query,
                "user_id": user_id,
                "session_id": session_id,
                "current_project": current_project,
                "conversation_history": conversation_history,
                "run_id": run_id,
                "step_id": step_id,
            }
        )
        return self.query_slice


def test_gateway_planner_returns_schema_valid_slice_and_records_trace() -> None:
    traces = InMemoryTraceRepository()
    provider = CapturingProvider(
        {
            "pattern": "topic_intersection",
            "project_keys": ["SOC-N-1"],
            "concerns": ["Performance"],
            "components": ["Camera"],
            "keywords": ["shot"],
        }
    )
    planner = GatewaySocSlicePlanner(
        client=ModelGatewayClient(
            provider=provider,
            profile=_profile(),
            prompt=_prompt(),
            trace_repo=traces,
        ),
        model_profile_id="dummy-soc-planner",
        prompt_version_id="pv_soc_slice_planning_v1",
    )

    query_slice = planner.plan(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        current_project="SOC-N-1",
    )

    assert query_slice.pattern == "topic_intersection"
    assert query_slice.project_keys == ["SOC-N-1"]
    assert query_slice.concerns == ["Performance"]
    assert query_slice.components == ["Camera"]
    assert provider.requests[0].model_profile_id == "dummy-soc-planner"
    assert provider.requests[0].prompt_version_id == "pv_soc_slice_planning_v1"
    assert provider.requests[0].payload["current_project"] == "SOC-N-1"
    assert "topic_intersection" in provider.requests[0].payload["allowed_patterns"]
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "soc_slice_planning"
    assert trace.validation_status == "passed"


def test_gateway_planner_falls_back_to_deterministic_slice_on_provider_failure() -> None:
    traces = InMemoryTraceRepository()
    planner = GatewaySocSlicePlanner(
        client=ModelGatewayClient(
            provider=CapturingProvider(exc=ModelProviderError("planner unavailable")),
            profile=_profile(),
            prompt=_prompt(),
            trace_repo=traces,
        ),
        model_profile_id="dummy-soc-planner",
        prompt_version_id="pv_soc_slice_planning_v1",
    )

    query_slice = planner.plan(
        user_query="이전 과제에서 power 관련 활동은?",
        user_id="architect_01",
        session_id="session_001",
    )

    assert query_slice.pattern == "concern_slice"
    assert query_slice.concerns == ["Power"]
    assert list(traces.llm_calls.values())[0].validation_status == "failed"


def test_answer_soc_query_uses_slice_planner_when_no_explicit_slice() -> None:
    planner = FakePlanner(
        SocSlice(
            pattern="topic_intersection",
            project_keys=["SOC-N-2"],
            concerns=["Thermal"],
            components=["GPU"],
        )
    )

    answer = answer_soc_query(
        user_query="planner가 GPU thermal 관련 자료로 라우팅해야 한다",
        user_id="architect_01",
        session_id="session_001",
        current_project="SOC-N-2",
        conversation_history=[{"role": "user", "content": "SOC-N-2만 봐줘"}],
        slice_planner=planner,
    )

    assert len(planner.calls) == 1
    assert planner.calls[0]["current_project"] == "SOC-N-2"
    assert answer.items
    assert all("Thermal" in item.concern for item in answer.items)
    assert all("GPU" in item.component for item in answer.items)


def test_answer_soc_query_bypasses_planner_when_explicit_slice_is_provided() -> None:
    planner = FakePlanner(
        SocSlice(
            pattern="topic_intersection",
            concerns=["Thermal"],
            components=["GPU"],
        )
    )

    answer = answer_soc_query(
        user_query="explicit slice를 우선해야 한다",
        user_id="architect_01",
        session_id="session_001",
        query_slice=SocSlice(pattern="concern_slice", concerns=["Power"]),
        slice_planner=planner,
    )

    assert planner.calls == []
    assert answer.items
    assert all("Power" in item.concern for item in answer.items)


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="dummy-soc-planner",
        provider="dummy",
        model_name="dummy-soc-planner",
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
        prompt_version_id="pv_soc_slice_planning_v1",
        task_name="soc_slice_planning",
        template="Plan typed SoC query slices.",
        schema_version_ref="soc.v0_1.slice",
        retrieval_policy_id="soc_seed",
        created_by="tester",
        status="active",
    )
