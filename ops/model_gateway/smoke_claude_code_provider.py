"""Smoke check for the Claude Code model-gateway provider."""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
from pathlib import Path
from typing import Any

from req_tracker.config.settings import Settings
from req_tracker.debug.traces import InMemoryTraceRepository
from req_tracker.model_gateway.client import ModelGatewayClient
from req_tracker.model_gateway.factory import provider_for_profile
from req_tracker.model_gateway.models import ModelRequest
from req_tracker.model_gateway.registry import ModelRegistry
from req_tracker.ontology.soc_models import SocSlice


def main() -> None:
    args = _parse_args()
    settings = Settings()
    registry = ModelRegistry.from_json_files(
        profiles_path=Path(settings.model_profiles_path),
        prompts_path=Path(settings.prompt_versions_path),
    )
    profile = registry.get_profile(args.model_profile_id)
    prompt = registry.active_prompt_for_task("soc_slice_planning")
    command_text = args.command or settings.model_gateway_claude_command or profile.endpoint_alias
    command = _command(command_text)
    command_status = "found" if shutil.which(command[0]) else "missing"

    if args.dry_run or not args.live:
        _emit(
            {
                "status": "skipped",
                "mode": "dry_run",
                "reason": "pass --live to invoke the Claude Code subprocess",
                "command": list(command),
                "command_status": command_status,
                "model_profile_id": profile.model_profile_id,
                "prompt_version_id": prompt.prompt_version_id,
            },
            args.format,
        )
        return

    provider = provider_for_profile(profile, claude_command=command)
    traces = InMemoryTraceRepository()
    client = ModelGatewayClient(
        provider=provider,
        profile=profile,
        prompt=prompt,
        trace_repo=traces,
    )
    request = ModelRequest(
        model_profile_id=profile.model_profile_id,
        prompt_version_id=prompt.prompt_version_id,
        payload={
            "user_query": "Camera shot performance issue?",
            "allowed_patterns": [
                "concern_slice",
                "topic_intersection",
                "timeline_slice",
                "lifecycle_trace",
                "unknown",
            ],
            "output_contract": "Return SocSlice JSON only.",
        },
        data_classification="public_internal",
        masking_applied=True,
        access_checked=True,
    )
    _response, parsed, validation = client.complete(
        run_id="smoke_claude_code_provider",
        step_id="soc_slice_planning",
        request=request,
        response_model=SocSlice,
    )
    _emit(
        {
            "status": _live_status(parsed, validation.status),
            "mode": "live",
            "command": list(command),
            "command_status": command_status,
            "model_profile_id": profile.model_profile_id,
            "prompt_version_id": prompt.prompt_version_id,
            "validation_status": validation.status,
            "trace_count": len(traces.llm_calls),
            "parsed": parsed.model_dump(mode="json") if parsed is not None else None,
            "error": validation.error_message,
        },
        args.format,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not invoke Claude Code.")
    parser.add_argument("--live", action="store_true", help="Invoke Claude Code subprocess.")
    parser.add_argument("--command", default="", help="Override Claude Code command.")
    parser.add_argument(
        "--model-profile-id",
        default="claude-code-local",
        help="Model profile to smoke test.",
    )
    parser.add_argument("--format", choices=["json", "text"], default="text")
    return parser.parse_args()


def _command(command_text: str) -> tuple[str, ...]:
    command = tuple(shlex.split(command_text)) if command_text.strip() else ()
    return command or ("claude", "-p", "--output-format", "json")


def _live_status(parsed: SocSlice | None, validation_status: str) -> str:
    if parsed is not None and validation_status == "passed":
        return "passed"
    return "failed"


def _emit(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
