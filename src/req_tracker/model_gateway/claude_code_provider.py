"""Claude Code subprocess model provider.

This provider keeps Claude Code invocation behind the model gateway boundary.
It sends a provider-neutral JSON payload on stdin and expects JSON on stdout.
"""

from __future__ import annotations

import json
import subprocess
import time
from collections.abc import Callable, Sequence
from typing import Any, TypedDict

from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.model_gateway.providers import ModelProviderError

SubprocessRunner = Callable[
    [Sequence[str], str, int],
    subprocess.CompletedProcess[str],
]


class UsageMetadata(TypedDict):
    """Provider-normalized token and cost metadata."""

    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None


class ClaudeCodeSubprocessProvider:
    """Invoke Claude Code through a subprocess while preserving gateway tracing."""

    def __init__(
        self,
        *,
        command: Sequence[str] = ("claude-code",),
        runner: SubprocessRunner | None = None,
    ) -> None:
        if not command:
            raise ValueError("claude code command must not be empty")
        self._command = tuple(command)
        self._runner = runner or _subprocess_runner

    def complete(
        self,
        request_payload: ModelRequest,
        profile: ModelProfile,
        prompt: PromptVersion,
    ) -> ModelResponse:
        """Send one model request to Claude Code and normalize the JSON response."""
        body = {
            "model_profile_id": profile.model_profile_id,
            "provider": profile.provider,
            "model": profile.model_name,
            "task_name": prompt.task_name,
            "prompt_version_id": prompt.prompt_version_id,
            "prompt_template": prompt.template,
            "schema_version_ref": prompt.schema_version_ref,
            "retrieval_policy_id": prompt.retrieval_policy_id,
            "temperature": profile.default_temperature,
            "response_format": "json_object" if profile.supports_json_schema else "text",
            "structured_output_instruction": _structured_output_instruction(prompt),
            "expected_response_envelope": {"output": "<schema-valid JSON object>"},
            "payload": request_payload.payload,
        }
        input_text = json.dumps(body, ensure_ascii=False)
        started = time.perf_counter()
        try:
            completed = self._runner(
                self._command,
                input_text,
                profile.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ModelProviderError("claude-code subprocess timed out") from exc
        latency_ms = int((time.perf_counter() - started) * 1000)
        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            detail = f": {stderr}" if stderr else ""
            raise ModelProviderError(
                f"claude-code subprocess failed with exit code {completed.returncode}{detail}"
            )
        response = _normalize_response(_load_response(completed.stdout))
        output = response.get("output", response)
        if not isinstance(output, dict):
            raise ModelProviderError("claude-code response output must be an object")
        usage = _usage_metadata(response)
        return ModelResponse(
            model_profile_id=profile.model_profile_id,
            prompt_version_id=prompt.prompt_version_id,
            output=output,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
            cost_usd=usage["cost_usd"],
            latency_ms=latency_ms,
        )


def _subprocess_runner(
    command: Sequence[str],
    input_text: str,
    timeout_seconds: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_seconds,
        check=False,
    )


def _load_response(stdout: str) -> dict[str, Any]:
    try:
        loaded = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ModelProviderError("claude-code response must be JSON") from exc
    if not isinstance(loaded, dict):
        raise ModelProviderError("claude-code response must be an object")
    return loaded


def _normalize_response(response: dict[str, Any]) -> dict[str, Any]:
    result = response.get("result")
    if not isinstance(result, str):
        return response
    loaded_result = _load_json_object_from_text(result)
    if loaded_result is None:
        return response
    usage = response.get("usage")
    if isinstance(usage, dict) and "usage" not in loaded_result:
        loaded_result["usage"] = usage
    return loaded_result


def _structured_output_instruction(prompt: PromptVersion) -> str:
    return (
        "Return ONLY one valid JSON object. Do not include markdown fences, prose, "
        "analysis, comments, or surrounding text. The JSON must match the requested "
        f"schema_version_ref={prompt.schema_version_ref}. If an output envelope is "
        'requested, use exactly {"output": <schema-valid JSON object>}.'
    )


def _load_json_object_from_text(value: str) -> dict[str, Any] | None:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        loaded = _extract_json_object(value)
    if isinstance(loaded, dict):
        return loaded
    return None


def _extract_json_object(value: str) -> Any:
    decoder = json.JSONDecoder()
    for index, char in enumerate(value):
        if char != "{":
            continue
        try:
            loaded, _end = decoder.raw_decode(value[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    return None


def _usage_metadata(response: dict[str, Any]) -> UsageMetadata:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        usage = response
    return {
        "input_tokens": _non_negative_int(
            usage.get("input_tokens", usage.get("prompt_tokens"))
        ),
        "output_tokens": _non_negative_int(
            usage.get("output_tokens", usage.get("completion_tokens"))
        ),
        "cost_usd": _non_negative_float(usage.get("cost_usd")),
    }


def _non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _non_negative_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0.0 else None
