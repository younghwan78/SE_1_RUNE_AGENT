"""Evaluate Claude Code quality for SoC query planning and answer assembly."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from req_tracker.config.settings import Settings
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.model_gateway.registry import ModelRegistry
from req_tracker.ontology.soc_models import (
    SOC_SCHEMA_VERSION,
    SocAnswer,
    SocAnswerItem,
    SocAnswerSource,
    SocQueryPlan,
    SocSlice,
)

DEFAULT_MODEL_PROFILE_ID = "claude-code-local"
DEFAULT_QUERY_ID = "soc_claude_quality_q2"
DEFAULT_USER_QUERY = "Camera shot 성능 이슈는 무엇이 있었나?"
RUN_ID = "soc_claude_quality_gate"

TASKS: dict[str, dict[str, str]] = {
    "slice_planning": {
        "task_name": "soc_slice_planning",
        "prompt_version_id": "pv_soc_slice_planning_v1",
        "response_model": "SocSlice",
    },
    "query_tool_planning": {
        "task_name": "soc_query_tool_planning",
        "prompt_version_id": "pv_soc_query_tool_planning_v1",
        "response_model": "SocQueryPlan",
    },
    "answer_assembly": {
        "task_name": "soc_answer_assembly",
        "prompt_version_id": "pv_soc_answer_assembly_v1",
        "response_model": "SocAnswer",
    },
}

ClientFactory = Callable[[str], Any]


def run_soc_claude_quality_gate(
    *,
    live: bool,
    model_profile_id: str = DEFAULT_MODEL_PROFILE_ID,
    command: str = "",
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Return Claude Code quality gate results without invoking Claude unless live is true."""
    if not live:
        return _dry_run_payload(model_profile_id=model_profile_id, command=command)

    factory: ClientFactory
    trace_counter: Callable[[], int] | None = None
    if client_factory is None:
        gateway_factory = _RegistryGatewayFactory(
            model_profile_id=model_profile_id,
            command_override=command,
        )
        factory = gateway_factory
        trace_counter = gateway_factory.trace_count
        command_info = gateway_factory.command_info()
    else:
        factory = client_factory
        command_info = {"command": [], "command_status": "injected"}

    checks: dict[str, Any] = {}
    failures: list[str] = []
    call_count = 0

    checks["slice_planning"] = _slice_planning_check(
        client=factory(TASKS["slice_planning"]["task_name"]),
        model_profile_id=model_profile_id,
    )
    call_count += 1
    if checks["slice_planning"]["status"] != "passed":
        failures.append("slice_planning_failed")
        return _live_payload(
            checks=checks,
            failures=failures,
            model_profile_id=model_profile_id,
            command_info=command_info,
            trace_count=trace_counter() if trace_counter is not None else call_count,
        )

    query_slice = SocSlice.model_validate(checks["slice_planning"]["parsed"])
    checks["query_tool_planning"] = _query_tool_planning_check(
        client=factory(TASKS["query_tool_planning"]["task_name"]),
        model_profile_id=model_profile_id,
        query_slice=query_slice,
    )
    call_count += 1
    if checks["query_tool_planning"]["status"] != "passed":
        failures.append("query_tool_planning_failed")
        return _live_payload(
            checks=checks,
            failures=failures,
            model_profile_id=model_profile_id,
            command_info=command_info,
            trace_count=trace_counter() if trace_counter is not None else call_count,
        )

    query_plan = SocQueryPlan.model_validate(checks["query_tool_planning"]["parsed"])
    checks["answer_assembly"] = _answer_assembly_check(
        client=factory(TASKS["answer_assembly"]["task_name"]),
        model_profile_id=model_profile_id,
        query_slice=query_slice,
        query_plan=query_plan,
    )
    call_count += 1
    if checks["answer_assembly"]["status"] != "passed":
        failures.append("answer_assembly_failed")

    return _live_payload(
        checks=checks,
        failures=failures,
        model_profile_id=model_profile_id,
        command_info=command_info,
        trace_count=trace_counter() if trace_counter is not None else call_count,
    )


