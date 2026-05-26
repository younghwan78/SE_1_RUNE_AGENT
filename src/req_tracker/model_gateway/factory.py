"""Model provider factory."""

import shlex
from collections.abc import Sequence

from req_tracker.model_gateway.claude_code_provider import ClaudeCodeSubprocessProvider
from req_tracker.model_gateway.dummy_provider import DummyModelProvider
from req_tracker.model_gateway.http_provider import HttpJsonModelProvider, HttpModelTransport
from req_tracker.model_gateway.models import ModelProfile
from req_tracker.model_gateway.providers import ModelProvider


def provider_for_profile(
    profile: ModelProfile,
    *,
    endpoint_url: str = "",
    api_key: str = "",
    transport: HttpModelTransport | None = None,
    claude_command: Sequence[str] | None = None,
) -> ModelProvider:
    """Create a provider implementation for a model profile."""
    if profile.provider == "dummy":
        return DummyModelProvider()
    if profile.provider == "claude_code":
        return ClaudeCodeSubprocessProvider(
            command=claude_command
            or tuple(shlex.split(profile.endpoint_alias))
            or ("claude", "-p", "--output-format", "json"),
        )
    if not endpoint_url:
        raise ValueError("endpoint_url is required for non-dummy model profiles")
    return HttpJsonModelProvider(endpoint_url=endpoint_url, api_key=api_key, transport=transport)
