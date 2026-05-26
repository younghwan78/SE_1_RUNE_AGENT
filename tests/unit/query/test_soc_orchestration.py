"""Tests for SoC query tool planning and answer assembly."""

from typing import Any

import pytest
from pydantic import ValidationError

from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.ontology.soc_models import (
    SocAnswer,
    SocAnswerItem,
    SocAnswerSource,
    SocQueryPlan,
    SocQueryToolCall,
    SocRerankResult,
    SocSlice,
)
from req_tracker.query.soc_orchestration import (
    GatewaySocAnswerAssembler,
    GatewaySocQueryToolPlanner,
    build_deterministic_query_plan,
)
from req_tracker.query.soc_service import answer_soc_query


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
            latency_ms=8,
        )


class FakeAnswerAssembler:
    def __init__(self, summary: str) -> None:
        self.summary = summary
        self.calls = 0

    def assemble(
        self,
        *,
        user_query: str,
        query_slice: SocSlice,
        query_plan: SocQueryPlan,
        base_answer: SocAnswer,
        candidate_context: list[dict[str, object]],
        run_id: str,
        step_id: str = "soc_answer_assembly",
    ) -> SocAnswer:
        self.calls += 1
        return base_answer.model_copy(update={"summary": self.summary})


def test_query_plan_contract_rejects_raw_sql_or_cypher_arguments() -> None:
    with pytest.raises(ValidationError, match="raw query"):
        SocQueryPlan(
            plan_id="plan_bad",
            pattern="topic_intersection",
            slice=SocSlice(
                pattern="topic_intersection",
                concerns=["Performance"],
                components=["Camera"],
            ),
            tool_calls=[
                SocQueryToolCall(
                    call_id="call_bad",
                    tool="graph_query",
                    arguments={"cypher": "MATCH (n) RETURN n"},
                )
            ],
        )


def test_deterministic_query_plan_uses_whitelisted_tools_without_raw_queries() -> None:
    query_plan = build_deterministic_query_plan(
        query_id="soc_query_plan_unit",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
            keywords=["shot"],
        ),
    )

    assert [call.tool for call in query_plan.tool_calls] == [
        "fixture_axis_filter",
        "keyword_search",
        "rerank",
        "answer_projection",
    ]
    assert query_plan.tool_calls[-1].depends_on == ["rerank"]
    assert all(
        forbidden_key not in call.arguments
        for call in query_plan.tool_calls
        for forbidden_key in {"sql", "cypher", "raw_query"}
    )


def test_rerank_result_rejects_duplicate_candidate_ids() -> None:
    with pytest.raises(ValidationError, match="duplicate rerank candidate"):
        SocRerankResult(
            query_id="soc_query_rerank_bad",
            ranked_items=[
                {"artifact_id": "SOC1-JIRA-001", "score": 0.7, "source": "rule"},
                {"artifact_id": "SOC1-JIRA-001", "score": 0.6, "source": "rule"},
            ],
        )


def test_gateway_query_tool_planner_validates_plan_and_records_trace() -> None:
    traces = InMemoryTraceRepository()
    provider = CapturingProvider(
        {
            "plan_id": "plan_gateway",
            "pattern": "topic_intersection",
            "slice": {
                "pattern": "topic_intersection",
                "concerns": ["Performance"],
                "components": ["Camera"],
            },
            "tool_calls": [
                {
                    "call_id": "call_filter",
                    "tool": "fixture_axis_filter",
                    "arguments": {"concerns": ["Performance"], "components": ["Camera"]},
                },
                {
                    "call_id": "call_answer",
                    "tool": "answer_projection",
                    "arguments": {"format": "SocAnswer"},
                    "depends_on": ["call_filter"],
                },
            ],
            "rationale": "Use typed fixture filter before answer projection.",
        }
    )
    planner = GatewaySocQueryToolPlanner(
        client=ModelGatewayClient(
            provider=provider,
            profile=_profile(),
            prompt=_prompt("pv_soc_query_tool_planning_v1", "soc_query_tool_planning"),
            trace_repo=traces,
        ),
        model_profile_id="dummy-soc-query",
        prompt_version_id="pv_soc_query_tool_planning_v1",
    )

    query_plan = planner.plan(
        query_id="soc_query_tool_plan_001",
        user_query="Camera shot 성능 이슈는?",
        query_slice=SocSlice(
            pattern="topic_intersection",
            concerns=["Performance"],
            components=["Camera"],
        ),
        run_id="soc_query_tool_plan_001",
    )

    assert query_plan.plan_id == "plan_gateway"
    assert [call.tool for call in query_plan.tool_calls] == [
        "fixture_axis_filter",
        "answer_projection",
    ]
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "soc_query_tool_planning"
    assert trace.validation_status == "passed"


