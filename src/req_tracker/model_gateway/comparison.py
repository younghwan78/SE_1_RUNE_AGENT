"""Model gateway comparison helpers for controlled model/prompt changes."""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.hash import stable_hash
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    PromptVersion,
)
from req_tracker.model_gateway.providers import ModelProvider


@dataclass(frozen=True)
class ModelGatewayCandidate:
    """A model gateway execution candidate for comparison."""

    provider: ModelProvider
    profile: ModelProfile
    prompt: PromptVersion
    label: str | None = None


class ModelGatewayComparisonResult(BaseModel):
    """Single candidate result in a model gateway comparison."""

    model_config = ConfigDict(extra="forbid")

    label: str
    model_profile_id: str
    prompt_version_id: str
    validation_status: str
    validation_error: str | None = None
    output_hash: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class ModelGatewayComparisonReport(BaseModel):
    """Comparison report for the same input across model/prompt candidates."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "v1"
    run_id: str
    step_id: str
    input_payload_hash: str
    compared_model_profile_ids: list[str]
    compared_prompt_version_ids: list[str]
    validation_statuses: dict[str, str]
    results: list[ModelGatewayComparisonResult]
    output_changed: bool
    output_diff: dict[str, Any]


def compare_model_gateway_candidates(
    *,
    run_id: str,
    step_id: str,
    request: ModelRequest,
    candidates: list[ModelGatewayCandidate],
    response_model: type[BaseModel] | None = None,
    trace_repo: InMemoryTraceRepository | None = None,
    artifact_store: LocalArtifactStore | None = None,
) -> ModelGatewayComparisonReport:
    """Run the same payload through candidates and return a diff report."""
    if len(candidates) < 2:
        raise ValueError("at least two candidates are required for comparison")

    results: list[ModelGatewayComparisonResult] = []
    for index, candidate in enumerate(candidates):
        candidate_label = candidate.label or candidate.profile.model_profile_id
        candidate_request = request.model_copy(
            update={
                "model_profile_id": candidate.profile.model_profile_id,
                "prompt_version_id": candidate.prompt.prompt_version_id,
            }
        )
        client = ModelGatewayClient(
            provider=candidate.provider,
            profile=candidate.profile,
            prompt=candidate.prompt,
            trace_repo=trace_repo,
            artifact_store=artifact_store,
        )
        try:
            response, _parsed, validation = client.complete(
                run_id=run_id,
                step_id=f"{step_id}_{index}",
                request=candidate_request,
                response_model=response_model,
            )
            output = response.output
            result = ModelGatewayComparisonResult(
                label=candidate_label,
                model_profile_id=candidate.profile.model_profile_id,
                prompt_version_id=candidate.prompt.prompt_version_id,
                validation_status=validation.status,
                validation_error=validation.error_message,
                output_hash=stable_hash(output),
                output=output,
                latency_ms=response.latency_ms,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                cost_usd=response.cost_usd,
            )
        except Exception as exc:
            result = ModelGatewayComparisonResult(
                label=candidate_label,
                model_profile_id=candidate.profile.model_profile_id,
                prompt_version_id=candidate.prompt.prompt_version_id,
                validation_status="failed",
                validation_error=str(exc),
            )
        results.append(result)

    output_diff = _diff_outputs(results[0].output, results[1].output)
    return ModelGatewayComparisonReport(
        run_id=run_id,
        step_id=step_id,
        input_payload_hash=stable_hash(request.payload),
        compared_model_profile_ids=_unique_non_empty(
            *(result.model_profile_id for result in results)
        ),
        compared_prompt_version_ids=_unique_non_empty(
            *(result.prompt_version_id for result in results)
        ),
        validation_statuses={
            result.model_profile_id: result.validation_status for result in results
        },
        results=results,
        output_changed=bool(
            output_diff["added"] or output_diff["removed"] or output_diff["changed"]
        ),
        output_diff=output_diff,
    )


def _diff_outputs(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_keys = set(left)
    right_keys = set(right)
    return {
        "added": {key: right[key] for key in sorted(right_keys - left_keys)},
        "removed": {key: left[key] for key in sorted(left_keys - right_keys)},
        "changed": {
            key: {"left": left[key], "right": right[key]}
            for key in sorted(left_keys & right_keys)
            if left[key] != right[key]
        },
    }


def _unique_non_empty(*values: str | None) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))
