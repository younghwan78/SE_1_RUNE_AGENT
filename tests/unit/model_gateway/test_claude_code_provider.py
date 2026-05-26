"""Claude Code subprocess provider tests."""

import json
import subprocess
from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import BaseModel

from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.claude_code_provider import ClaudeCodeSubprocessProvider
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.models import ModelProfile, ModelRequest, PromptVersion
from req_tracker.model_gateway.providers import ModelProviderError


class AnswerOutput(BaseModel):
    answer: str


def test_claude_code_provider_sends_gateway_payload_over_stdin() -> None:
    calls: list[dict[str, Any]] = []

    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            {
                "command": list(command),
                "payload": json.loads(input_text),
                "timeout_seconds": timeout_seconds,
            }
        )
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout=json.dumps(
                {
                    "output": {"answer": "전력 이슈 2건을 찾았습니다."},
                    "usage": {"input_tokens": 17, "output_tokens": 9},
                },
                ensure_ascii=False,
            ),
            stderr="",
        )

    provider = ClaudeCodeSubprocessProvider(
        command=("claude-code", "--json"),
        runner=runner,
    )

    response = provider.complete(
        _request(),
        _profile(),
        _prompt(),
    )

    assert calls[0]["command"] == ["claude-code", "--json"]
    assert calls[0]["timeout_seconds"] == 30
    payload = calls[0]["payload"]
    assert payload["model_profile_id"] == "claude-code-local"
    assert payload["provider"] == "claude_code"
    assert payload["model"] == "claude-code"
    assert payload["task_name"] == "answer_generation"
    assert payload["prompt_template"] == "Answer with sources"
    assert payload["payload"] == {"question": "이전 과제 power 이슈는?"}
    assert response.output == {"answer": "전력 이슈 2건을 찾았습니다."}
    assert response.input_tokens == 17
    assert response.output_tokens == 9


def test_claude_code_provider_rejects_nonzero_subprocess_exit() -> None:
    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=2,
            stdout="",
            stderr="bad prompt",
        )

    provider = ClaudeCodeSubprocessProvider(command=("claude-code",), runner=runner)

    with pytest.raises(ModelProviderError, match="claude-code subprocess failed"):
        provider.complete(_request(), _profile(), _prompt())


def test_provider_factory_creates_claude_code_provider_without_http_endpoint() -> None:
    provider = provider_for_profile(
        _profile(),
        claude_command=("claude-code", "--json"),
    )

    assert isinstance(provider, ClaudeCodeSubprocessProvider)


def test_provider_factory_splits_claude_endpoint_alias() -> None:
    provider = provider_for_profile(
        _profile().model_copy(update={"endpoint_alias": "claude -p --output-format json"}),
    )

    assert isinstance(provider, ClaudeCodeSubprocessProvider)


def test_claude_code_provider_records_gateway_trace() -> None:
    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout=json.dumps({"output": {"answer": "ok"}}),
            stderr="",
        )

    traces = InMemoryTraceRepository()
    client = ModelGatewayClient(
        provider=ClaudeCodeSubprocessProvider(command=("claude-code",), runner=runner),
        profile=_profile(),
        prompt=_prompt(),
        trace_repo=traces,
    )

    _response, parsed, validation = client.complete(
        run_id="run_claude",
        step_id="step_answer",
        request=_request(),
        response_model=AnswerOutput,
    )

    trace = next(iter(traces.llm_calls.values()))
    assert parsed is not None
    assert parsed.answer == "ok"
    assert validation.status == "passed"
    assert trace.model_profile_id == "claude-code-local"
    assert trace.prompt_version_id == "pv_answer_generation_v1"
    assert trace.validation_status == "passed"


def test_claude_code_provider_accepts_claude_cli_json_result_wrapper() -> None:
    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "result": json.dumps({"output": {"answer": "wrapped ok"}}),
                    "usage": {"input_tokens": 5, "output_tokens": 4},
                }
            ),
            stderr="",
        )

    provider = ClaudeCodeSubprocessProvider(
        command=("claude", "-p", "--output-format", "json"),
        runner=runner,
    )

    response = provider.complete(_request(), _profile(), _prompt())

    assert response.output == {"answer": "wrapped ok"}
    assert response.input_tokens == 5
    assert response.output_tokens == 4


def test_claude_code_provider_includes_json_only_instruction_for_schema_profiles() -> None:
    calls: list[dict[str, Any]] = []

    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(json.loads(input_text))
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout=json.dumps({"output": {"answer": "ok"}}),
            stderr="",
        )

    provider = ClaudeCodeSubprocessProvider(command=("claude", "-p"), runner=runner)

    provider.complete(_request(), _profile(), _prompt())

    instruction = calls[0]["structured_output_instruction"]
    assert "Return ONLY one valid JSON object" in instruction
    assert calls[0]["expected_response_envelope"] == {"output": "<schema-valid JSON object>"}


def test_claude_code_provider_extracts_fenced_json_from_cli_result_text() -> None:
    def runner(
        command: Sequence[str],
        input_text: str,
        timeout_seconds: int,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "result": (
                        'Here is the JSON:\n```json\n'
                        '{"output": {"answer": "fenced ok"}}\n```'
                    ),
                    "usage": {"input_tokens": 5, "output_tokens": 4},
                }
            ),
            stderr="",
        )

    provider = ClaudeCodeSubprocessProvider(
        command=("claude", "-p", "--output-format", "json"),
        runner=runner,
    )

    response = provider.complete(_request(), _profile(), _prompt())

    assert response.output == {"answer": "fenced ok"}


def _profile() -> ModelProfile:
    return ModelProfile(
        model_profile_id="claude-code-local",
        provider="claude_code",
        model_name="claude-code",
        endpoint_alias="claude-code",
        allowed_data_classes=["public_internal", "restricted"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=200_000,
        default_temperature=0.0,
        timeout_seconds=30,
    )


def _prompt() -> PromptVersion:
    return PromptVersion(
        prompt_version_id="pv_answer_generation_v1",
        task_name="answer_generation",
        template="Answer with sources",
        schema_version_ref="soc.answer.v1",
        retrieval_policy_id="soc_seed",
        created_by="tester",
    )


def _request() -> ModelRequest:
    return ModelRequest(
        model_profile_id="claude-code-local",
        prompt_version_id="pv_answer_generation_v1",
        payload={"question": "이전 과제 power 이슈는?"},
        data_classification="public_internal",
        masking_applied=True,
        access_checked=True,
    )