class _RegistryGatewayFactory:
    """Create task-specific model gateway clients from the configured registry."""

    def __init__(self, *, model_profile_id: str, command_override: str) -> None:
        settings = Settings()
        self._registry = ModelRegistry.from_json_files(
            profiles_path=Path(settings.model_profiles_path),
            prompts_path=Path(settings.prompt_versions_path),
        )
        self._profile = self._registry.get_profile(model_profile_id)
        command_text = command_override or settings.model_gateway_claude_command
        command_text = command_text or self._profile.endpoint_alias
        self._command = _command(command_text)
        self._provider = provider_for_profile(self._profile, claude_command=self._command)
        self._traces = InMemoryTraceRepository()

    def __call__(self, task_name: str) -> ModelGatewayClient:
        prompt = self._registry.active_prompt_for_task(task_name)  # type: ignore[arg-type]
        return ModelGatewayClient(
            provider=self._provider,
            profile=self._profile,
            prompt=prompt,
            trace_repo=self._traces,
        )

    def trace_count(self) -> int:
        return len(self._traces.llm_calls)

    def command_info(self) -> dict[str, Any]:
        return {
            "command": list(self._command),
            "command_status": "found" if shutil.which(self._command[0]) else "missing",
        }


def _slice_planning_check(*, client: Any, model_profile_id: str) -> dict[str, Any]:
    prompt_version_id = TASKS["slice_planning"]["prompt_version_id"]
    request = ModelRequest(
        model_profile_id=model_profile_id,
        prompt_version_id=prompt_version_id,
        payload={
            "task": "soc_slice_planning",
            "schema_version": SOC_SCHEMA_VERSION,
            "user_query": DEFAULT_USER_QUERY,
            "allowed_patterns": [
                "concern_slice",
                "topic_intersection",
                "timeline_slice",
                "lifecycle_trace",
                "unknown",
            ],
            "allowed_axes": ["project", "v_level", "concern", "component"],
            "output_contract": (
                "Return ONLY raw JSON for one SocSlice object. No prose, no markdown, "
                "no code fences. Do not emit SQL or Cypher."
            ),
            "example_output": {
                "pattern": "topic_intersection",
                "project_keys": ["SOC-N-1"],
                "concerns": ["Performance"],
                "components": ["Camera"],
                "keywords": ["shot"],
            },
        },
        data_classification="public_internal",
        masking_applied=True,
        access_checked=True,
    )
    try:
        _response, parsed, validation = client.complete(
            run_id=RUN_ID,
            step_id="soc_slice_planning",
            request=request,
            response_model=SocSlice,
        )
    except Exception as exc:  # noqa: BLE001
        return _failed_check(prompt_version_id=prompt_version_id, error=str(exc))
    if parsed is None or validation.status != "passed":
        return _failed_check(
            prompt_version_id=prompt_version_id,
            error=validation.error_message or "SocSlice validation failed",
        )
    selectors_ok = (
        parsed.pattern == "topic_intersection"
        and "Performance" in parsed.concerns
        and "Camera" in parsed.components
    )
    return {
        "expected_pattern": "topic_intersection",
        "parsed": parsed.model_dump(mode="json"),
        "prompt_version_id": prompt_version_id,
        "response_model": "SocSlice",
        "status": "passed" if selectors_ok else "failed",
        "validation_status": validation.status,
    }


