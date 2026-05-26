"""Typed SoC query orchestration and optional answer assembly."""

from typing import Protocol

from req_tracker.debug.hash import stable_hash
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.ontology.soc_models import (
    SOC_SCHEMA_VERSION,
    SocAnswer,
    SocQueryPlan,
    SocQueryToolCall,
    SocSlice,
)


class SocQueryToolPlanner(Protocol):
    """Plan whitelisted retrieval and projection tool calls for a SoC slice."""

    def plan(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        current_project: str | None = None,
        run_id: str | None = None,
        step_id: str = "soc_query_tool_planning",
    ) -> SocQueryPlan:
        """Return a schema-valid, whitelisted query tool plan."""


class SocAnswerAssembler(Protocol):
    """Assemble a final answer from deterministic context."""

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
        """Return a schema-valid answer."""


class GatewaySocQueryToolPlanner:
    """Use the model gateway to propose a typed query plan with fallback."""

    def __init__(
        self,
        *,
        client: ModelGatewayClient,
        model_profile_id: str,
        prompt_version_id: str,
    ) -> None:
        self._client = client
        self._model_profile_id = model_profile_id
        self._prompt_version_id = prompt_version_id

    def plan(
        self,
        *,
        query_id: str,
        user_query: str,
        query_slice: SocSlice,
        current_project: str | None = None,
        run_id: str | None = None,
        step_id: str = "soc_query_tool_planning",
    ) -> SocQueryPlan:
        """Return a gateway-planned tool sequence, falling back to deterministic rules."""
        request = ModelRequest(
            model_profile_id=self._model_profile_id,
            prompt_version_id=self._prompt_version_id,
            payload={
                "task": "soc_query_tool_planning",
                "schema_version": SOC_SCHEMA_VERSION,
                "query_id": query_id,
                "user_query": user_query,
                "current_project": current_project,
                "slice": query_slice.model_dump(mode="json"),
                "allowed_tools": [
                    "fixture_axis_filter",
                    "keyword_search",
                    "event_log",
                    "get_artifact",
                    "answer_projection",
                    "graph_query",
                    "vector_search",
                    "rerank",
                ],
                "forbidden_argument_keys": ["sql", "cypher", "raw_query"],
            },
            data_classification="public_internal",
        )
        fallback = build_deterministic_query_plan(query_id=query_id, query_slice=query_slice)
        try:
            _response, parsed, validation = self._client.complete(
                run_id=run_id or f"soc_query_tools_{stable_hash(request.payload)[:12]}",
                step_id=step_id,
                request=request,
                response_model=SocQueryPlan,
            )
        except Exception:
            return fallback
        if parsed is None or validation.status == "failed":
            return fallback
        return parsed


class GatewaySocAnswerAssembler:
    """Use the model gateway to assemble a schema-valid answer with fallback."""

    def __init__(
        self,
        *,
        client: ModelGatewayClient,
        model_profile_id: str,
        prompt_version_id: str,
    ) -> None:
        self._client = client
        self._model_profile_id = model_profile_id
        self._prompt_version_id = prompt_version_id

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
        """Return a gateway-assembled answer, falling back to deterministic output."""
        request = ModelRequest(
            model_profile_id=self._model_profile_id,
            prompt_version_id=self._prompt_version_id,
            payload={
                "task": "soc_answer_assembly",
                "schema_version": SOC_SCHEMA_VERSION,
                "user_query": user_query,
                "slice": query_slice.model_dump(mode="json"),
                "query_plan": query_plan.model_dump(mode="json"),
                "candidate_context": candidate_context,
                "fallback_answer": base_answer.model_dump(mode="json"),
                "output_contract": "Return exactly one SocAnswer JSON object with source URLs.",
            },
            data_classification="public_internal",
        )
        try:
            _response, parsed, validation = self._client.complete(
                run_id=run_id,
                step_id=step_id,
                request=request,
                response_model=SocAnswer,
            )
        except Exception:
            return base_answer
        if parsed is None or validation.status == "failed":
            return base_answer
        if parsed.query_id != base_answer.query_id:
            return base_answer
        return parsed


def build_deterministic_query_plan(*, query_id: str, query_slice: SocSlice) -> SocQueryPlan:
    """Build the safe seed query plan executed by the deterministic fixture backend."""
    tool_calls: list[SocQueryToolCall] = []
    if query_slice.pattern == "unknown":
        return SocQueryPlan(
            plan_id=f"plan_{stable_hash([query_id, query_slice])[:16]}",
            pattern=query_slice.pattern,
            slice=query_slice,
            tool_calls=[],
            rationale="Unknown slices do not execute retrieval tools.",
        )
    if query_slice.pattern == "lifecycle_trace":
        tool_calls.extend(
            [
                SocQueryToolCall(
                    call_id="event_log",
                    tool="event_log",
                    arguments={"artifact_id": query_slice.artifact_id},
                ),
                SocQueryToolCall(
                    call_id="get_artifact",
                    tool="get_artifact",
                    arguments={"artifact_id": query_slice.artifact_id},
                    depends_on=["event_log"],
                ),
            ]
        )
    else:
        tool_calls.append(
            SocQueryToolCall(
                call_id="fixture_axis_filter",
                tool="fixture_axis_filter",
                arguments={
                    "pattern": query_slice.pattern,
                    "project_keys": query_slice.project_keys,
                    "v_levels": query_slice.v_levels,
                    "concerns": query_slice.concerns,
                    "components": query_slice.components,
                    "keywords": query_slice.keywords,
                },
            )
        )
        if query_slice.keywords:
            tool_calls.append(
                SocQueryToolCall(
                    call_id="keyword_search",
                    tool="keyword_search",
                    arguments={"keywords": query_slice.keywords},
                    depends_on=["fixture_axis_filter"],
                )
            )
        tool_calls.append(
            SocQueryToolCall(
                call_id="rerank",
                tool="rerank",
                arguments={
                    "strategy": "lexical_seed_or_model_gateway",
                    "candidate_source": tool_calls[-1].call_id,
                },
                depends_on=[tool_calls[-1].call_id],
            )
        )
    tool_calls.append(
        SocQueryToolCall(
            call_id="answer_projection",
            tool="answer_projection",
            arguments={"format": "SocAnswer"},
            depends_on=[tool_calls[-1].call_id] if tool_calls else [],
        )
    )
    return SocQueryPlan(
        plan_id=f"plan_{stable_hash([query_id, query_slice])[:16]}",
        pattern=query_slice.pattern,
        slice=query_slice,
        tool_calls=tool_calls,
        rationale="Deterministic seed plan using whitelisted in-process tools.",
    )
