"""Export-file source adapter tests."""

import json

from req_tracker.adapters.base import SourceScope
from req_tracker.adapters.export_file import (
    ConfluenceExportSourceAdapter,
    DecisionEmailExportSourceAdapter,
    JiraExportSourceAdapter,
)


def _artifact(
    external_id: str,
    source_type: str,
    project_key: str = "RUNE_CAM_ALPHA",
) -> dict[str, object]:
    return {
        "external_id": external_id,
        "source_type": source_type,
        "source_url": f"export://{source_type}/{external_id}",
        "project_key": project_key,
        "title": f"{source_type} {external_id}",
        "body_text": f"{external_id} shall be traceable.",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "labels": ["export"],
        "links": [],
        "metadata": {"mbse_type": "Requirement"},
        "access_scope": ["RUNE_CAM_ALPHA"],
        "data_classification": "public_internal",
    }


def test_jira_export_adapter_reads_json_and_paginates(tmp_path) -> None:  # type: ignore[no-untyped-def]
    export_path = tmp_path / "jira.json"
    export_path.write_text(
        json.dumps(
            {
                "artifacts": [
                    _artifact("JIRA-1", "jira"),
                    _artifact("JIRA-2", "jira"),
                    _artifact("OTHER-1", "jira", "OTHER"),
                ]
            }
        ),
        encoding="utf-8",
    )
    adapter = JiraExportSourceAdapter(export_path)
    first = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA", limit=1))
    second = adapter.fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA", limit=1),
        first.next_cursor,
    )

    assert [item.external_id for item in first.artifacts] == ["JIRA-1"]
    assert [item.external_id for item in second.artifacts] == ["JIRA-2"]
    assert second.next_cursor is None


def test_confluence_and_decision_export_adapters_read_jsonl(tmp_path) -> None:  # type: ignore[no-untyped-def]
    confluence_path = tmp_path / "confluence.jsonl"
    decision_path = tmp_path / "decision.jsonl"
    confluence_path.write_text(
        json.dumps(_artifact("CONF-1", "confluence")) + "\n",
        encoding="utf-8",
    )
    decision_path.write_text(
        json.dumps(_artifact("DEC-1", "decision_archive")) + "\n",
        encoding="utf-8",
    )

    confluence = ConfluenceExportSourceAdapter(confluence_path).fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA")
    )
    decision = DecisionEmailExportSourceAdapter(decision_path).fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA")
    )

    assert confluence.artifacts[0].source_type == "confluence"
    assert decision.artifacts[0].source_type == "decision_archive"


def test_missing_export_file_reports_partial_failure(tmp_path) -> None:  # type: ignore[no-untyped-def]
    result = JiraExportSourceAdapter(tmp_path / "missing.json").fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA")
    )

    assert result.artifacts == []
    assert result.partial_failure is True
    assert result.source_warnings == ["export_file_missing"]