def _query_tool_planning_check(
    *,
    client: Any,
    model_profile_id: str,
    query_slice: SocSlice,
) -> dict[str, Any]:
    prompt_version_id = TASKS["query_tool_planning"]["prompt_version_id"]
    request = ModelRequest(
        model_profile_id=model_profile_id,
        prompt_version_id=prompt_version_id,
        payload={
            "task": "soc_query_tool_planning",
            "schema_version": SOC_SCHEMA_VERSION,
            "query_id": DEFAULT_QUERY_ID,
            "user_query": DEFAULT_USER_QUERY,
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
            "output_contract": (
                "Return ONLY raw JSON for one SocQueryPlan object. No prose, no markdown, "
                "no code fences. Use whitelisted tool names only."
            ),
            "example_output": {
                "plan_id": "plan_soc_claude_quality",
                "pattern": "topic_intersection",
                "slice": query_slice.model_dump(mode="json"),
                "tool_calls": [
                    {
                        "call_id": "graph",
                        "tool": "graph_query",
                        "arguments": {"pattern": "topic_intersection"},
                    },
                    {
                        "call_id": "answer",
                        "tool": "answer_projection",
                        "arguments": {"format": "SocAnswer"},
                        "depends_on": ["graph"],
                    },
                ],
                "rationale": "Use graph candidates before answer projection.",
            },
        },
        data_classification="public_internal",
        masking_applied=True,
        access_checked=True,
    )
    try:
        _response, parsed, validation = client.complete(
            run_id=RUN_ID,
            step_id="soc_query_tool_planning",
            request=request,
            response_model=SocQueryPlan,
        )
    except Exception as exc:  # noqa: BLE001
        return _failed_check(prompt_version_id=prompt_version_id, error=str(exc))
    if parsed is None or validation.status != "passed":
        return _failed_check(
            prompt_version_id=prompt_version_id,
            error=validation.error_message or "SocQueryPlan validation failed",
        )
    forbidden_present = _has_forbidden_query_key(parsed.model_dump(mode="json"))
    has_answer_projection = any(call.tool == "answer_projection" for call in parsed.tool_calls)
    status = "passed" if has_answer_projection and not forbidden_present else "failed"
    return {
        "forbidden_raw_query_args_present": forbidden_present,
        "parsed": parsed.model_dump(mode="json"),
        "prompt_version_id": prompt_version_id,
        "response_model": "SocQueryPlan",
        "status": status,
        "tool_count": len(parsed.tool_calls),
        "validation_status": validation.status,
    }


def _answer_assembly_check(
    *,
    client: Any,
    model_profile_id: str,
    query_slice: SocSlice,
    query_plan: SocQueryPlan,
) -> dict[str, Any]:
    prompt_version_id = TASKS["answer_assembly"]["prompt_version_id"]
    base_answer = _base_answer()
    request = ModelRequest(
        model_profile_id=model_profile_id,
        prompt_version_id=prompt_version_id,
        payload={
            "task": "soc_answer_assembly",
            "schema_version": SOC_SCHEMA_VERSION,
            "query_id": DEFAULT_QUERY_ID,
            "user_query": DEFAULT_USER_QUERY,
            "slice": query_slice.model_dump(mode="json"),
            "query_plan": query_plan.model_dump(mode="json"),
            "candidate_context": _candidate_context(),
            "fallback_answer": base_answer.model_dump(mode="json"),
            "output_contract": (
                "Return ONLY raw JSON for one SocAnswer object. No prose, no markdown, "
                "no code fences. Keep source URLs attached."
            ),
            "example_output": base_answer.model_dump(mode="json"),
        },
        data_classification="public_internal",
        masking_applied=True,
        access_checked=True,
    )
    try:
        _response, parsed, validation = client.complete(
            run_id=RUN_ID,
            step_id="soc_answer_assembly",
            request=request,
            response_model=SocAnswer,
        )
    except Exception as exc:  # noqa: BLE001
        return _failed_check(prompt_version_id=prompt_version_id, error=str(exc))
    if parsed is None or validation.status != "passed":
        return _failed_check(
            prompt_version_id=prompt_version_id,
            error=validation.error_message or "SocAnswer validation failed",
        )
    source_urls = [
        source.url
        for item in parsed.items
        for source in item.sources
        if source.url.startswith(("http://", "https://"))
    ]
    status = "passed" if parsed.query_id == DEFAULT_QUERY_ID and source_urls else "failed"
    return {
        "parsed": parsed.model_dump(mode="json"),
        "prompt_version_id": prompt_version_id,
        "response_model": "SocAnswer",
        "source_url_count": len(source_urls),
        "status": status,
        "validation_status": validation.status,
    }


