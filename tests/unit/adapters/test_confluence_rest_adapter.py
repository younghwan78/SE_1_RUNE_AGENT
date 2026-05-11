"""Confluence REST source adapter tests."""

from typing import Any

from req_tracker.adapters.base import SourceScope
from req_tracker.adapters.confluence_rest import ConfluenceRestSourceAdapter


def test_confluence_rest_adapter_fetches_page_and_maps_contract() -> None:
    calls: list[dict[str, Any]] = []

    def transport(
        method: str,
        url: str,
        headers: dict[str, str],
        payload: None,
    ) -> dict[str, Any]:
        calls.append({"method": method, "url": url, "headers": headers, "payload": payload})
        return {
            "size": 1,
            "totalSize": 2,
            "results": [_page("123", "Camera Architecture")],
        }

    adapter = ConfluenceRestSourceAdapter(
        base_url="https://confluence.example.com",
        token="token",
        space_key="CAM",
        transport=transport,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA", limit=1))

    assert calls[0]["method"] == "GET"
    assert "space+%3D+%22CAM%22" in calls[0]["url"]
    assert result.next_cursor is not None
    assert result.next_cursor.offset == 1
    artifact = result.artifacts[0]
    assert artifact.external_id == "123"
    assert artifact.source_type == "confluence"
    assert artifact.body_text == "Design references CAM-REQ-001 and CAM-VER-002."
    assert artifact.links == ["CAM-REQ-001", "CAM-VER-002"]
    assert artifact.parent_id == "10"
    assert artifact.metadata["version_number"] == 3


def test_confluence_rest_adapter_reports_malformed_page_warning() -> None:
    adapter = ConfluenceRestSourceAdapter(
        base_url="https://confluence.example.com",
        token="",
        space_key="CAM",
        transport=lambda *_args: {"size": 1, "totalSize": 1, "results": [{"id": "broken"}]},
    )

    result = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA"))

    assert result.artifacts == []
    assert result.partial_failure is True
    assert result.source_warnings[0].startswith("confluence_page_skipped:broken")


def _page(page_id: str, title: str) -> dict[str, Any]:
    return {
        "id": page_id,
        "title": title,
        "space": {"key": "CAM"},
        "body": {
            "storage": {
                "value": "<p>Design references CAM-REQ-001 and CAM-VER-002.</p>",
            }
        },
        "version": {"number": 3, "when": "2026-01-03T00:00:00.000Z"},
        "history": {
            "createdDate": "2026-01-01T00:00:00.000Z",
            "createdBy": {"accountId": "user_1"},
        },
        "ancestors": [{"id": "5"}, {"id": "10"}],
        "metadata": {"labels": {"results": [{"name": "camera"}, {"name": "design"}]}},
    }
