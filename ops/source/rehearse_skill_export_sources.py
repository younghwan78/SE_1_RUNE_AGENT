"""Rehearse source-skill export files without company systems.

This validates the same app-level datasource factory and workflow injection path
that company Claude Code source skills use after writing approved export files.
It creates local synthetic exports only; no company endpoint, token, MCP tool, or
mailbox is required.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from fastapi.testclient import TestClient

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings

ExportMode = Literal["jira_export", "confluence_export", "decision_email_export"]


def main() -> int:
    """CLI entrypoint."""
    report = run_skill_export_rehearsal()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


def run_skill_export_rehearsal() -> dict[str, Any]:
    """Run all local source-skill export datasource modes through the API."""
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        results = [
            _run_mode(root, mode)
            for mode in ("jira_export", "confluence_export", "decision_email_export")
        ]
    return {
        "passed": all(result["passed"] for result in results),
        "results": results,
        "schema_version": "v1",
    }


def _run_mode(root: Path, mode: ExportMode) -> dict[str, Any]:
    export_path = root / f"{mode}.jsonl"
    _write_export(export_path, mode)
    app = create_app(
        Settings(
            artifact_root=root / f"artifacts_{mode}",
            datasource_mode=mode,
            source_export_path=export_path,
        )
    )
    run_id = f"run_{mode}"
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/runs/ingest",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": run_id,
            },
        )
        cursors = client.get("/api/v1/debug/source-cursors?project_key=RUNE_CAM_ALPHA")
    response_payload = response.json() if response.status_code == 200 else {}
    cursor_payload = cursors.json() if cursors.status_code == 200 else []
    artifact_count = response_payload.get("counts", {}).get("artifacts", 0)
    expected_source = _expected_cursor_source(mode)
    expected_cursor_id = f"src_cursor_{expected_source}_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA"
    cursor = cursor_payload[0] if cursor_payload else {}
    return {
        "mode": mode,
        "passed": (
            response.status_code == 200
            and cursors.status_code == 200
            and artifact_count == 1
            and cursor.get("cursor_id") == expected_cursor_id
            and cursor.get("run_id") == run_id
        ),
        "status_code": response.status_code,
        "artifact_count": artifact_count,
        "cursor_id": cursor.get("cursor_id"),
        "run_id": cursor.get("run_id"),
        "source_warnings": cursor.get("source_warnings", []),
    }


def _write_export(path: Path, mode: ExportMode) -> None:
    artifact = _artifact_for_mode(mode)
    path.write_text(json.dumps(artifact.model_dump(mode="json")) + "\n", encoding="utf-8")


def _artifact_for_mode(mode: ExportMode) -> RawSourceArtifact:
    if mode == "jira_export":
        return _artifact(
            external_id="CAM-REQ-EXPORT-001",
            source_type="jira",
            labels=["requirement"],
            metadata={"mbse_type": "Requirement"},
        )
    if mode == "confluence_export":
        return _artifact(
            external_id="CONF-CAM-EXPORT-001",
            source_type="confluence",
            labels=["architecture"],
            metadata={"mbse_type": "Architecture_Block"},
        )
    return _artifact(
        external_id="MAIL-DEC-EXPORT-001",
        source_type="email",
        labels=["decision"],
        metadata={
            "mbse_type": "Decision",
            "decision_source_approved": True,
        },
    )


def _artifact(
    *,
    external_id: str,
    source_type: str,
    labels: list[str],
    metadata: dict[str, object],
) -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id=external_id,
        source_type=source_type,
        source_url=f"export://{source_type}/{external_id}",
        project_key="RUNE_CAM_ALPHA",
        title=external_id,
        body_text=f"{external_id} source skill export rehearsal body.",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        labels=labels,
        links=[],
        metadata=metadata,
        access_scope=["RUNE_CAM_ALPHA"],
        data_classification="public_internal",
    )


def _expected_cursor_source(mode: ExportMode) -> str:
    if mode == "jira_export":
        return "jira"
    if mode == "confluence_export":
        return "confluence"
    return "decision_archive"


if __name__ == "__main__":
    raise SystemExit(main())
