"""Confluence REST source adapter tests."""

from typing import Any

from req_tracker.adapters.base import SourceAdapterRequestError, SourceScope
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


def test_confluence_rest_adapter_preserves_sections_and_table_cells() -> None:
    adapter = ConfluenceRestSourceAdapter(
        base_url="https://confluence.example.com",
        token="token",
        space_key="CAM",
        transport=lambda *_args: {
            "size": 1,
            "totalSize": 1,
            "results": [
                _page(
                    "124",
                    "Verification Matrix",
                    body=(
                        "<h1>Camera</h1>"
                        "<h2>Verification</h2>"
                        "<table><tr><th>Requirement</th><th>Verification</th></tr>"
                        "<tr><td>CAM-REQ-001</td><td>CAM-VER-002</td></tr></table>"
                    ),
                )
            ],
        },
    )

    result = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA"))

    artifact = result.artifacts[0]
    assert artifact.links == ["CAM-REQ-001", "CAM-VER-002"]
    assert artifact.metadata["section_paths"] == ["Camera", "Camera > Verification"]
    assert artifact.metadata["table_cells"] == [
        {
            "table_index": 0,
            "row_index": 0,
            "column_index": 0,
            "section_path": "Camera > Verification",
            "text_preview": "Requirement",
        },
        {
            "table_index": 0,
            "row_index": 0,
            "column_index": 1,
            "section_path": "Camera > Verification",
            "text_preview": "Verification",
        },
        {
            "table_index": 0,
            "row_index": 1,
            "column_index": 0,
            "section_path": "Camera > Verification",
            "text_preview": "CAM-REQ-001",
        },
        {
            "table_index": 0,
            "row_index": 1,
            "column_index": 1,
            "section_path": "Camera > Verification",
            "text_preview": "CAM-VER-002",
        },
    ]


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


def test_confluence_rest_adapter_retries_transient_server_error() -> None:
    calls = 0
    sleep_delays: list[float] = []

    def transport(
        _method: str,
        _url: str,
        _headers: dict[str, str],
        _payload: None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SourceAdapterRequestError("temporary failure", status_code=503)
        return {"size": 1, "totalSize": 1, "results": [_page("123", "Camera Architecture")]}

    adapter = ConfluenceRestSourceAdapter(
        base_url="https://confluence.example.com",
        token="token",
        space_key="CAM",
        transport=transport,
        max_retries=1,
        retry_sleep=sleep_delays.append,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA"))

    assert calls == 2
    assert sleep_delays == [0.25]
    assert result.partial_failure is True
    assert result.source_warnings == ["confluence_request_retry:503:attempt_1"]
    assert result.artifacts[0].external_id == "123"


def test_confluence_rest_adapter_reports_permission_denied_without_retry() -> None:
    calls = 0

    def transport(
        _method: str,
        _url: str,
        _headers: dict[str, str],
        _payload: None,
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise SourceAdapterRequestError("unauthorized", status_code=401)

    adapter = ConfluenceRestSourceAdapter(
        base_url="https://confluence.example.com",
        token="token",
        space_key="CAM",
        transport=transport,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA"))

    assert calls == 1
    assert result.artifacts == []
    assert result.partial_failure is True
    assert result.source_warnings == ["confluence_permission_denied:401"]


def _page(page_id: str, title: str, *, body: str | None = None) -> dict[str, Any]:
    return {
        "id": page_id,
        "title": title,
        "space": {"key": "CAM"},
        "body": {
            "storage": {
                "value": body or "<p>Design references CAM-REQ-001 and CAM-VER-002.</p>",
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
