"""Deterministic dummy model provider for local validation."""

from collections.abc import Mapping
from typing import Any

from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
)


class DummyModelTimeoutError(TimeoutError):
    """Raised by dummy fixtures to simulate provider timeout."""


class DummyModelProvider:
    """Return deterministic fixture responses without live model access."""

    def __init__(self, fixtures: Mapping[str, dict[str, Any]] | None = None) -> None:
        self._fixtures = dict(fixtures or {})

    def complete(
        self,
        request: ModelRequest,
        profile: ModelProfile,
        prompt: PromptVersion,
    ) -> ModelResponse:
        """Return fixture output selected by request payload."""
        fixture_name = str(request.payload.get("fixture_name", "default"))
        if fixture_name == "timeout":
            raise DummyModelTimeoutError("dummy model timeout")

        output = self._fixtures.get(fixture_name)
        if output is None:
            output = {
                "provider": profile.provider,
                "model_name": profile.model_name,
                "task_name": prompt.task_name,
                "echo": request.payload,
            }

        return ModelResponse(
            model_profile_id=profile.model_profile_id,
            prompt_version_id=prompt.prompt_version_id,
            output=output,
            latency_ms=0,
        )
