"""Run a local production-shaped full-stack rehearsal.

The rehearsal starts disposable PostgreSQL, Neo4j, and Qdrant services, launches
the FastAPI app against those backends, runs a dummy analysis, approves one
graph delta, and checks health, graph projection, metrics, and audit retention APIs.
"""

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from urllib import error, request

ROOT = Path(__file__).resolve().parents[2]
BACKEND_RUNNER = ROOT / "ops" / "integration" / "run_backend_integration.py"
LOAD_RUNNER = ROOT / "ops" / "load" / "smoke_load.py"


def rehearsal_env(*, artifact_root: Path, api_port: int) -> dict[str, str]:
    """Return environment variables for the full-stack rehearsal app."""
    backend_runner = _load_backend_runner()
    env = backend_runner.integration_env()
    if not isinstance(env, dict):
        raise RuntimeError("backend integration env must be a dictionary")
    env.update(
        {
            "REQ_TRACKER_ENV": "rehearsal",
            "DATASOURCE_MODE": "dummy",
            "STATE_STORE": "postgres",
            "POSTGRES_DSN": env["POSTGRES_TEST_DSN"],
            "POSTGRES_MIGRATION_PROFILE": "core",
            "GRAPH_BACKEND": "neo4j",
            "NEO4J_URI": env["NEO4J_TEST_URI"],
            "NEO4J_USERNAME": env["NEO4J_TEST_USERNAME"],
            "NEO4J_PASSWORD": env["NEO4J_TEST_PASSWORD"],
            "NEO4J_DATABASE": env["NEO4J_TEST_DATABASE"],
            "VECTOR_BACKEND": "qdrant",
            "QDRANT_URL": env["QDRANT_TEST_URL"],
            "QDRANT_COLLECTION": "rune_rehearsal_chunks",
            "QDRANT_VECTOR_SIZE": "64",
            "MODEL_GATEWAY_MODE": "dummy",
            "AUTH_MODE": "local",
            "ARTIFACT_STORE": "local",
            "ARTIFACT_ROOT": str(artifact_root),
            "ENABLE_DOCS": "false",
            "SCHEDULER_ENABLED": "false",
            "RUNE_REHEARSAL_API_PORT": str(api_port),
        }
    )
    return cast(dict[str, str], env)


