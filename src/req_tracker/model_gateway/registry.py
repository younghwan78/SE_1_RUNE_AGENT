"""File-backed model profile and prompt registry."""

from pathlib import Path

from pydantic import TypeAdapter

from req_tracker.model_gateway.models import ModelProfile, PromptTask, PromptVersion

_MODEL_PROFILES = TypeAdapter(list[ModelProfile])
_PROMPT_VERSIONS = TypeAdapter(list[PromptVersion])


class ModelRegistryError(ValueError):
    """Raised when model registry lookup or loading fails."""


class ModelRegistry:
    """Read-only registry for model profiles and prompt versions."""

    def __init__(
        self,
        *,
        profiles: list[ModelProfile],
        prompts: list[PromptVersion],
    ) -> None:
        self._profiles = {profile.model_profile_id: profile for profile in profiles}
        self._prompts = {prompt.prompt_version_id: prompt for prompt in prompts}

    @classmethod
    def from_json_files(cls, *, profiles_path: Path, prompts_path: Path) -> "ModelRegistry":
        """Load registry entries from JSON files."""
        profiles = _MODEL_PROFILES.validate_json(profiles_path.read_text(encoding="utf-8"))
        prompts = _PROMPT_VERSIONS.validate_json(prompts_path.read_text(encoding="utf-8"))
        return cls(profiles=profiles, prompts=prompts)

    def get_profile(self, model_profile_id: str) -> ModelProfile:
        """Return an active model profile by id."""
        profile = self._profiles.get(model_profile_id)
        if profile is None:
            raise ModelRegistryError(f"model profile not found: {model_profile_id}")
        if not profile.is_active:
            raise ModelRegistryError(f"model profile is not active: {model_profile_id}")
        return profile

    def get_prompt(self, prompt_version_id: str) -> PromptVersion:
        """Return a prompt version by id."""
        prompt = self._prompts.get(prompt_version_id)
        if prompt is None:
            raise ModelRegistryError(f"prompt version not found: {prompt_version_id}")
        return prompt

    def active_prompt_for_task(self, task_name: PromptTask) -> PromptVersion:
        """Return the active prompt for a task."""
        matches = [
            prompt
            for prompt in self._prompts.values()
            if prompt.task_name == task_name and prompt.status == "active"
        ]
        if len(matches) != 1:
            raise ModelRegistryError(
                f"expected exactly one active prompt for task '{task_name}', found {len(matches)}"
            )
        return matches[0]
