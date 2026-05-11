"""Observability asset validation tests."""

from pathlib import Path
from runpy import run_path

OBS_ROOT = Path("ops/observability")


def test_observability_assets_are_packaged() -> None:
    required_paths = {
        "prometheus.yml",
        "rune-agent-alerts.yml",
        "grafana-dashboard.json",
        "validate_observability_assets.py",
    }

    missing = [path for path in required_paths if not (OBS_ROOT / path).exists()]

    assert missing == []


def test_observability_assets_reference_runtime_metrics() -> None:
    dashboard = (OBS_ROOT / "grafana-dashboard.json").read_text(encoding="utf-8")
    alerts = (OBS_ROOT / "rune-agent-alerts.yml").read_text(encoding="utf-8")
    prometheus = (OBS_ROOT / "prometheus.yml").read_text(encoding="utf-8")

    for metric in [
        "rune_http_requests_total",
        "rune_llm_calls_total",
        "rune_llm_input_tokens_total",
        "rune_llm_output_tokens_total",
        "rune_llm_cost_usd_total",
        "rune_graph_nodes",
        "rune_scheduler_lease_skips_total",
    ]:
        assert metric in dashboard or metric in alerts

    assert "metrics_path: /api/v1/metrics" in prometheus
    assert "rune-agent-alerts.yml" in prometheus
    assert "basic_auth:" not in prometheus
    assert "bearer_token" not in prometheus


def test_observability_asset_validator_passes() -> None:
    namespace = run_path("ops/observability/validate_observability_assets.py")

    result = namespace["validate_observability_assets"]()

    assert result["passed"] is True
    assert result["missing_files"] == []
    assert result["forbidden_hits"] == []
    assert result["prometheus"]["passed"] is True
    assert result["alerts"]["passed"] is True
    assert result["dashboard"]["passed"] is True
