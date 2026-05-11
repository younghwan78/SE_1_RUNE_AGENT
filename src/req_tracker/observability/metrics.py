"""In-process operational metrics for local and production-shaped deployments."""

from collections import Counter, defaultdict
from threading import Lock
from typing import Any


class InMemoryMetrics:
    """Collect low-cardinality HTTP metrics for Prometheus-style scraping."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_counts: Counter[tuple[str, str, int]] = Counter()
        self._request_duration_ms: defaultdict[tuple[str, str, int], float] = defaultdict(float)

    def observe_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """Record one completed HTTP request."""
        key = (method.upper(), path, status_code)
        with self._lock:
            self._request_counts[key] += 1
            self._request_duration_ms[key] += duration_ms

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe HTTP metrics snapshot."""
        with self._lock:
            routes = [
                {
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "count": count,
                    "duration_ms_total": round(self._request_duration_ms[key], 3),
                    "duration_ms_avg": round(self._request_duration_ms[key] / count, 3),
                }
                for key, count in self._request_counts.items()
                for method, path, status_code in [key]
            ]
        routes.sort(key=lambda item: (item["path"], item["method"], item["status_code"]))
        return {
            "total_requests": sum(item["count"] for item in routes),
            "routes": routes,
        }


def build_metrics_summary(runtime: Any, metrics: InMemoryMetrics) -> dict[str, Any]:
    """Build a JSON-safe runtime metrics summary from the current process state."""
    run_statuses = Counter(run.status for run in runtime.traces.runs.values())
    step_statuses = Counter(step.status for step in runtime.traces.steps.values())
    step_stages = Counter(step.stage_name for step in runtime.traces.steps.values())
    validation_statuses = Counter(
        call.validation_status for call in runtime.traces.llm_calls.values()
    )
    approval_statuses = Counter(item.status for item in runtime.approvals.items.values())
    finding_statuses = Counter(finding.approval_status for finding in runtime.findings.values())
    finding_severities = Counter(finding.severity for finding in runtime.findings.values())
    feedback_actions = Counter(event.action for event in runtime.approvals.feedback)
    feedback_reasons = Counter(
        event.reason_code or "none" for event in runtime.approvals.feedback
    )
    llm_latency_total = sum(call.latency_ms for call in runtime.traces.llm_calls.values())
    llm_call_count = len(runtime.traces.llm_calls)
    llm_input_tokens = sum(call.input_tokens or 0 for call in runtime.traces.llm_calls.values())
    llm_output_tokens = sum(call.output_tokens or 0 for call in runtime.traces.llm_calls.values())
    scheduler_status = runtime.scheduler.status().model_dump(mode="json")

    return {
        "schema_version": "v1",
        "http": metrics.snapshot(),
        "runtime": {
            "runs": {
                "total": len(runtime.traces.runs),
                "by_status": dict(sorted(run_statuses.items())),
                "analysis_results": len(runtime.analyses),
                "ingestion_results": len(runtime.ingestions),
                "replay_results": len(runtime.replays),
            },
            "steps": {
                "total": len(runtime.traces.steps),
                "by_status": dict(sorted(step_statuses.items())),
                "by_stage": dict(sorted(step_stages.items())),
            },
            "llm_calls": {
                "total": llm_call_count,
                "by_validation_status": dict(sorted(validation_statuses.items())),
                "latency_ms_total": llm_latency_total,
                "latency_ms_avg": round(llm_latency_total / llm_call_count, 3)
                if llm_call_count
                else 0,
                "input_tokens_total": llm_input_tokens,
                "output_tokens_total": llm_output_tokens,
                "retry_count_total": sum(
                    call.retry_count for call in runtime.traces.llm_calls.values()
                ),
            },
            "graph": {
                "nodes": len(runtime.graph.nodes),
                "approved_edges": len(runtime.graph.edges),
                "pending_deltas": len(runtime.approvals.deltas),
            },
            "approvals": {
                "total": len(runtime.approvals.items),
                "by_status": dict(sorted(approval_statuses.items())),
            },
            "findings": {
                "total": len(runtime.findings),
                "by_status": dict(sorted(finding_statuses.items())),
                "by_severity": dict(sorted(finding_severities.items())),
            },
            "feedback": {
                "total": len(runtime.approvals.feedback),
                "by_action": dict(sorted(feedback_actions.items())),
                "by_reason_code": dict(sorted(feedback_reasons.items())),
            },
            "audit": {
                "events": len(runtime.audit.events),
            },
            "idempotency": {
                "cached_results": len(runtime.idempotency_results),
            },
            "scheduler": scheduler_status,
        },
    }