def main() -> int:
    """Run the full-stack rehearsal."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-port", type=int, default=18080)
    parser.add_argument("--no-up", action="store_true", help="Use already running backend services")
    parser.add_argument("--keep", action="store_true", help="Leave backend services running")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--load-runs", type=int, default=3)
    parser.add_argument("--max-load-p95-ms", type=float, default=5000.0)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        result = run_full_stack_rehearsal(
            api_port=args.api_port,
            artifact_root=Path(temp_dir) / "artifacts",
            start_backends=not args.no_up,
            keep_backends=args.keep,
            timeout_seconds=args.timeout_seconds,
            load_runs=args.load_runs,
            max_load_p95_ms=args.max_load_p95_ms,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


def run_full_stack_rehearsal(
    *,
    api_port: int = 18080,
    artifact_root: Path,
    start_backends: bool = True,
    keep_backends: bool = False,
    timeout_seconds: int = 180,
    load_runs: int = 3,
    max_load_p95_ms: float = 5000.0,
) -> dict[str, Any]:
    """Run the full-stack API rehearsal and return a structured summary."""
    backend_runner = _load_backend_runner()
    env = rehearsal_env(artifact_root=artifact_root, api_port=api_port)
    compose_file = Path(backend_runner.COMPOSE_FILE)
    api_base_url = f"http://127.0.0.1:{api_port}"
    server: subprocess.Popen[str] | None = None
    try:
        if start_backends:
            backend_runner.compose(compose_file, env, "up", "-d")
        backend_runner.wait_for_backends(env, timeout_seconds=timeout_seconds)
        server = start_api_server(env, api_port)
        health = wait_for_health(api_base_url, timeout_seconds=timeout_seconds)
        readiness = require_object(get_json(f"{api_base_url}/api/v1/ready"))
        analyze = post_json(
            f"{api_base_url}/api/v1/runs/analyze",
            {
                "run_id": "run_full_stack_rehearsal",
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_MULTI_SOURCE",
            },
        )
        approvals = require_array(get_json(f"{api_base_url}/api/v1/approvals"))
        if not approvals:
            raise RuntimeError("analysis produced no approval items")
        approval_id = str(approvals[0]["approval_id"])
        decision = post_json(
            f"{api_base_url}/api/v1/approvals/{approval_id}/decision",
            {
                "approval_id": approval_id,
                "action": "approve",
                "decided_by": "rehearsal_operator",
            },
        )
        recorded_feedback = post_json(
            f"{api_base_url}/api/v1/feedback",
            {
                "feedback_id": "fb_full_stack_rehearsal_answer",
                "target_type": "answer",
                "target_id": analyze["run"]["run_id"],
                "action": "commented",
                "user_id": "rehearsal_operator",
                "user_role": "System Architect",
                "reason_code": "weak_evidence",
                "correction_text": "Full-stack rehearsal feedback persistence check.",
            },
        )
        projection = require_object(
            get_json(f"{api_base_url}/api/v1/graph/projection?project_key=RUNE_CAM_ALPHA")
        )
        audit_retention = require_object(get_json(f"{api_base_url}/api/v1/audit/retention"))
        metrics_summary = require_object(get_json(f"{api_base_url}/api/v1/metrics/summary"))
        prometheus_metrics = get_text(f"{api_base_url}/api/v1/metrics")
        metrics_ok = metrics_surface_passed(metrics_summary, prometheus_metrics)
        stop_api_server(server)
        server = start_api_server(env, api_port)
        wait_for_health(api_base_url, timeout_seconds=timeout_seconds)
        restored_runs = require_array(get_json(f"{api_base_url}/api/v1/debug/runs"))
        restored_projection = require_object(
            get_json(f"{api_base_url}/api/v1/graph/projection?project_key=RUNE_CAM_ALPHA")
        )
        restored_audit = require_array(
            get_json(f"{api_base_url}/api/v1/audit/events?project_key=RUNE_CAM_ALPHA")
        )
        restored_feedback_summary = require_object(
            get_json(f"{api_base_url}/api/v1/feedback/summary")
        )
        feedback_persistence = feedback_persistence_summary(
            recorded_feedback,
            restored_feedback_summary,
        )
        load_smoke = run_load_smoke(
            api_base_url=api_base_url,
            runs=load_runs,
            max_p95_ms=max_load_p95_ms,
        )
        restart_restored = (
            any(
                isinstance(run, dict) and run.get("run_id") == "run_full_stack_rehearsal"
                for run in restored_runs
            )
            and restored_projection["counts"]["visible_approved_edges"] >= 1
            and len(restored_audit) >= 2
        )
        passed = (
            health.get("state_store") == "postgres"
            and readiness.get("status") == "ok"
            and health.get("graph_backend") == "neo4j"
            and health.get("vector_backend") == "qdrant"
            and analyze["counts"]["approvals"] > 0
            and decision["status"] == "approved"
            and projection["counts"]["visible_approved_edges"] >= 1
            and audit_retention["total_events"] >= 2
            and metrics_ok
            and restart_restored
            and feedback_persistence["passed"]
            and load_smoke["passed"]
        )
        return {
            "passed": passed,
            "api_base_url": api_base_url,
            "health": health,
            "readiness": readiness,
            "run_id": analyze["run"]["run_id"],
            "approval_id": approval_id,
            "approved_status": decision["status"],
            "graph_counts": projection["counts"],
            "audit_total_events": audit_retention["total_events"],
            "metrics": {
                "passed": metrics_ok,
                "http_total_requests": metrics_summary["http"]["total_requests"],
                "graph_nodes": metrics_summary["runtime"]["graph"]["nodes"],
                "llm_calls": metrics_summary["runtime"]["llm_calls"]["total"],
                "scheduler_runs_started": metrics_summary["runtime"]["scheduler"][
                    "runs_started"
                ],
            },
            "restart_restored": restart_restored,
            "feedback_persistence": feedback_persistence,
            "load_smoke": load_smoke,
            "schema_version": "v1",
        }
    finally:
        if server is not None:
            stop_api_server(server)
        if start_backends and not keep_backends:
            backend_runner.compose(compose_file, env, "down", "-v")


def start_api_server(env: dict[str, str], api_port: int) -> subprocess.Popen[str]:
    """Start uvicorn for the rehearsal API."""
    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "req_tracker.api.app:create_app",
            "--factory",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def stop_api_server(server: subprocess.Popen[str]) -> None:
    """Stop the rehearsal API process."""
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=10)


def run_load_smoke(*, api_base_url: str, runs: int, max_p95_ms: float) -> dict[str, Any]:
    """Run a small smoke-load pass against the live rehearsal API."""
    smoke_load = _load_smoke_runner()
    results = smoke_load.run_smoke_load(
        base_url=api_base_url,
        runs=runs,
        project_key="RUNE_CAM_ALPHA",
        scenario="RUNE_MULTI_SOURCE",
    )
    latencies = [result.latency_ms for result in results]
    p95_ms = float(smoke_load.percentile(latencies, 95))
    approvals = sum(int(result.approvals) for result in results)
    return {
        "runs": len(results),
        "p95_ms": p95_ms,
        "max_ms": max(latencies) if latencies else 0.0,
        "approvals": approvals,
        "passed": p95_ms <= max_p95_ms and approvals > 0,
        "max_p95_ms": max_p95_ms,
    }


def feedback_persistence_summary(
    recorded_feedback: dict[str, Any],
    restored_summary: dict[str, Any],
) -> dict[str, Any]:
    """Summarize whether answer feedback survived API restart through the state store."""
    reason_code = str(recorded_feedback.get("reason_code") or "")
    restored_count = int(restored_summary.get(reason_code, 0) or 0)
    return {
        "feedback_id": str(recorded_feedback.get("feedback_id") or ""),
        "passed": restored_count >= 1,
        "reason_code": reason_code,
        "restored_count": restored_count,
        "target_type": str(recorded_feedback.get("target_type") or ""),
    }


def metrics_surface_passed(metrics_summary: dict[str, Any], prometheus_text: str) -> bool:
    """Return whether metrics endpoints expose the expected rehearsal counters."""
    return (
        metrics_summary.get("schema_version") == "v1"
        and metrics_summary.get("http", {}).get("total_requests", 0) > 0
        and metrics_summary.get("runtime", {}).get("runs", {}).get("total", 0) >= 1
        and metrics_summary.get("runtime", {}).get("llm_calls", {}).get("total", 0) >= 1
        and metrics_summary.get("runtime", {}).get("graph", {}).get("nodes", 0) >= 1
        and "rune_http_requests_total" in prometheus_text
        and "rune_agent_runs_total" in prometheus_text
        and "rune_llm_calls_total" in prometheus_text
        and "rune_graph_nodes" in prometheus_text
    )


def wait_for_health(base_url: str, *, timeout_seconds: int) -> dict[str, Any]:
    """Wait until the API health endpoint responds."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            payload = require_object(get_json(f"{base_url}/api/v1/health"))
            if payload.get("status") == "ok":
                return payload
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(1.0)
    message = f"api did not become healthy within {timeout_seconds}s"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise TimeoutError(message)


