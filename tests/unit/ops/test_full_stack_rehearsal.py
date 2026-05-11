"""Full-stack rehearsal runner tests."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


def test_rehearsal_env_configures_production_backends(tmp_path) -> None:  # type: ignore[no-untyped-def]
    rehearsal = _load_rehearsal_module()

    env = rehearsal.rehearsal_env(artifact_root=tmp_path / "artifacts", api_port=18080)

    assert env["STATE_STORE"] == "postgres"
    assert env["POSTGRES_DSN"].endswith("@127.0.0.1:16432/rune_agent_test")
    assert env["GRAPH_BACKEND"] == "neo4j"
    assert env["NEO4J_URI"] == "bolt://127.0.0.1:17687"
    assert env["VECTOR_BACKEND"] == "qdrant"
    assert env["QDRANT_URL"] == "http://127.0.0.1:16333"
    assert env["AUTH_MODE"] == "local"
    assert env["ARTIFACT_ROOT"] == str(tmp_path / "artifacts")


def test_load_smoke_summary_uses_smoke_runner(monkeypatch: Any) -> None:
    rehearsal = _load_rehearsal_module()

    class FakeResult:
        def __init__(self, latency_ms: float, approvals: int) -> None:
            self.latency_ms = latency_ms
            self.approvals = approvals

    class FakeSmokeLoad:
        @staticmethod
        def run_smoke_load(**_: Any) -> list[FakeResult]:
            return [FakeResult(10.0, 2), FakeResult(20.0, 3)]

        @staticmethod
        def percentile(values: list[float], percent: int) -> float:
            assert percent == 95
            return max(values)

    monkeypatch.setattr(rehearsal, "_load_smoke_runner", lambda: FakeSmokeLoad)

    summary = rehearsal.run_load_smoke(
        api_base_url="http://127.0.0.1:18080",
        runs=2,
        max_p95_ms=50.0,
    )

    assert summary["runs"] == 2
    assert summary["p95_ms"] == 20.0
    assert summary["approvals"] == 5
    assert summary["passed"] is True


def test_metrics_surface_requires_json_and_prometheus_counters() -> None:
    rehearsal = _load_rehearsal_module()

    metrics_summary = {
        "schema_version": "v1",
        "http": {"total_requests": 4},
        "runtime": {
            "runs": {"total": 1},
            "llm_calls": {"total": 1},
            "graph": {"nodes": 3},
        },
    }
    prometheus_text = "\n".join(
        [
            "rune_http_requests_total 4",
            "rune_agent_runs_total 1",
            "rune_llm_calls_total 1",
            "rune_graph_nodes 3",
        ]
    )

    assert rehearsal.metrics_surface_passed(metrics_summary, prometheus_text) is True
    assert rehearsal.metrics_surface_passed(metrics_summary, "rune_http_requests_total 4") is False


def _load_rehearsal_module() -> ModuleType:
    module_path = Path("ops/rehearsal/run_full_stack_rehearsal.py")
    spec = importlib.util.spec_from_file_location("run_full_stack_rehearsal", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
