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
    assert env["POSTGRES_MIGRATION_PROFILE"] == "core"
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


def test_full_stack_rehearsal_records_and_restores_feedback(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    rehearsal = _load_rehearsal_module()
    posted_payloads: list[dict[str, Any]] = []

    class FakeBackendRunner:
        COMPOSE_FILE = Path("ops/integration/docker-compose.integration.yml")

        @staticmethod
        def integration_env() -> dict[str, str]:
            return {
                "POSTGRES_TEST_DSN": "postgresql://rune:rune@127.0.0.1:16432/rune_agent_test",
                "NEO4J_TEST_URI": "bolt://127.0.0.1:17687",
                "NEO4J_TEST_USERNAME": "neo4j",
                "NEO4J_TEST_PASSWORD": "rune_integration_password",
                "NEO4J_TEST_DATABASE": "neo4j",
                "QDRANT_TEST_URL": "http://127.0.0.1:16333",
            }

        @staticmethod
        def compose(*_: Any) -> None:
            return None

        @staticmethod
        def wait_for_backends(*_: Any, **__: Any) -> None:
            return None

    def fake_post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
        posted_payloads.append({"url": url, "payload": payload})
        if url.endswith("/api/v1/runs/analyze"):
            return {"counts": {"approvals": 1}, "run": {"run_id": payload["run_id"]}}
        if "/api/v1/approvals/" in url:
            return {"status": "approved"}
        if url.endswith("/api/v1/feedback"):
            return payload
        raise AssertionError(f"unexpected POST {url}")

    def fake_get_json(url: str) -> dict[str, Any] | list[Any]:
        if url.endswith("/api/v1/ready"):
            return {"status": "ok"}
        if url.endswith("/api/v1/approvals"):
            return [{"approval_id": "apv_feedback_1"}]
        if "/api/v1/graph/projection" in url:
            return {"counts": {"visible_approved_edges": 1}}
        if url.endswith("/api/v1/audit/retention"):
            return {"total_events": 3}
        if url.endswith("/api/v1/metrics/summary"):
            return {
                "schema_version": "v1",
                "http": {"total_requests": 4},
                "runtime": {
                    "runs": {"total": 1},
                    "llm_calls": {"total": 1},
                    "graph": {"nodes": 3},
                    "scheduler": {"runs_started": 0},
                },
            }
        if url.endswith("/api/v1/debug/runs"):
            return [{"run_id": "run_full_stack_rehearsal"}]
        if "/api/v1/audit/events" in url:
            return [{"audit_id": "aud1"}, {"audit_id": "aud2"}]
        if url.endswith("/api/v1/feedback/summary"):
            return {"weak_evidence": 1}
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(rehearsal, "_load_backend_runner", lambda: FakeBackendRunner)
    monkeypatch.setattr(rehearsal, "start_api_server", lambda *_args: object())
    monkeypatch.setattr(rehearsal, "stop_api_server", lambda *_args: None)
    monkeypatch.setattr(
        rehearsal,
        "wait_for_health",
        lambda *_args, **_kwargs: {
            "state_store": "postgres",
            "graph_backend": "neo4j",
            "vector_backend": "qdrant",
        },
    )
    monkeypatch.setattr(rehearsal, "post_json", fake_post_json)
    monkeypatch.setattr(rehearsal, "get_json", fake_get_json)
    monkeypatch.setattr(
        rehearsal,
        "get_text",
        lambda *_args: "\n".join(
            [
                "rune_http_requests_total 4",
                "rune_agent_runs_total 1",
                "rune_llm_calls_total 1",
                "rune_graph_nodes 3",
            ]
        ),
    )
    monkeypatch.setattr(
        rehearsal,
        "run_load_smoke",
        lambda **_kwargs: {"passed": True, "runs": 1, "p95_ms": 1.0},
    )

    result = rehearsal.run_full_stack_rehearsal(
        api_port=18080,
        artifact_root=tmp_path / "artifacts",
        start_backends=False,
    )

    assert result["passed"] is True
    assert result["feedback_persistence"] == {
        "feedback_id": "fb_full_stack_rehearsal_answer",
        "passed": True,
        "reason_code": "weak_evidence",
        "restored_count": 1,
        "target_type": "answer",
    }
    assert any(
        item["url"].endswith("/api/v1/feedback")
        and item["payload"]["target_type"] == "answer"
        for item in posted_payloads
    )


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
