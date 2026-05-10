"""Model provider protocol."""

from typing import Protocol

from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)


class ModelProvider(Protocol):
    """Provider interface hidden behind the model gateway."""

    def complete(
        self,
        request: ModelRequest,
        profile: ModelProfile,
        prompt: PromptVersion,
    ) -> ModelResponse:
        """Return a model response for a request."""
