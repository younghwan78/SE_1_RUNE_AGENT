"""Rehearse restricted decision/email export ingestion.

This script validates an exported decision archive or approved limited-email
export without reading a broad mailbox. It uses DecisionEmailExportSourceAdapter
and reports only artifact ids, counts, warnings, and classification metadata.
"""

import argparse
import json
import os
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from req_tracker.adapters.base import SourceScope
from req_tracker.adapters.export_file import DecisionEmailExportSourceAdapter


@dataclass(frozen=True)
class DecisionEmailRehearsalConfig:
    """Restricted decision/email export rehearsal config."""

    export_path: Path | None
    export_path_present: bool
    project_key: str
    limit: int


def main() -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-path", type=Path)
    parser.add_argument("--project-key")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    result = run_decision_email_export_rehearsal(
        os.environ,
        export_path=args.export_path,
        project_key=args.project_key,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def run_decision_email_export_rehearsal(
    env: Mapping[str, str],
    *,
    export_path: Path | None = None,
    project_key: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run restricted decision/email export rehearsal and return a report."""
    config = _config_from_inputs(
        env,
        export_path=export_path,
        project_key=project_key,
        limit=limit,
    )
    missing = _missing_config(config)
    if missing:
        return {
            "passed": False,
            "status": "missing_config",
            "missing": missing,
            "config": _safe_config(config),
            "artifacts": [],
            "warnings": [],
        }
    try:
        assert config.export_path is not None
        result = DecisionEmailExportSourceAdapter(config.export_path).fetch_incremental(
            SourceScope(project_key=config.project_key, limit=config.limit)
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "passed": False,
            "status": "export_read_failed",
            "error_type": exc.__class__.__name__,
            "config": _safe_config(config),
            "artifacts": [],
            "warnings": [],
        }
    artifacts = [
        {
            "external_id": artifact.external_id,
            "source_type": artifact.source_type,
            "project_key": artifact.project_key,
            "classification": artifact.data_classification,
            "labels": artifact.labels,
            "mbse_type": artifact.metadata.get("mbse_type"),
            "decision_source_approved": artifact.metadata.get("decision_source_approved"),
        }
        for artifact in result.artifacts
    ]
    skipped = [
        warning
        for warning in result.source_warnings
        if warning.startswith("decision_email_artifact_skipped:")
    ]
    manual_review = [
        warning
        for warning in result.source_warnings
        if warning.startswith("decision_email_manual_review_required:")
    ]
    passed = bool(artifacts) and all(
        artifact["source_type"] in {"email", "decision_archive"} for artifact in artifacts
    )
    return {
        "passed": passed,
        "status": "passed" if passed else "no_approved_decision_artifacts",
        "config": _safe_config(config),
        "artifact_count": len(artifacts),
        "skipped_count": len(skipped),
        "manual_review_count": len(manual_review),
        "next_cursor_present": result.next_cursor is not None,
        "partial_failure": result.partial_failure,
        "artifacts": artifacts,
        "warnings": result.source_warnings,
        "schema_version": "v1",
    }


def _config_from_inputs(
    env: Mapping[str, str],
    *,
    export_path: Path | None,
    project_key: str | None,
    limit: int | None,
) -> DecisionEmailRehearsalConfig:
    raw_path = export_path or _optional_path(env.get("RUNE_EMAIL_EXPORT_PATH"))
    return DecisionEmailRehearsalConfig(
        export_path=raw_path,
        export_path_present=raw_path is not None and raw_path.is_file(),
        project_key=project_key or env.get("RUNE_PROJECT_KEY", "RUNE_CAM_ALPHA"),
        limit=(
            limit
            if limit and limit > 0
            else _positive_int(env.get("RUNE_EMAIL_EXPORT_LIMIT"), 50)
        ),
    )


def _missing_config(config: DecisionEmailRehearsalConfig) -> list[str]:
    if not config.export_path_present:
        return ["RUNE_EMAIL_EXPORT_PATH"]
    return []


def _safe_config(config: DecisionEmailRehearsalConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["export_path"] = "<set>" if config.export_path is not None else "<unset>"
    return payload


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value)


def _positive_int(value: str | None, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


if __name__ == "__main__":
    raise SystemExit(main())
