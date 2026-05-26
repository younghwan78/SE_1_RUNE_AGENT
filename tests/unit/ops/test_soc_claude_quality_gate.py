"""Tests for the SoC Claude Code quality gate."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from req_tracker.model_gateway.models import ModelRequest, ModelResponse, StructuredValidationResult

ROOT = Path(__file__).resolve().parents[3]


def test_soc_claude_quality_gate_dry_run_reports_live_requirements() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/evals/run_soc_claude_quality_gate.py",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "skipped"
    assert payload["mode"] == "dry_run"
    assert payload["requires_live"] is True
    assert payload["model_profile_id"] == "claude-code-local"
    assert payload["checks"]["slice_planning"]["status"] == "skipped"
    assert payload["checks"]["query_tool_planning"]["status"] == "skipped"
    assert payload["checks"]["answer_assembly"]["status"] == "skipped"
    assert payload["checks"]["slice_planning"]["prompt_version_id"] == "pv_soc_slice_planning_v1"
    assert (
        payload["checks"]["query_tool_planning"]["prompt_version_id"]
        == "pv_soc_query_tool_planning_v1"
    )
    assert (
        payload["checks"]["answer_assembly"]["prompt_version_id"]
        == "pv_soc_answer_assembly_v1"
    )


def test_soc_claude_quality_gate_validates_slice_plan_and_answer_with_fake_gateway() -> None:
    module = _load_quality_gate()
    factory = FakeClientFactory()

    report = module.run_soc_claude_quality_gate(live=True, client_factory=factory)

    assert report["status"] == "passed"
    assert report["checks"]["slice_planning"]["status"] == "passed"
    assert report["checks"]["slice_planning"]["parsed"]["pattern"] == "topic_intersection"
    assert report["checks"]["query_tool_planning"]["status"] == "passed"
    assert report["checks"]["query_tool_planning"]["tool_count"] >= 3
    assert report["checks"]["query_tool_planning"]["forbidden_raw_query_args_present"] is False
    assert report["checks"]["answer_assembly"]["status"] == "passed"
    assert report["checks"]["answer_assembly"]["source_url_count"] >= 1
    assert report["trace_count"] == 3
    assert [request.payload["task"] for request in factory.requests] == [
        "soc_slice_planning",
        "soc_query_tool_planning",
        "soc_answer_assembly",
    ]
    assert all("example_output" in request.payload for request in factory.requests)
    assert "no prose" in str(factory.requests[0].payload["output_contract"]).lower()


class FakeClientFactory:
    def __init__(self) -> None:
        self.requests: list[ModelRequest] = []

    def __call__(self, task_name: str) -> "FakeClient":
        return FakeClient(task_name=task_name, requests=self.requests)


class FakeClient:
    def __init__(self, *, task_name: str, requests: list[ModelRequest]) -> None:
        self.task_name = task_name
        self.requests = requests

    def complete(
        self,
        *,
        run_id: str,
        step_id: str,
        request: ModelRequest,
        response_model: type[Any],
    ) -> tuple[ModelResponse, Any, StructuredValidationResult]:
        self.requests.append(request)
        output = _payload_for_task(self.task_name)
        parsed = response_model.model_validate(output)
        return (
            ModelResponse(
                model_profile_id=request.model_profile_id,
                prompt_version_id=request.prompt_version_id,
                output=output,
                latency_ms=5,
            ),
            parsed,
            StructuredValidationResult(status="passed"),
        )


def _payload_for_task(task_name: str) -> dict[str, Any]:
    if task_name == "soc_slice_planning":
        return {
            "pattern": "topic_intersection",
            "concerns": ["Performance"],
            "components": ["Camera"],
            "keywords": ["shot"],
        }
    if task_name == "soc_query_tool_planning":
        return {
            "plan_id": "plan_soc_claude_quality",
            "pattern": "topic_intersection",
            "slice": _payload_for_task("soc_slice_planning"),
            "tool_calls": [
                {
                    "call_id": "graph",
                    "tool": "graph_query",
                    "arguments": {"pattern": "topic_intersection"},
                },
                {
                    "call_id": "vector",
                    "tool": "vector_search",
                    "arguments": {"keywords": ["shot"]},
                },
                {
                    "call_id": "answer",
                    "tool": "answer_projection",
                    "arguments": {"format": "SocAnswer"},
                    "depends_on": ["graph", "vector"],
                },
            ],
            "rationale": "Use graph and vector candidates before answer projection.",
        }
    if task_name == "soc_answer_assembly":
        return {
            "query_id": "soc_claude_quality_q2",
            "summary": "Camera shot performance issues were found in sourced artifacts.",
            "items": [
                {
                    "title": "Camera shot latency issue",
                    "summary": "JIRA issue records shot latency degradation and mitigation.",
                    "sources": [
                        {
                            "type": "jira",
                            "key": "SOC1-JIRA-014",
                            "url": "https://jira.example.local/browse/SOC1-JIRA-014",
                        }
                    ],
                    "level": "L3",
                    "concern": ["Performance"],
                    "component": ["Camera"],
                }
            ],
            "timeline": [],
            "confidence": "high",
            "reasoning_log_ref": "memory://soc-claude-quality/soc_claude_quality_q2",
            "quality_signals": ["schema_valid", "source_url_preserved"],
        }
    raise AssertionError(f"unexpected task: {task_name}")


def _load_quality_gate() -> ModuleType:
    module_path = ROOT / "ops/evals/run_soc_claude_quality_gate.py"
    spec = importlib.util.spec_from_file_location("run_soc_claude_quality_gate", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
