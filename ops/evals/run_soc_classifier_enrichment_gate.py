"""Evaluate skip-safe Claude Code enrichment for SoC axis classification."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.config.settings import Settings
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.ingestion.soc_classification import GatewaySocAxisClassifier, classify_soc_axes
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.registry import ModelRegistry

DEFAULT_MODEL_PROFILE_ID = "claude-code-local"
PROMPT_VERSION_ID = "pv_soc_axis_classification_v1"
TASK_NAME = "soc_axis_classification"
RUN_ID = "soc_classifier_enrichment_gate"

ClientFactory = Callable[[str], Any]


def run_soc_classifier_enrichment_gate(
    *,
    live: bool,
    model_profile_id: str = DEFAULT_MODEL_PROFILE_ID,
    command: str = "",
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Return classifier enrichment results without invoking Claude unless live is true."""
    if not live:
        return _dry_run_payload(model_profile_id=model_profile_id, command=command)

    trace_counter: Callable[[], int] | None = None
    if client_factory is None:
        gateway_factory = _RegistryGatewayFactory(
            model_profile_id=model_profile_id,
            command_override=command,
        )
        factory: ClientFactory = gateway_factory
        trace_counter = gateway_factory.trace_count
        command_info = gateway_factory.command_info()
    else:
        factory = client_factory
        command_info = {"command": [], "command_status": "injected"}

    checks = {
        "classifier_enrichment": _classifier_enrichment_check(
            client=factory(TASK_NAME),
            model_profile_id=model_profile_id,
        )
    }
    failures = []
    if checks["classifier_enrichment"]["status"] != "passed":
        failures.append("classifier_enrichment_failed")
    return {
        "checks": checks,
        **command_info,
        "failure_count": len(failures),
        "failures": failures,
        "mode": "live",
        "model_profile_id": model_profile_id,
        "requires_live": True,
        "schema_version": "v1",
        "status": "passed" if not failures else "failed",
        "trace_count": trace_counter() if trace_counter is not None else 1,
    }


class _RegistryGatewayFactory:
    """Create model gateway clients from the configured registry."""

    def __init__(self, *, model_profile_id: str, command_override: str) -> None:
        settings = Settings()
        self._registry = ModelRegistry.from_json_files(
            profiles_path=Path(settings.model_profiles_path),
            prompts_path=Path(settings.prompt_versions_path),
        )
        self._profile = self._registry.get_profile(model_profile_id)
        command_text = command_override or settings.model_gateway_claude_command
        command_text = command_text or self._profile.endpoint_alias
        self._command = _command(command_text)
        self._provider = provider_for_profile(self._profile, claude_command=self._command)
        self._traces = InMemoryTraceRepository()

    def __call__(self, task_name: str) -> ModelGatewayClient:
        prompt = self._registry.active_prompt_for_task(task_name)  # type: ignore[arg-type]
        return ModelGatewayClient(
            provider=self._provider,
            profile=self._profile,
            prompt=prompt,
            trace_repo=self._traces,
        )

    def trace_count(self) -> int:
        return len(self._traces.llm_calls)

    def command_info(self) -> dict[str, Any]:
        return {
            "command": list(self._command),
            "command_status": "found" if shutil.which(self._command[0]) else "missing",
        }


def _classifier_enrichment_check(*, client: Any, model_profile_id: str) -> dict[str, Any]:
    artifact = _enrichment_artifact()
    baseline = classify_soc_axes(
        artifact,
        run_id=RUN_ID,
        step_id="soc_axis_classification_rule_baseline",
    )
    proposals = GatewaySocAxisClassifier(
        client=client,
        model_profile_id=model_profile_id,
        prompt_version_id=PROMPT_VERSION_ID,
    ).enrich_artifact(
        artifact,
        baseline_classifications=baseline,
        run_id=RUN_ID,
        step_id="soc_axis_classification_enrichment",
    )
    pending_count = sum(
        1 for item in proposals if item.source == "claude" and item.status == "pending"
    )
    return {
        "pending_count": pending_count,
        "prompt_version_id": PROMPT_VERSION_ID,
        "proposal_count": len(proposals),
        "response_model": "SocAxisClassificationBatch",
        "status": "passed" if pending_count > 0 else "failed",
    }


def _enrichment_artifact() -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id="SOC-CLAUDE-ENRICH-001",
        source_type="jira",
        source_url="https://jira.example.local/browse/SOC-CLAUDE-ENRICH-001",
        project_key="SOC-N-1",
        title="Camera shot response regression needs triage",
        body_text=(
            "Shot-to-shot camera response got worse after ISP queue changes. "
            "The artifact deliberately omits concern labels so Claude Code must "
            "infer the right SoC concern from the symptom."
        ),
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-02T00:00:00+00:00",
        labels=["level/L3", "component/camera"],
        metadata={"soc_fixture_seed": True, "masking_applied": True},
    )


def _dry_run_payload(*, model_profile_id: str, command: str) -> dict[str, Any]:
    command_tuple = _command(command or "claude -p --output-format json")
    return {
        "checks": {
            "classifier_enrichment": {
                "prompt_version_id": PROMPT_VERSION_ID,
                "requires_live": True,
                "response_model": "SocAxisClassificationBatch",
                "status": "skipped",
            }
        },
        "command": list(command_tuple),
        "command_status": "found" if shutil.which(command_tuple[0]) else "missing",
        "mode": "dry_run",
        "model_profile_id": model_profile_id,
        "requires_live": True,
        "schema_version": "v1",
        "status": "skipped",
    }


def _command(command_text: str) -> tuple[str, ...]:
    command = tuple(shlex.split(command_text)) if command_text.strip() else ()
    return command or ("claude", "-p", "--output-format", "json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke Claude Code.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Invoke Claude Code through model gateway.",
    )
    parser.add_argument("--command", default="", help="Override Claude Code command.")
    parser.add_argument("--model-profile-id", default=DEFAULT_MODEL_PROFILE_ID)
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


def main() -> int:
    args = _parse_args()
    report = run_soc_classifier_enrichment_gate(
        live=args.live and not args.dry_run,
        model_profile_id=args.model_profile_id,
        command=args.command,
    )
    _emit(report, args.format)
    return 0 if report["status"] in {"passed", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
