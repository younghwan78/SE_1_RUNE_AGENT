"""Model provider factory."""

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
) -> ModelProvider:
    """Create a provider implementation for a model profile."""
    if profile.provider == "dummy":
        return DummyModelProvider()
    if not endpoint_url:
        raise ValueError("endpoint_url is required for non-dummy model profiles")
    return HttpJsonModelProvider(endpoint_url=endpoint_url, api_key=api_key, transport=transport)