def get_json(url: str) -> dict[str, Any] | list[Any]:
    """GET JSON from the rehearsal API."""
    req = request.Request(url, headers={"accept": "application/json"}, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"GET failed with HTTP {exc.code}: {url}") from exc
    if not isinstance(loaded, dict | list):
        raise RuntimeError("response must be a JSON object or array")
    return loaded


def get_text(url: str) -> str:
    """GET text from the rehearsal API."""
    req = request.Request(url, headers={"accept": "text/plain"}, method="GET")
    try:
        with request.urlopen(req, timeout=30) as response:
            return response.read().decode("utf-8")
    except error.HTTPError as exc:
        raise RuntimeError(f"GET failed with HTTP {exc.code}: {url}") from exc


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON to the rehearsal API."""
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"accept": "application/json", "content-type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            loaded = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        raise RuntimeError(f"POST failed with HTTP {exc.code}: {url}") from exc
    if not isinstance(loaded, dict):
        raise RuntimeError("response must be a JSON object")
    return loaded


def require_object(payload: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Return payload if it is a JSON object."""
    if not isinstance(payload, dict):
        raise RuntimeError("response must be a JSON object")
    return payload


def require_array(payload: dict[str, Any] | list[Any]) -> list[Any]:
    """Return payload if it is a JSON array."""
    if not isinstance(payload, list):
        raise RuntimeError("response must be a JSON array")
    return payload


def _load_backend_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_backend_integration", BACKEND_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load backend runner: {BACKEND_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_smoke_runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("smoke_load", LOAD_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load smoke-load runner: {LOAD_RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