def render_prometheus_metrics(summary: dict[str, Any]) -> str:
    """Render a compact Prometheus text exposition from a metrics summary."""
    lines = [
        "# HELP rune_http_requests_total Total HTTP requests observed by this process.",
        "# TYPE rune_http_requests_total counter",
    ]
    for route in summary["http"]["routes"]:
        labels = {
            "method": route["method"],
            "path": route["path"],
            "status_code": str(route["status_code"]),
        }
        lines.append(f"rune_http_requests_total{_labels(labels)} {route['count']}")
    lines.extend(
        [
            "# HELP rune_http_request_duration_ms_sum Total HTTP request duration in milliseconds.",
            "# TYPE rune_http_request_duration_ms_sum counter",
        ]
    )
    for route in summary["http"]["routes"]:
        labels = {
            "method": route["method"],
            "path": route["path"],
            "status_code": str(route["status_code"]),
        }
        lines.append(
            f"rune_http_request_duration_ms_sum{_labels(labels)} "
            f"{route['duration_ms_total']}"
        )

    runtime = summary["runtime"]
    _append_counter_by_label(
        lines,
        "rune_agent_runs_total",
        "Agent runs by status.",
        "status",
        runtime["runs"]["by_status"],
    )
    _append_counter_by_label(
        lines,
        "rune_agent_steps_total",
        "Agent steps by status.",
        "status",
        runtime["steps"]["by_status"],
    )
    _append_counter_by_label(
        lines,
        "rune_llm_calls_total",
        "LLM calls by structured-output validation status.",
        "validation_status",
        runtime["llm_calls"]["by_validation_status"],
    )
    _append_gauge(lines, "rune_llm_call_latency_ms_sum", runtime["llm_calls"]["latency_ms_total"])
    _append_gauge(lines, "rune_graph_nodes", runtime["graph"]["nodes"])
    _append_gauge(lines, "rune_graph_approved_edges", runtime["graph"]["approved_edges"])
    _append_counter_by_label(
        lines,
        "rune_approval_items_total",
        "Approval items by status.",
        "status",
        runtime["approvals"]["by_status"],
    )
    _append_counter_by_label(
        lines,
        "rune_findings_total",
        "Findings by review status.",
        "status",
        runtime["findings"]["by_status"],
    )
    _append_counter_by_label(
        lines,
        "rune_feedback_events_total",
        "Feedback events by action.",
        "action",
        runtime["feedback"]["by_action"],
    )
    _append_gauge(lines, "rune_audit_events", runtime["audit"]["events"])
    _append_gauge(lines, "rune_scheduler_runs_started_total", runtime["scheduler"]["runs_started"])
    _append_gauge(lines, "rune_scheduler_lease_skips_total", runtime["scheduler"]["lease_skips"])
    return "\n".join(lines) + "\n"


def _append_counter_by_label(
    lines: list[str],
    name: str,
    help_text: str,
    label_name: str,
    values: dict[str, int],
) -> None:
    lines.extend([f"# HELP {name} {help_text}", f"# TYPE {name} counter"])
    for label_value, value in values.items():
        lines.append(f"{name}{_labels({label_name: label_value})} {value}")


def _append_gauge(lines: list[str], name: str, value: int | float) -> None:
    lines.extend([f"# HELP {name} Runtime gauge.", f"# TYPE {name} gauge", f"{name} {value}"])


def _labels(labels: dict[str, str]) -> str:
    encoded = ",".join(f'{key}="{_escape_label(value)}"' for key, value in sorted(labels.items()))
    return f"{{{encoded}}}"


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
