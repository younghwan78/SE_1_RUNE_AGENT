"""Generic HTTP JSON model provider.

This provider targets company-approved model gateways or thin provider wrappers.
It intentionally avoids provider-specific SDKs so the application boundary stays
model-agnostic.
"""

import json
import time
from collections.abc import Callable
from typing import Any, TypedDict
from urllib import error, request

from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)
from req_tracker.model_gateway.providers import ModelProviderError

HttpModelTransport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]


class UsageMetadata(TypedDict):
    """Provider-normalized token and cost metadata."""

    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None


class HttpJsonModelProvider:
    """Call a JSON-over-HTTP model gateway and normalize the response."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        api_key: str = "",
        transport: HttpModelTransport | None = None,
    ) -> None:
        if not endpoint_url:
            raise ValueError("model endpoint_url is required")
        self._endpoint_url = endpoint_url
        self._api_key = api_key
        self._transport = transport or _urllib_transport

    def complete(
        self,
        request_payload: ModelRequest,
        profile: ModelProfile,
        prompt: PromptVersion,
    ) -> ModelResponse:
        """Send a provider-neutral JSON request to a model gateway."""
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-model-profile-id": profile.model_profile_id,
            "x-prompt-version-id": prompt.prompt_version_id,
        }
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
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
            "payload": request_payload.payload,
        }
        started = time.perf_counter()
        response = self._transport(self._endpoint_url, headers, body, profile.timeout_seconds)
        latency_ms = int((time.perf_counter() - started) * 1000)
        output = response.get("output", response)
        if not isinstance(output, dict):
            raise ModelProviderError("model gateway response output must be an object")
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


def _urllib_transport(
    endpoint_url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(endpoint_url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise ModelProviderError(f"model gateway http request failed: {exc.code}") from exc
    except error.URLError as exc:
        raise ModelProviderError(f"model gateway network request failed: {exc.reason}") from exc
    if not isinstance(loaded, dict):
        raise ModelProviderError("model gateway response must be an object")
    return loaded


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
