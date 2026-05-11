"""Confluence REST source adapter."""

import json
import re
from collections.abc import Callable
from typing import Any
from urllib import parse, request

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult, SourceScope, SyncCursor
from req_tracker.debug.hash import stable_hash

ConfluenceTransport = Callable[[str, str, dict[str, str], None], dict[str, Any]]


class ConfluenceRestSourceAdapter:
    """Fetch Confluence pages through REST and normalize them into raw artifacts."""

    source_type = "confluence"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        space_key: str,
        cql: str | None = None,
        transport: ConfluenceTransport | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("confluence base_url is required")
        if not space_key:
            raise ValueError("confluence space_key is required")
        if not token and transport is None:
            raise ValueError("confluence token is required when transport is not provided")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.space_key = space_key
        self.cql = cql
        self._transport = transport or _urllib_transport

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch one page of Confluence content."""
        offset = cursor.offset if cursor else 0
        cql = self.cql or f'space = "{self.space_key}" and type = page order by lastmodified asc'
        query = parse.urlencode(
            {
                "cql": cql,
                "start": offset,
                "limit": scope.limit,
                "expand": "body.storage,version,history,ancestors,metadata.labels",
            }
        )
        response = self._transport(
            "GET",
            f"{self.base_url}/wiki/rest/api/content/search?{query}",
            {"authorization": f"Bearer {self.token}", "accept": "application/json"},
            None,
        )
        results = response.get("results", [])
        if not isinstance(results, list):
            return SourceFetchResult(
                artifacts=[],
                next_cursor=None,
                source_warnings=["confluence_response_results_not_list"],
                partial_failure=True,
            )
        artifacts: list[RawSourceArtifact] = []
        warnings: list[str] = []
        for page in results:
            try:
                artifacts.append(_page_to_artifact(page, self.base_url, scope.project_key))
            except (KeyError, TypeError, ValueError) as exc:
                page_id = page.get("id", "unknown") if isinstance(page, dict) else "unknown"
                warnings.append(f"confluence_page_skipped:{page_id}:{exc.__class__.__name__}")
        size = int(response.get("size", len(results)))
        total = int(response.get("totalSize", offset + size))
        next_offset = offset + size
        next_cursor = None
        if next_offset < total:
            next_cursor = SyncCursor(offset=next_offset, content_hash=stable_hash(artifacts))
        return SourceFetchResult(
            artifacts=artifacts,
            next_cursor=next_cursor,
            source_warnings=warnings,
            partial_failure=bool(warnings),
        )


def _page_to_artifact(
    page: dict[str, Any],
    base_url: str,
    project_key: str,
) -> RawSourceArtifact:
    page_id = str(page["id"])
    version = page.get("version", {})
    history = page.get("history", {})
    body_text = _html_to_text(
        page.get("body", {}).get("storage", {}).get("value", "")
    )
    labels = [
        str(label.get("name"))
        for label in page.get("metadata", {}).get("labels", {}).get("results", [])
        if isinstance(label, dict) and label.get("name")
    ]
    ancestors = [
        str(ancestor.get("id"))
        for ancestor in page.get("ancestors", [])
        if isinstance(ancestor, dict) and ancestor.get("id")
    ]
    return RawSourceArtifact(
        external_id=page_id,
        source_type="confluence",
        source_url=f"{base_url}/wiki/pages/{page_id}",
        project_key=project_key,
        title=str(page.get("title") or page_id),
        body_text=body_text or str(page.get("title") or page_id),
        author_id=_account_id(history.get("createdBy")),
        created_at=str(history.get("createdDate") or version["when"]),
        updated_at=str(version["when"]),
        labels=labels,
        links=_extract_jira_keys(body_text),
        parent_id=ancestors[-1] if ancestors else None,
        child_ids=[],
        metadata={
            "space_key": page.get("space", {}).get("key"),
            "version_number": version.get("number"),
            "ancestor_ids": ancestors,
        },
        access_scope=[project_key, str(page.get("space", {}).get("key") or "")],
        data_classification="public_internal",
    )


def _html_to_text(value: str) -> str:
    text = value.replace("<br />", "\n").replace("<br/>", "\n").replace("</p>", "\n")
    result: list[str] = []
    in_tag = False
    for char in text:
        if char == "<":
            in_tag = True
            continue
        if char == ">":
            in_tag = False
            continue
        if not in_tag:
            result.append(char)
    return " ".join("".join(result).split())


def _extract_jira_keys(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)*-\d+\b", text)))


def _account_id(value: Any) -> str | None:
    if isinstance(value, dict):
        account_id = value.get("accountId") or value.get("username") or value.get("displayName")
        if account_id is not None:
            return str(account_id)
    return None


def _urllib_transport(
    method: str,
    url: str,
    headers: dict[str, str],
    _payload: None,
) -> dict[str, Any]:
    req = request.Request(url, headers=headers, method=method)
    with request.urlopen(req, timeout=30) as response:
        loaded = json.loads(response.read().decode("utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("confluence response must be an object")
    return loaded
