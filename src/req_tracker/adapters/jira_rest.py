"""JIRA REST source adapter.

This adapter is intentionally transport-injected. Claude Code skills can decide
whether data came from MCP, REST, export, or another company-approved path, while
the application only sees the stable SourceAdapter contract.
"""

import json
import time
from collections.abc import Callable
from typing import Any
from urllib import error, request

from req_tracker.adapters.base import (
    RawSourceArtifact,
    SourceAdapterRequestError,
    SourceFetchResult,
    SourceScope,
    SyncCursor,
)
from req_tracker.adapters.retry import RetrySleep, parse_retry_after, request_with_retry
from req_tracker.debug.hash import stable_hash

JiraTransport = Callable[[str, str, dict[str, str], dict[str, Any]], dict[str, Any]]


class JiraRestSourceAdapter:
    """Fetch JIRA issues through REST and normalize them into raw source artifacts."""

    source_type = "jira"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        jql: str | None = None,
        transport: JiraTransport | None = None,
        max_retries: int = 2,
        retry_sleep: RetrySleep | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("jira base_url is required")
        if not token and transport is None:
            raise ValueError("jira token is required when transport is not provided")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.jql = jql
        self._transport = transport or _urllib_transport
        self._max_retries = max_retries
        self._retry_sleep = retry_sleep or time.sleep

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch one page of JIRA issues."""
        offset = cursor.offset if cursor else 0
        payload = {
            "jql": self.jql or f"project = {scope.project_key} ORDER BY updated ASC",
            "startAt": offset,
            "maxResults": scope.limit,
            "fields": [
                "summary",
                "description",
                "issuetype",
                "status",
                "priority",
                "labels",
                "components",
                "fixVersions",
                "reporter",
                "assignee",
                "created",
                "updated",
                "issuelinks",
                "parent",
                "subtasks",
            ],
        }
        headers = {
            "authorization": f"Bearer {self.token}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        response, request_warnings = request_with_retry(
            source_type="jira",
            max_retries=self._max_retries,
            retry_sleep=self._retry_sleep,
            request_call=lambda: self._transport(
                "POST",
                f"{self.base_url}/rest/api/3/search",
                headers,
                payload,
            ),
        )
        if response is None:
            return SourceFetchResult(
                artifacts=[],
                next_cursor=None,
                source_warnings=request_warnings,
                partial_failure=True,
            )
        issues = response.get("issues", [])
        if not isinstance(issues, list):
            return SourceFetchResult(
                artifacts=[],
                next_cursor=None,
                source_warnings=[*request_warnings, "jira_response_issues_not_list"],
                partial_failure=True,
            )
        artifacts: list[RawSourceArtifact] = []
        warnings: list[str] = list(request_warnings)
        for issue in issues:
            try:
                artifacts.append(_issue_to_artifact(issue, self.base_url, scope.project_key))
            except (KeyError, TypeError, ValueError) as exc:
                issue_key = issue.get("key", "unknown") if isinstance(issue, dict) else "unknown"
                warnings.append(f"jira_issue_skipped:{issue_key}:{exc.__class__.__name__}")
        total = int(response.get("total", offset + len(issues)))
        next_offset = offset + len(issues)
        next_cursor = None
        if next_offset < total:
            next_cursor = SyncCursor(offset=next_offset, content_hash=stable_hash(artifacts))
        return SourceFetchResult(
            artifacts=artifacts,
            next_cursor=next_cursor,
            source_warnings=warnings,
            partial_failure=bool(warnings),
        )


def _issue_to_artifact(
    issue: dict[str, Any],
    base_url: str,
    project_key: str,
) -> RawSourceArtifact:
    fields = issue["fields"]
    key = str(issue["key"])
    body = _extract_text(fields.get("description"))
    labels = [str(label) for label in fields.get("labels", [])]
    links = _issue_links(fields)
    metadata = {
        "jira_issue_type": _nested_name(fields.get("issuetype")),
        "jira_status": _nested_name(fields.get("status")),
        "jira_priority": _nested_name(fields.get("priority")),
        "components": [_nested_name(component) for component in fields.get("components", [])],
        "fix_versions": [_nested_name(version) for version in fields.get("fixVersions", [])],
    }
    parent = fields.get("parent")
    subtasks = fields.get("subtasks", [])
    return RawSourceArtifact(
        external_id=key,
        source_type="jira",
        source_url=f"{base_url}/browse/{key}",
        project_key=project_key,
        title=str(fields.get("summary") or key),
        body_text=body or str(fields.get("summary") or key),
        author_id=_account_id(fields.get("reporter")),
        created_at=str(fields["created"]),
        updated_at=str(fields["updated"]),
        labels=labels,
        links=links,
        parent_id=str(parent["key"]) if isinstance(parent, dict) and "key" in parent else None,
        child_ids=[
            str(subtask["key"])
            for subtask in subtasks
            if isinstance(subtask, dict) and "key" in subtask
        ],
        metadata=metadata,
        access_scope=[project_key],
        data_classification="public_internal",
    )


def _issue_links(fields: dict[str, Any]) -> list[str]:
    links: list[str] = []
    for link in fields.get("issuelinks", []):
        if not isinstance(link, dict):
            continue
        for key in ("outwardIssue", "inwardIssue"):
            linked = link.get(key)
            if isinstance(linked, dict) and "key" in linked:
                links.append(str(linked["key"]))
    return list(dict.fromkeys(links))


def _extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(part for item in value if (part := _extract_text(item)))
    if isinstance(value, dict):
        parts: list[str] = []
        text = value.get("text")
        if isinstance(text, str):
            parts.append(text)
        content = value.get("content")
        if isinstance(content, list):
            parts.extend(part for item in content if (part := _extract_text(item)))
        return "\n".join(parts)
    return ""


def _nested_name(value: Any) -> str | None:
    if isinstance(value, dict) and value.get("name") is not None:
        return str(value["name"])
    return None


def _account_id(value: Any) -> str | None:
    if isinstance(value, dict):
        account_id = value.get("accountId") or value.get("name")
        if account_id is not None:
            return str(account_id)
    return None


def _urllib_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise SourceAdapterRequestError(
            f"jira http request failed: {exc.code}",
            status_code=exc.code,
            retry_after_seconds=parse_retry_after(exc.headers.get("Retry-After")),
        ) from exc
    except error.URLError as exc:
        raise SourceAdapterRequestError(
            f"jira network request failed: {exc.reason}",
            code="network_error",
        ) from exc
    if not isinstance(loaded, dict):
        raise ValueError("jira response must be an object")
    return loaded
