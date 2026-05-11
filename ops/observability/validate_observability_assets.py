"""Validate production-shaped observability assets without external services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OBS_ROOT = ROOT / "ops" / "observability"

REQUIRED_FILES = (
    "prometheus.yml",
    "rune-agent-alerts.yml",
    "grafana-dashboard.json",
)

REQUIRED_METRICS = (
    "rune_http_requests_total",
    "rune_http_request_duration_ms_sum",
    "rune_llm_calls_total",
    "rune_llm_input_tokens_total",
    "rune_llm_output_tokens_total",
    "rune_llm_cost_usd_total",
    "rune_graph_nodes",
    "rune_graph_approved_edges",
    "rune_approval_items_total",
    "rune_feedback_events_total",
    "rune_audit_events",
    "rune_scheduler_runs_started_total",
    "rune_scheduler_lease_skips_total",
)

FORBIDDEN_SNIPPETS = (
    "authorization:",
    "basic_auth:",
    "bearer_token",
    "password:",
    "api_key:",
    "client_secret",
)


def validate_observability_assets(root: Path = OBS_ROOT) -> dict[str, Any]:
    """Return a structured validation report for observability config assets."""
    missing_files = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    combined = _combined_text(root)
    forbidden_hits = [
        snippet for snippet in FORBIDDEN_SNIPPETS if snippet in combined.lower()
    ]
    prometheus_checks = _validate_prometheus(root / "prometheus.yml")
    alert_checks = _validate_alerts(root / "rune-agent-alerts.yml")
    dashboard_checks = _validate_dashboard(root / "grafana-dashboard.json")
    passed = (
        not missing_files
        and not forbidden_hits
        and prometheus_checks["passed"]
        and alert_checks["passed"]
        and dashboard_checks["passed"]
    )
    return {
        "schema_version": "v1",
        "passed": passed,
        "root": str(root),
        "missing_files": missing_files,
        "forbidden_hits": forbidden_hits,
        "prometheus": prometheus_checks,
        "alerts": alert_checks,
        "dashboard": dashboard_checks,
    }


def _validate_prometheus(path: Path) -> dict[str, Any]:
    text = _safe_read(path)
    required_snippets = (
        "metrics_path: /api/v1/metrics",
        "rune-agent-alerts.yml",
        "job_name: rune-agent-api",
        "127.0.0.1:8000",
    )
    missing = [snippet for snippet in required_snippets if snippet not in text]
    return {
        "passed": path.is_file() and not missing,
        "missing_snippets": missing,
    }


def _validate_alerts(path: Path) -> dict[str, Any]:
    text = _safe_read(path)
    required_metrics = (
        "rune_http_requests_total",
        "rune_llm_calls_total",
        "rune_scheduler_lease_skips_total",
        "rune_graph_nodes",
    )
    missing_metrics = [metric for metric in required_metrics if metric not in text]
    alert_count = text.count("- alert:")
    return {
        "passed": path.is_file() and not missing_metrics and alert_count >= 4,
        "alert_count": alert_count,
        "missing_metrics": missing_metrics,
    }


def _validate_dashboard(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "passed": False,
            "error": exc.__class__.__name__,
            "panel_count": 0,
            "missing_metrics": list(REQUIRED_METRICS),
        }

    panels = payload.get("panels")
    if not isinstance(panels, list):
        panels = []
    expressions = _dashboard_expressions(panels)
    missing_metrics = [metric for metric in REQUIRED_METRICS if metric not in expressions]
    return {
        "passed": (
            payload.get("uid") == "rune-agent-ops"
            and payload.get("title") == "RUNE Agent Operations"
            and payload.get("schemaVersion", 0) >= 39
            and len(panels) >= 6
            and not missing_metrics
        ),
        "panel_count": len(panels),
        "missing_metrics": missing_metrics,
    }


def _dashboard_expressions(panels: list[Any]) -> str:
    expressions: list[str] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        targets = panel.get("targets", [])
        if not isinstance(targets, list):
            continue
        for target in targets:
            if isinstance(target, dict) and isinstance(target.get("expr"), str):
                expressions.append(target["expr"])
    return "\n".join(expressions)


def _combined_text(root: Path) -> str:
    texts: list[str] = []
    for name in REQUIRED_FILES:
        texts.append(_safe_read(root / name))
    return "\n".join(texts)


def _safe_read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def main() -> int:
    """CLI entrypoint."""
    report = validate_observability_assets()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