def _base_answer() -> SocAnswer:
    return SocAnswer(
        query_id=DEFAULT_QUERY_ID,
        summary="Fallback answer for Camera shot performance.",
        items=[
            SocAnswerItem(
                title="Camera shot latency issue",
                summary="Seed evidence records shot latency degradation and mitigation.",
                sources=[
                    SocAnswerSource(
                        type="jira",
                        key="SOC1-JIRA-014",
                        url="https://jira.example.local/browse/SOC1-JIRA-014",
                    )
                ],
                level="L3",
                concern=["Performance"],
                component=["Camera"],
            )
        ],
        timeline=[],
        confidence="high",
        reasoning_log_ref=f"memory://soc-claude-quality/{DEFAULT_QUERY_ID}",
        quality_signals=["fallback_source_url_preserved"],
    )


def _candidate_context() -> list[dict[str, object]]:
    return [
        {
            "artifact_id": "SOC1-JIRA-014",
            "title": "Camera shot latency issue",
            "summary": "Shot pipeline latency increased after ISP queue changes.",
            "source_url": "https://jira.example.local/browse/SOC1-JIRA-014",
            "concern": ["Performance"],
            "component": ["Camera"],
            "v_level": "L3",
        }
    ]


def _dry_run_payload(*, model_profile_id: str, command: str) -> dict[str, Any]:
    command_tuple = _command(command or "claude -p --output-format json")
    return {
        "checks": {
            key: {
                "prompt_version_id": value["prompt_version_id"],
                "requires_live": True,
                "response_model": value["response_model"],
                "status": "skipped",
            }
            for key, value in TASKS.items()
        },
        "command": list(command_tuple),
        "command_status": "found" if shutil.which(command_tuple[0]) else "missing",
        "mode": "dry_run",
        "model_profile_id": model_profile_id,
        "requires_live": True,
        "schema_version": "v1",
        "status": "skipped",
    }


def _live_payload(
    *,
    checks: dict[str, Any],
    failures: list[str],
    model_profile_id: str,
    command_info: dict[str, Any],
    trace_count: int,
) -> dict[str, Any]:
    return {
        "checks": checks,
        **command_info,
        "failure_count": len(failures),
        "failures": failures,
        "mode": "live",
        "model_profile_id": model_profile_id,
        "requires_live": True,
        "schema_version": "v1",
        "status": "passed" if not failures else "failed",
        "trace_count": trace_count,
    }


def _failed_check(*, prompt_version_id: str, error: str) -> dict[str, Any]:
    return {
        "error": error,
        "prompt_version_id": prompt_version_id,
        "status": "failed",
        "validation_status": "failed",
    }


def _has_forbidden_query_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in {"sql", "cypher", "raw_query"}:
                return True
            if _has_forbidden_query_key(item):
                return True
    if isinstance(value, list):
        return any(_has_forbidden_query_key(item) for item in value)
    return False


def _command(command_text: str) -> tuple[str, ...]:
    command = tuple(shlex.split(command_text)) if command_text.strip() else ()
    return command or ("claude", "-p", "--output-format", "json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke Claude Code.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Invoke Claude Code through model gateway.",
    )
    parser.add_argument("--command", default="", help="Override Claude Code command.")
    parser.add_argument("--model-profile-id", default=DEFAULT_MODEL_PROFILE_ID)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main() -> int:
    args = _parse_args()
    report = run_soc_claude_quality_gate(
        live=args.live and not args.dry_run,
        model_profile_id=args.model_profile_id,
        command=args.command,
    )
    _emit(report, args.format)
    return 0 if report["status"] in {"passed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
