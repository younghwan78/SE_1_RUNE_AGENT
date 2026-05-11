"""Model provider protocol."""

from typing import Protocol

from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)


class ModelProviderError(RuntimeError):
    """Raised when a model provider request fails before structured validation."""


class ModelProvider(Protocol):
    """Provider interface hidden behind the model gateway."""

    def complete(
        self,
        request: ModelRequest,
        profile: ModelProfile,
        prompt: PromptVersion,
    ) -> ModelResponse:
        """Return a model response for a request."""
