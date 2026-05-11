"""JIRA REST source adapter tests."""

from typing import Any

from req_tracker.adapters.base import SourceAdapterRequestError, SourceScope
from req_tracker.adapters.jira_rest import JiraRestSourceAdapter


def test_jira_rest_adapter_fetches_page_and_maps_issue_contract() -> None:
    calls: list[dict[str, Any]] = []

    def transport(
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append({"method": method, "url": url, "headers": headers, "payload": payload})
        return {
            "total": 2,
            "issues": [_issue("CAM-REQ-001", "Camera latency")],
        }

    adapter = JiraRestSourceAdapter(
        base_url="https://jira.example.com",
        token="token",
        transport=transport,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="CAM", limit=1))

    assert calls[0]["method"] == "POST"
    assert calls[0]["payload"]["jql"] == "project = CAM ORDER BY updated ASC"
    assert result.next_cursor is not None
    assert result.next_cursor.offset == 1
    assert result.partial_failure is False
    artifact = result.artifacts[0]
    assert artifact.external_id == "CAM-REQ-001"
    assert artifact.source_url == "https://jira.example.com/browse/CAM-REQ-001"
    assert artifact.body_text == "Camera must open fast"
    assert artifact.links == ["CAM-VER-001"]
    assert artifact.metadata["jira_issue_type"] == "Requirement"


def test_jira_rest_adapter_reports_malformed_issue_warning() -> None:
    adapter = JiraRestSourceAdapter(
        base_url="https://jira.example.com",
        token="",
        transport=lambda *_args: {"total": 1, "issues": [{"key": "BROKEN"}]},
    )

    result = adapter.fetch_incremental(SourceScope(project_key="CAM"))

    assert result.artifacts == []
    assert result.partial_failure is True
    assert result.source_warnings[0].startswith("jira_issue_skipped:BROKEN")


def test_jira_rest_adapter_retries_rate_limited_request() -> None:
    calls = 0
    sleep_delays: list[float] = []

    def transport(
        _method: str,
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise SourceAdapterRequestError(
                "rate limited",
                status_code=429,
                retry_after_seconds=0.25,
            )
        return {"total": 1, "issues": [_issue("CAM-REQ-001", "Camera latency")]}

    adapter = JiraRestSourceAdapter(
        base_url="https://jira.example.com",
        token="token",
        transport=transport,
        max_retries=1,
        retry_sleep=sleep_delays.append,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="CAM"))

    assert calls == 2
    assert sleep_delays == [0.25]
    assert result.partial_failure is True
    assert result.source_warnings == ["jira_request_retry:429:attempt_1"]
    assert result.artifacts[0].external_id == "CAM-REQ-001"


def test_jira_rest_adapter_retries_network_os_error() -> None:
    calls = 0

    def transport(
        _method: str,
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionAbortedError("local smoke server reset")
        return {"total": 1, "issues": [_issue("CAM-REQ-001", "Camera latency")]}

    adapter = JiraRestSourceAdapter(
        base_url="https://jira.example.com",
        token="token",
        transport=transport,
        max_retries=1,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="CAM"))

    assert calls == 2
    assert result.partial_failure is True
    assert result.source_warnings == ["jira_request_retry:network_error:attempt_1"]
    assert result.artifacts[0].external_id == "CAM-REQ-001"


def test_jira_rest_adapter_reports_permission_denied_without_retry() -> None:
    calls = 0

    def transport(
        _method: str,
        _url: str,
        _headers: dict[str, str],
        _payload: dict[str, Any],
    ) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise SourceAdapterRequestError("forbidden", status_code=403)

    adapter = JiraRestSourceAdapter(
        base_url="https://jira.example.com",
        token="token",
        transport=transport,
    )

    result = adapter.fetch_incremental(SourceScope(project_key="CAM"))

    assert calls == 1
    assert result.artifacts == []
    assert result.partial_failure is True
    assert result.source_warnings == ["jira_permission_denied:403"]


def _issue(key: str, summary: str) -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "description": {
                "content": [
                    {"content": [{"text": "Camera must open fast"}]},
                ]
            },
            "issuetype": {"name": "Requirement"},
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "labels": ["camera", "latency"],
            "components": [{"name": "Camera"}],
            "fixVersions": [{"name": "R1"}],
            "reporter": {"accountId": "user_1"},
            "created": "2026-01-01T00:00:00.000+0000",
            "updated": "2026-01-02T00:00:00.000+0000",
            "issuelinks": [{"outwardIssue": {"key": "CAM-VER-001"}}],
            "parent": {"key": "CAM-EPIC-001"},
            "subtasks": [{"key": "CAM-TASK-001"}],
        },
    }
