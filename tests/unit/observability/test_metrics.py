"""Observability metrics tests."""

from req_tracker.observability.metrics import InMemoryMetrics, render_prometheus_metrics


def test_in_memory_metrics_accumulates_request_counts_and_durations() -> None:
    metrics = InMemoryMetrics()

    metrics.observe_http_request(
        method="get",
        path="/api/v1/health",
        status_code=200,
        duration_ms=1.5,
    )
    metrics.observe_http_request(
        method="GET",
        path="/api/v1/health",
        status_code=200,
        duration_ms=2.5,
    )

    snapshot = metrics.snapshot()

    assert snapshot["total_requests"] == 2
    route = snapshot["routes"][0]
    assert route["method"] == "GET"
    assert route["path"] == "/api/v1/health"
    assert route["status_code"] == 200
    assert route["count"] == 2
    assert route["duration_ms_total"] == 4.0
    assert route["duration_ms_avg"] == 2.0


def test_prometheus_renderer_escapes_label_values() -> None:
    text = render_prometheus_metrics(
        {
            "http": {
                "routes": [
                    {
                        "method": "GET",
                        "path": '/api/v1/path"with\\quote',
                        "status_code": 200,
                        "count": 1,
                        "duration_ms_total": 3.0,
                    }
                ]
            },
            "runtime": {
                "runs": {"by_status": {"succeeded": 1}},
                "steps": {"by_status": {"succeeded": 2}},
                "llm_calls": {
                    "by_validation_status": {"passed": 1},
                    "latency_ms_total": 10,
                    "input_tokens_total": 12,
                    "output_tokens_total": 5,
                    "cost_usd_total": 0.0004,
                },
                "graph": {"nodes": 3, "approved_edges": 4},
                "approvals": {"by_status": {"pending": 5}},
                "findings": {"by_status": {"open": 6}},
                "feedback": {"by_action": {"approved": 7}},
                "audit": {"events": 8},
                "scheduler": {"runs_started": 9, "lease_skips": 10},
            },
        }
    )

    assert 'path="/api/v1/path\\"with\\\\quote"' in text
    assert "rune_scheduler_runs_started_total 9" in text
    assert "rune_llm_input_tokens_total 12" in text
    assert "rune_llm_output_tokens_total 5" in text
    assert "rune_llm_cost_usd_total 0.0004" in text
