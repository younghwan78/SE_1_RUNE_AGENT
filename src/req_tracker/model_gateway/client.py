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
    ) -> None:
        self._provider = provider
        self._profile = profile
        self._prompt = prompt
        self._policy = policy or ModelPolicy()
        self._trace_repo = trace_repo
        self._artifact_store = artifact_store

    def complete(
        self,
        *,
        run_id: str,
        step_id: str,
        request: ModelRequest,
        response_model: type[TModel] | None = None,
    ) -> tuple[ModelResponse, TModel | None, StructuredValidationResult]:
        """Complete a request and optionally validate structured output."""
        self._policy.assert_allowed(request, self._profile)
        masked_payload_ref = self._write_artifact(run_id, "masked_payload", request.payload)

        try:
            response = self._provider.complete(request, self._profile, self._prompt)
        except Exception as exc:
            trace = self._build_trace(
                run_id=run_id,
                step_id=step_id,
                request=request,
                masked_payload_ref=masked_payload_ref,
                response=None,
                validation=StructuredValidationResult(
                    status="failed",
                    error_message=str(exc),
                ),
                error_message=str(exc),
            )
            self._record_trace(trace)
            raise

        raw_response_ref = self._write_artifact(run_id, "raw_response", response.output)
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
            parsed_output_ref = self._write_artifact(run_id, "parsed_output", parsed_payload)

        response = response.model_copy(
            update={
                "raw_response_ref": raw_response_ref,
                "parsed_output_ref": parsed_output_ref,
            }
        )
        trace = self._build_trace(
            run_id=run_id,
            step_id=step_id,
            request=request,
            masked_payload_ref=masked_payload_ref,
            response=response,
            validation=validation,
            error_message=validation.error_message,
        )
        self._record_trace(trace)
        return response, parsed, validation

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
    ) -> LLMCallTrace:
        response_hash = stable_hash(response.output) if response is not None else None
        call_hash = stable_hash(
            {
                "run_id": run_id,
                "step_id": step_id,
                "request": request.model_dump(mode="json"),
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
            latency_ms=response.latency_ms if response is not None else 0,
            validation_status=validation.status,
            retry_count=0,
            error_message=error_message,
        )

    def _record_trace(self, trace: LLMCallTrace) -> None:
        if self._trace_repo is not None:
            self._trace_repo.record_llm_call(trace)
