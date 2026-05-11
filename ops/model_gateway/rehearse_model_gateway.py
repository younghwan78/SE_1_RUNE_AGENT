"""Run an env-driven model gateway rehearsal against a company sandbox endpoint.

The script targets the provider-neutral HTTP JSON contract used by
HttpJsonModelProvider. It prints trace/validation metadata and masks API keys.
"""

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from req_tracker.debug.artifacts import LocalArtifactStore
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.http_provider import HttpJsonModelProvider
from req_tracker.model_gateway.models import ModelProfile, ModelRequest, PromptVersion, Provider


class GatewayProbeOutput(BaseModel):
    """Expected model gateway probe output."""

    probe_id: str
    confidence_score: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class GatewayRehearsalConfig:
    """Model gateway rehearsal config loaded from environment."""

    endpoint_url: str
    api_key_present: bool
    api_key: str
    model_profile_id: str
    provider: Provider
    model_name: str
    prompt_version_id: str
    timeout_seconds: int
    artifact_root: str | None


def main() -> int:
    """CLI entrypoint."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run_model_gateway_rehearsal(os.environ)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def run_model_gateway_rehearsal(env: Mapping[str, str]) -> dict[str, Any]:
    """Run one structured-output request against a configured model gateway."""
    config = _config_from_env(env)
    missing = _missing_config(config)
    if missing:
        return {
            "passed": False,
            "status": "missing_config",
            "missing": missing,
            "config": _safe_config(config),
            "traces": [],
        }
    try:
        result = _run_probe(config)
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "status": "probe_failed",
            "error_type": exc.__class__.__name__,
            "config": _safe_config(config),
            "traces": [],
        }
    return result


def _run_probe(config: GatewayRehearsalConfig) -> dict[str, Any]:
    trace_repo = InMemoryTraceRepository()
    with tempfile.TemporaryDirectory() as temp_dir:
        artifact_root = Path(config.artifact_root) if config.artifact_root else Path(temp_dir)
        artifact_store = LocalArtifactStore(artifact_root)
        profile = _profile(config)
        prompt = _prompt(config)
        client = ModelGatewayClient(
            provider=HttpJsonModelProvider(
                endpoint_url=config.endpoint_url,
                api_key=config.api_key,
            ),
            profile=profile,
            prompt=prompt,
            trace_repo=trace_repo,
            artifact_store=artifact_store,
        )
        _response, parsed, validation = client.complete(
            run_id="run_company_model_gateway_rehearsal",
            step_id="step_company_model_gateway_rehearsal",
            request=ModelRequest(
                model_profile_id=profile.model_profile_id,
                prompt_version_id=prompt.prompt_version_id,
                payload={
                    "probe_id": "MODEL-GATEWAY-PROBE-001",
                    "instruction": (
                        "Return JSON with probe_id='MODEL-GATEWAY-PROBE-001' "
                        "and confidence_score between 0 and 1."
                    ),
                },
                data_classification="public_internal",
            ),
            response_model=GatewayProbeOutput,
        )
        traces = sorted(trace_repo.llm_calls.values(), key=lambda item: item.retry_count)
        trace_payloads = [
            {
                "model_profile_id": trace.model_profile_id,
                "prompt_version_id": trace.prompt_version_id,
                "validation_status": trace.validation_status,
                "retry_count": trace.retry_count,
                "request_hash": trace.request_hash,
                "response_hash_present": trace.response_hash is not None,
                "raw_response_ref_present": trace.raw_response_ref is not None,
                "parsed_output_ref_present": trace.parsed_output_ref is not None,
                "error_type": None if trace.error_message is None else "model_gateway_error",
            }
            for trace in traces
        ]
        passed = (
            validation.status == "passed"
            and parsed is not None
            and parsed.probe_id == "MODEL-GATEWAY-PROBE-001"
        )
        return {
            "passed": passed,
            "status": "passed" if passed else "validation_failed",
            "config": _safe_config(config),
            "validation_status": validation.status,
            "output": None if parsed is None else parsed.model_dump(mode="json"),
            "trace_count": len(traces),
            "traces": trace_payloads,
            "schema_version": "v1",
        }


def _config_from_env(env: Mapping[str, str]) -> GatewayRehearsalConfig:
    provider = env.get("MODEL_GATEWAY_PROVIDER", "internal")
    if provider not in {"internal", "openai", "anthropic", "azure", "local", "dummy"}:
        provider = "internal"
    api_key = env.get("MODEL_GATEWAY_API_KEY", "")
    return GatewayRehearsalConfig(
        endpoint_url=env.get("MODEL_GATEWAY_ENDPOINT_URL", ""),
        api_key_present=bool(api_key),
        api_key=api_key,
        model_profile_id=env.get("MODEL_GATEWAY_PROFILE_ID", "company-sandbox"),
        provider=provider,
        model_name=env.get("MODEL_GATEWAY_MODEL_NAME", "company-sandbox-model"),
        prompt_version_id=env.get("MODEL_GATEWAY_PROMPT_VERSION_ID", "pv_company_probe"),
        timeout_seconds=_positive_int(env.get("MODEL_GATEWAY_TIMEOUT_SECONDS"), default=30),
        artifact_root=env.get("MODEL_GATEWAY_REHEARSAL_ARTIFACT_ROOT"),
    )


def _missing_config(config: GatewayRehearsalConfig) -> list[str]:
    missing: list[str] = []
    if not config.endpoint_url:
        missing.append("MODEL_GATEWAY_ENDPOINT_URL")
    return missing


def _safe_config(config: GatewayRehearsalConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["endpoint_url"] = "<set>" if config.endpoint_url else "<unset>"
    payload["api_key"] = "<set>" if config.api_key_present else "<unset>"
    return payload


def _profile(config: GatewayRehearsalConfig) -> ModelProfile:
    return ModelProfile(
        model_profile_id=config.model_profile_id,
        provider=config.provider,
        model_name=config.model_name,
        endpoint_alias="company-sandbox-gateway",
        allowed_data_classes=["public_internal"],
        supports_json_schema=True,
        supports_tool_calling=False,
        max_context_tokens=4096,
        default_temperature=0.0,
        timeout_seconds=config.timeout_seconds,
    )


def _prompt(config: GatewayRehearsalConfig) -> PromptVersion:
    return PromptVersion(
        prompt_version_id=config.prompt_version_id,
        task_name="node_extraction",
        template=(
            "Return a JSON object with probe_id exactly matching the input probe_id "
            "and confidence_score as a number from 0 to 1."
        ),
        schema_version_ref="gateway_probe_output.v1",
        retrieval_policy_id="ret_company_probe",
        created_by="ops",
        status="active",
    )


def _positive_int(value: str | None, *, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


if __name__ == "__main__":
    raise SystemExit(main())
