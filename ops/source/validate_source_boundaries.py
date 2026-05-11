"""Validate source adapter boundaries for MCP isolation and no write-back."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = ROOT / "src" / "req_tracker"
ADAPTER_ROOT = CORE_ROOT / "adapters"

FORBIDDEN_CORE_SNIPPETS = (
    "RUNE_JIRA_MCP_URL",
    "RUNE_CONFLUENCE_MCP_URL",
    ".mcp.json",
    "mcp_tool",
    "mcp_server",
    "jira_mcp",
    "confluence_mcp",
    "email_mcp",
)
FORBIDDEN_ADAPTER_SNIPPETS = (
    '"PUT"',
    '"PATCH"',
    '"DELETE"',
    "'PUT'",
    "'PATCH'",
    "'DELETE'",
    "write_back",
    "writeback",
    "send_email",
    "update_issue",
    "create_issue",
    "delete_issue",
    "update_page",
    "create_page",
    "delete_page",
)


def validate_source_boundaries(
    *,
    core_root: Path = CORE_ROOT,
    adapter_root: Path = ADAPTER_ROOT,
) -> dict[str, Any]:
    """Return a structured source-boundary validation report."""
    core_hits = _scan_files(core_root, FORBIDDEN_CORE_SNIPPETS)
    adapter_hits = _scan_files(adapter_root, FORBIDDEN_ADAPTER_SNIPPETS)
    return {
        "core_root": _display_path(core_root),
        "adapter_root": _display_path(adapter_root),
        "forbidden_core_hits": core_hits,
        "forbidden_adapter_hits": adapter_hits,
        "passed": not core_hits and not adapter_hits,
        "schema_version": "v1",
    }


def _scan_files(root: Path, snippets: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    if not root.exists():
        return [f"{_display_path(root)}:missing_root"]
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet in text:
                hits.append(f"{_display_path(path)}:{snippet}")
    return hits


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    """CLI entrypoint."""
    report = validate_source_boundaries()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
