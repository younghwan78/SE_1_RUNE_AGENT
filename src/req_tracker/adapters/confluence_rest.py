"""Confluence REST source adapter."""

import html
import json
import re
import time
from collections.abc import Callable
from typing import Any
from urllib import error, parse, request

from req_tracker.adapters.base import (
    RawSourceArtifact,
    SourceAdapterRequestError,
    SourceFetchResult,
    SourceScope,
    SyncCursor,
)
from req_tracker.adapters.retry import RetrySleep, parse_retry_after, request_with_retry
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import SourceType

ConfluenceTransport = Callable[[str, str, dict[str, str], None], dict[str, Any]]


class ConfluenceRestSourceAdapter:
    """Fetch Confluence pages through REST and normalize them into raw artifacts."""

    source_type: SourceType = "confluence"

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        space_key: str,
        cql: str | None = None,
        transport: ConfluenceTransport | None = None,
        max_retries: int = 2,
        retry_sleep: RetrySleep | None = None,
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
        self._max_retries = max_retries
        self._retry_sleep = retry_sleep or time.sleep

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
        response, request_warnings = request_with_retry(
            source_type="confluence",
            max_retries=self._max_retries,
            retry_sleep=self._retry_sleep,
            request_call=lambda: self._transport(
                "GET",
                f"{self.base_url}/wiki/rest/api/content/search?{query}",
                {"authorization": f"Bearer {self.token}", "accept": "application/json"},
                None,
            ),
        )
        if response is None:
            return SourceFetchResult(
                artifacts=[],
                next_cursor=None,
                source_warnings=request_warnings,
                partial_failure=True,
            )
        results = response.get("results", [])
        if not isinstance(results, list):
            return SourceFetchResult(
                artifacts=[],
                next_cursor=None,
                source_warnings=[*request_warnings, "confluence_response_results_not_list"],
                partial_failure=True,
            )
        artifacts: list[RawSourceArtifact] = []
        warnings: list[str] = list(request_warnings)
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
    previous_version_number = _previous_version_number(page)
    storage_html = str(page.get("body", {}).get("storage", {}).get("value", ""))
    body_text = _html_to_text(storage_html)
    section_paths = _extract_section_paths(storage_html)
    table_cells = _extract_table_cells(storage_html, section_path=_section_at_end(section_paths))
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
            **(
                {"previous_version_number": previous_version_number}
                if previous_version_number is not None
                else {}
            ),
            "ancestor_ids": ancestors,
            "section_paths": section_paths,
            "table_cells": table_cells,
        },
        access_scope=[project_key, str(page.get("space", {}).get("key") or "")],
        data_classification="public_internal",
    )


def _html_to_text(value: str) -> str:
    text = value.replace("<br />", "\n").replace("<br/>", "\n")
    text = re.sub(r"</(p|div|li|h[1-6]|tr|td|th)>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(html.unescape(text).split())


def _extract_section_paths(value: str) -> list[str]:
    headings: list[str | None] = [None] * 6
    section_paths: list[str] = []
    for match in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", value, flags=re.IGNORECASE | re.DOTALL):
        level = int(match.group(1))
        text = _html_to_text(match.group(2))
        if not text:
            continue
        headings[level - 1] = text
        for index in range(level, len(headings)):
            headings[index] = None
        section_paths.append(" > ".join(heading for heading in headings if heading))
    return section_paths


def _extract_table_cells(value: str, *, section_path: str | None) -> list[dict[str, object]]:
    cells: list[dict[str, object]] = []
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", flags=re.IGNORECASE | re.DOTALL)
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", flags=re.IGNORECASE | re.DOTALL)
    cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", flags=re.IGNORECASE | re.DOTALL)
    for table_index, table_match in enumerate(table_pattern.finditer(value)):
        for row_index, row_match in enumerate(row_pattern.finditer(table_match.group(1))):
            for column_index, cell_match in enumerate(cell_pattern.finditer(row_match.group(1))):
                text = _html_to_text(cell_match.group(1))
                if not text:
                    continue
                cells.append(
                    {
                        "table_index": table_index,
                        "row_index": row_index,
                        "column_index": column_index,
                        "section_path": section_path,
                        "text_preview": text[:120],
                    }
                )
    return cells


def _section_at_end(section_paths: list[str]) -> str | None:
    if not section_paths:
        return None
    return section_paths[-1]


def _previous_version_number(page: dict[str, Any]) -> int | None:
    for container_name in ("history", "version"):
        previous = page.get(container_name, {}).get("previousVersion")
        if isinstance(previous, dict):
            value = previous.get("number")
            if isinstance(value, int) and not isinstance(value, bool):
                return value
    return None


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
    try:
        with request.urlopen(req, timeout=30) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise SourceAdapterRequestError(
            f"confluence http request failed: {exc.code}",
            status_code=exc.code,
            retry_after_seconds=parse_retry_after(exc.headers.get("Retry-After")),
        ) from exc
    except error.URLError as exc:
        raise SourceAdapterRequestError(
            f"confluence network request failed: {exc.reason}",
            code="network_error",
        ) from exc
    if not isinstance(loaded, dict):
        raise ValueError("confluence response must be an object")
    return loaded
