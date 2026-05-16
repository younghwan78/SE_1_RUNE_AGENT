"""Model gateway client with policy, validation, and trace recording."""

from typing import Any, TypeVar

from pydantic import BaseModel

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.hash import stable_hash
from req_tracker.debug.models import LLMCallTrace
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.models import (
    ModelProfile,
    ModelRequest,
    ModelResponse,
    PromptVersion,
    StructuredValidationResult,
)
from req_tracker.model_gateway.policy import ModelPolicy
from req_tracker.model_gateway.providers import ModelProvider
from req_tracker.model_gateway.structured_output import validate_structured_output

TModel = TypeVar("TModel", bound=BaseModel)


class ModelGatewayClient:
    """Model-agnostic gateway facade."""

    def __init__(
        self,
        *,
        provider: ModelProvider,
        profile: ModelProfile,
        prompt: PromptVersion,
        policy: ModelPolicy | None = None,
        trace_repo: InMemoryTraceRepository | None = None,
        artifact_store: LocalArtifactStore | None = None,
        max_validation_retries: int = 0,
        fallback_provider: ModelProvider | None = None,
        fallback_profile: ModelProfile | None = None,
        fallback_prompt: PromptVersion | None = None,
    ) -> None:
        self._provider = provider
        self._profile = profile
        self._prompt = prompt
        self._policy = policy or ModelPolicy()
        self._trace_repo = trace_repo
        self._artifact_store = artifact_store
        self._max_validation_retries = max_validation_retries
        self._fallback_provider = fallback_provider
        self._fallback_profile = fallback_profile
        self._fallback_prompt = fallback_prompt

    def complete(
        self,
        *,
        run_id: str,
        step_id: str,
        request: ModelRequest,
        response_model: type[TModel] | None = None,
    ) -> tuple[ModelResponse, TModel | None, StructuredValidationResult]:
        """Complete a request and optionally validate structured output."""
        attempts = self._attempts(request)
        last_exc: Exception | None = None
        last_response: ModelResponse | None = None
        last_parsed: TModel | None = None
        last_validation = StructuredValidationResult(
            status="failed",
            error_message="model gateway did not run",
        )
        for provider, profile, prompt, attempt_request, retry_count in attempts:
            self._policy.assert_allowed(attempt_request, profile)
            masked_payload_ref = self._write_artifact(
                run_id,
                f"{step_id}_masked_payload_{retry_count}",
                attempt_request.payload,
            )
            try:
                response = provider.complete(attempt_request, profile, prompt)
            except Exception as exc:
                last_exc = exc
                self._record_trace(
                    self._build_trace(
                        run_id=run_id,
                        step_id=step_id,
                        request=attempt_request,
                        masked_payload_ref=masked_payload_ref,
                        response=None,
                        validation=StructuredValidationResult(
                            status="failed",
                            error_message=str(exc),
                        ),
                        error_message=str(exc),
                        retry_count=retry_count,
                    )
                )
                continue

            raw_response_ref = self._write_artifact(
                run_id,
                f"{step_id}_raw_response_{retry_count}",
                response.output,
            )
            parsed: TModel | None = None
            if response_model is None:
                validation = StructuredValidationResult(status="passed")
                parsed_output_ref = raw_response_ref
            else:
                parsed, validation = validate_structured_output(response.output, response_model)
                parsed_payload = (
                    parsed.model_dump(mode="json")
                    if parsed is not None
                    else {"error": validation.error_message}
                )
                parsed_output_ref = self._write_artifact(
                    run_id,
                    f"{step_id}_parsed_output_{retry_count}",
                    parsed_payload,
                )
            response = response.model_copy(
                update={
                    "raw_response_ref": raw_response_ref,
                    "parsed_output_ref": parsed_output_ref,
                }
            )
            self._record_trace(
                self._build_trace(
                    run_id=run_id,
                    step_id=step_id,
                    request=attempt_request,
                    masked_payload_ref=masked_payload_ref,
                    response=response,
                    validation=validation,
                    error_message=validation.error_message,
                    retry_count=retry_count,
                )
            )
            last_response = response
            last_parsed = parsed
            last_validation = validation
            if validation.status == "passed":
                return response, parsed, validation

        if last_response is not None:
            return last_response, last_parsed, last_validation
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("model gateway attempts exhausted")

    def _write_artifact(self, run_id: str, name: str, payload: dict[str, Any]) -> str:
        if self._artifact_store is None:
            return f"memory://{run_id}/{name}/{stable_hash(payload)[:12]}"
        ref = self._artifact_store.write_json(run_id, name, payload)
        return ref.artifact_ref

    def _build_trace(
        self,
        *,
        run_id: str,
        step_id: str,
        request: ModelRequest,
        masked_payload_ref: str,
        response: ModelResponse | None,
        validation: StructuredValidationResult,
        error_message: str | None,
        retry_count: int,
    ) -> LLMCallTrace:
        response_hash = stable_hash(response.output) if response is not None else None
        call_hash = stable_hash(
            {
                "run_id": run_id,
                "step_id": step_id,
                "request": request.model_dump(mode="json"),
                "retry_count": retry_count,
            }
        )
        return LLMCallTrace(
            llm_call_id=f"llm_{call_hash[:16]}",
            run_id=run_id,
            step_id=step_id,
            model_profile_id=request.model_profile_id,
            prompt_version_id=request.prompt_version_id,
            request_hash=stable_hash(request),
            response_hash=response_hash,
            masked_payload_ref=masked_payload_ref,
            raw_response_ref=response.raw_response_ref if response is not None else None,
            parsed_output_ref=response.parsed_output_ref if response is not None else None,
            input_tokens=response.input_tokens if response is not None else None,
            output_tokens=response.output_tokens if response is not None else None,
            cost_usd=response.cost_usd if response is not None else None,
            latency_ms=response.latency_ms if response is not None else 0,
            validation_status=validation.status,
            retry_count=retry_count,
            error_message=error_message,
        )

    def _record_trace(self, trace: LLMCallTrace) -> None:
        if self._trace_repo is not None:
            self._trace_repo.record_llm_call(trace)

    def _attempts(
        self,
        request: ModelRequest,
    ) -> list[tuple[ModelProvider, ModelProfile, PromptVersion, ModelRequest, int]]:
        attempts: list[tuple[ModelProvider, ModelProfile, PromptVersion, ModelRequest, int]] = []
        for retry_count in range(self._max_validation_retries + 1):
            attempts.append((self._provider, self._profile, self._prompt, request, retry_count))
        if self._fallback_provider and self._fallback_profile:
            fallback_prompt = self._fallback_prompt or self._prompt
            fallback_request = request.model_copy(
                update={
                    "model_profile_id": self._fallback_profile.model_profile_id,
                    "prompt_version_id": fallback_prompt.prompt_version_id,
                }
            )
            attempts.append(
                (
                    self._fallback_provider,
                    self._fallback_profile,
                    fallback_prompt,
                    fallback_request,
                    len(attempts),
                )
            )
        return attempts