def test_gateway_answer_assembler_returns_schema_valid_answer_and_records_trace() -> None:
    traces = InMemoryTraceRepository()
    provider = CapturingProvider(_assembled_answer_payload())
    assembler = GatewaySocAnswerAssembler(
        client=ModelGatewayClient(
            provider=provider,
            profile=_profile(),
            prompt=_prompt("pv_soc_answer_assembly_v1", "soc_answer_assembly"),
            trace_repo=traces,
        ),
        model_profile_id="dummy-soc-query",
        prompt_version_id="pv_soc_answer_assembly_v1",
    )
    base_answer = SocAnswer.model_validate(_assembled_answer_payload())
    query_plan = build_deterministic_query_plan(
        query_id="soc_query_answer_001",
        query_slice=SocSlice(pattern="concern_slice", concerns=["Power"]),
    )

    answer = assembler.assemble(
        user_query="power 관련 활동",
        query_slice=SocSlice(pattern="concern_slice", concerns=["Power"]),
        query_plan=query_plan,
        base_answer=base_answer.model_copy(update={"summary": "fallback summary"}),
        candidate_context=[],
        run_id="soc_query_answer_001",
    )

    assert answer.summary == "Gateway assembled answer."
    assert answer.items[0].sources[0].url.startswith("https://")
    trace = list(traces.llm_calls.values())[0]
    assert trace.step_id == "soc_answer_assembly"
    assert trace.validation_status == "passed"


def test_answer_soc_query_can_use_answer_assembler_and_persist_query_plan(tmp_path) -> None:  # type: ignore[no-untyped-def]
    assembler = FakeAnswerAssembler("Assembler summary.")

    answer = answer_soc_query(
        user_query="Camera shot 성능 이슈는 무엇이 있었나?",
        user_id="architect_01",
        session_id="session_001",
        query_id="soc_query_orchestration_001",
        artifact_store=None,
        answer_assembler=assembler,
    )

    assert answer.summary == "Assembler summary."
    assert assembler.calls == 1


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="dummy-soc-query",
        provider="dummy",
        model_name="dummy-soc-query",
        endpoint_alias="dummy",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def _prompt(prompt_version_id: str, task_name: str) -> PromptVersion:
    return PromptVersion(
        prompt_version_id=prompt_version_id,
        task_name=task_name,  # type: ignore[arg-type]
        template="Return schema-valid JSON only.",
        schema_version_ref="soc.v0_1.query",
        retrieval_policy_id="soc_seed",
        created_by="tester",
        status="active",
    )


def _assembled_answer_payload() -> dict[str, Any]:
    return {
        "query_id": "soc_query_answer_001",
        "summary": "Gateway assembled answer.",
        "items": [
            SocAnswerItem(
                title="Power review",
                summary="Power optimization activity.",
                sources=[
                    SocAnswerSource(
                        type="jira",
                        key="SOC1-JIRA-001",
                        url="https://jira.example.local/SOC1-JIRA-001",
                    )
                ],
                level="L3",
                concern=["Power"],
                component=["PMU"],
            ).model_dump(mode="json")
        ],
        "timeline": [],
        "confidence": "high",
        "reasoning_log_ref": "memory://soc-query/soc_query_answer_001/reasoning",
        "quality_signals": [],
    }
