"""Local JIRA and Confluence REST source-adapter smoke harness.

The harness starts a disposable localhost source server and exercises the real
JiraRestSourceAdapter and ConfluenceRestSourceAdapter over HTTP. It validates
pagination, artifact mapping, links, and permission-denied warning behavior
without using company systems or MCP tool names.
"""

import argparse
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib import parse

from req_tracker.adapters.base import SourceScope
from req_tracker.adapters.confluence_rest import ConfluenceRestSourceAdapter
from req_tracker.adapters.jira_rest import JiraRestSourceAdapter


class _SourceHandler(BaseHTTPRequestHandler):
    """Small deterministic source server for localhost adapter validation."""

    server_version = "RuneMockSource/1.0"

    def do_POST(self) -> None:  # noqa: N802
        if self.headers.get("authorization") == "Bearer deny":
            self._send_json({"error": "forbidden"}, status=403)
            return
        if self.path != "/rest/api/3/search":
            self._send_json({"error": "not found"}, status=404)
            return
        body = self.rfile.read(int(self.headers.get("content-length", "0")))
        payload = json.loads(body.decode("utf-8")) if body else {}
        start = int(payload.get("startAt", 0)) if isinstance(payload, dict) else 0
        limit = int(payload.get("maxResults", 1)) if isinstance(payload, dict) else 1
        issues = _jira_issues()
        self._send_json({"total": len(issues), "issues": issues[start : start + limit]})

    def do_GET(self) -> None:  # noqa: N802
        if self.headers.get("authorization") == "Bearer deny":
            self._send_json({"error": "unauthorized"}, status=401)
            return
        parsed = parse.urlparse(self.path)
        if parsed.path != "/wiki/rest/api/content/search":
            self._send_json({"error": "not found"}, status=404)
            return
        query = parse.parse_qs(parsed.query)
        start = int(query.get("start", ["0"])[0])
        limit = int(query.get("limit", ["1"])[0])
        pages = _confluence_pages()
        self._send_json(
            {
                "size": len(pages[start : start + limit]),
                "totalSize": len(pages),
                "results": pages[start : start + limit],
            }
        )

    def log_message(self, _format: str, *_args: object) -> None:
        """Suppress default HTTP request logs for stable smoke output."""

    def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def mock_source_server(port: int = 0) -> Iterator[str]:
    """Run a disposable local source server and yield its base URL."""
    server = ThreadingHTTPServer(("127.0.0.1", port), _SourceHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run_source_adapter_smoke(*, port: int = 0) -> dict[str, Any]:
    """Run JIRA and Confluence REST adapter smoke checks."""
    with mock_source_server(port) as base_url:
        jira_adapter = JiraRestSourceAdapter(base_url=base_url, token="ok")
        jira_first = jira_adapter.fetch_incremental(SourceScope(project_key="CAM", limit=1))
        jira_second = jira_adapter.fetch_incremental(
            SourceScope(project_key="CAM", limit=1),
            cursor=jira_first.next_cursor,
        )
        jira_denied = JiraRestSourceAdapter(base_url=base_url, token="deny").fetch_incremental(
            SourceScope(project_key="CAM", limit=1)
        )

        confluence_adapter = ConfluenceRestSourceAdapter(
            base_url=base_url,
            token="ok",
            space_key="CAM",
        )
        confluence_first = confluence_adapter.fetch_incremental(
            SourceScope(project_key="RUNE_CAM_ALPHA", limit=1)
        )
        confluence_second = confluence_adapter.fetch_incremental(
            SourceScope(project_key="RUNE_CAM_ALPHA", limit=1),
            cursor=confluence_first.next_cursor,
        )
        confluence_denied = ConfluenceRestSourceAdapter(
            base_url=base_url,
            token="deny",
            space_key="CAM",
        ).fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA", limit=1))

        jira_artifacts = [*jira_first.artifacts, *jira_second.artifacts]
        confluence_artifacts = [*confluence_first.artifacts, *confluence_second.artifacts]
        passed = (
            len(jira_artifacts) == 2
            and len(confluence_artifacts) == 2
            and jira_second.next_cursor is None
            and confluence_second.next_cursor is None
            and jira_denied.source_warnings == ["jira_permission_denied:403"]
            and confluence_denied.source_warnings == ["confluence_permission_denied:401"]
        )
        return {
            "passed": passed,
            "base_url": base_url,
            "jira_artifacts": [artifact.external_id for artifact in jira_artifacts],
            "jira_links": sorted({link for artifact in jira_artifacts for link in artifact.links}),
            "jira_permission_warnings": jira_denied.source_warnings,
            "confluence_artifacts": [
                artifact.external_id for artifact in confluence_artifacts
            ],
            "confluence_links": sorted(
                {link for artifact in confluence_artifacts for link in artifact.links}
            ),
            "confluence_permission_warnings": confluence_denied.source_warnings,
            "schema_version": "v1",
        }


def main() -> int:
    """Run the local source-adapter smoke harness."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    result = run_source_adapter_smoke(port=args.port)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def _jira_issues() -> list[dict[str, Any]]:
    return [
        _jira_issue("CAM-REQ-001", "Camera latency requirement", "CAM-VER-001"),
        _jira_issue("CAM-VER-001", "Camera latency validation", "CAM-REQ-001"),
    ]


def _jira_issue(key: str, summary: str, linked_key: str) -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "description": {"content": [{"content": [{"text": f"{summary} body"}]}]},
            "issuetype": {"name": "Requirement" if "REQ" in key else "Verification"},
            "status": {"name": "Open"},
            "priority": {"name": "High"},
            "labels": ["camera", "latency"],
            "components": [{"name": "Camera"}],
            "fixVersions": [{"name": "R1"}],
            "reporter": {"accountId": "source_user"},
            "created": "2026-01-01T00:00:00.000+0000",
            "updated": "2026-01-02T00:00:00.000+0000",
            "issuelinks": [{"outwardIssue": {"key": linked_key}}],
            "parent": {"key": "CAM-EPIC-001"},
            "subtasks": [],
        },
    }


def _confluence_pages() -> list[dict[str, Any]]:
    return [
        _confluence_page("1001", "Camera Architecture", "CAM-REQ-001"),
        _confluence_page("1002", "Camera Verification Plan", "CAM-VER-001"),
    ]


def _confluence_page(page_id: str, title: str, linked_key: str) -> dict[str, Any]:
    return {
        "id": page_id,
        "title": title,
        "space": {"key": "CAM"},
        "body": {"storage": {"value": f"<p>{title} references {linked_key}.</p>"}},
        "version": {"number": 1, "when": "2026-01-03T00:00:00.000Z"},
        "history": {
            "createdDate": "2026-01-01T00:00:00.000Z",
            "createdBy": {"accountId": "source_user"},
        },
        "ancestors": [{"id": "10"}],
        "metadata": {"labels": {"results": [{"name": "camera"}]}},
    }


if __name__ == "__main__":
    raise SystemExit(main())
