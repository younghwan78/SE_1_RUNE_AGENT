"""Run disposable PostgreSQL, Neo4j, and Qdrant integration tests.

This script starts the local Docker Compose integration stack, waits until each
backend accepts client calls, runs the env-gated integration tests, and tears the
stack down by default.
"""

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib import request

import psycopg
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = ROOT / "ops" / "integration" / "docker-compose.integration.yml"


def integration_env() -> dict[str, str]:
    """Return environment variables for local disposable backend tests."""
    env = os.environ.copy()
    postgres_port = env.get("RUNE_IT_POSTGRES_PORT", "16432")
    neo4j_bolt_port = env.get("RUNE_IT_NEO4J_BOLT_PORT", "17687")
    qdrant_http_port = env.get("RUNE_IT_QDRANT_HTTP_PORT", "16333")
    env.update(
        {
            "RUNE_IT_POSTGRES_PORT": postgres_port,
            "RUNE_IT_NEO4J_BOLT_PORT": neo4j_bolt_port,
            "RUNE_IT_QDRANT_HTTP_PORT": qdrant_http_port,
            "POSTGRES_TEST_DSN": (
                f"postgresql://rune:rune@127.0.0.1:{postgres_port}/rune_agent_test"
            ),
            "NEO4J_TEST_URI": f"bolt://127.0.0.1:{neo4j_bolt_port}",
            "NEO4J_TEST_USERNAME": "neo4j",
            "NEO4J_TEST_PASSWORD": "rune_integration_password",
            "NEO4J_TEST_DATABASE": "neo4j",
            "QDRANT_TEST_URL": f"http://127.0.0.1:{qdrant_http_port}",
            "QDRANT_TEST_COLLECTION": "rune_test_chunks",
        }
    )
    return env


def main() -> int:
    """Run backend integration tests against disposable local services."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-file", type=Path, default=COMPOSE_FILE)
    parser.add_argument("--no-up", action="store_true", help="Use already running services")
    parser.add_argument("--keep", action="store_true", help="Leave services running after tests")
    parser.add_argument("--timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    compose_file = args.compose_file.resolve()
    env = integration_env()
    try:
        if not args.no_up:
            compose(compose_file, env, "up", "-d")
        wait_for_backends(env, timeout_seconds=args.timeout_seconds)
        result = run_pytest(env)
        return result.returncode
    finally:
        if not args.keep and not args.no_up:
            compose(compose_file, env, "down", "-v")


def compose(compose_file: Path, env: dict[str, str], *args: str) -> None:
    """Run docker compose with the integration project name."""
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            "rune-agent-integration",
            "-f",
            str(compose_file),
            *args,
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )


def wait_for_backends(env: dict[str, str], *, timeout_seconds: int) -> None:
    """Wait until all disposable backends accept real client operations."""
    wait_until(
        "postgres",
        lambda: _check_postgres(env["POSTGRES_TEST_DSN"]),
        timeout_seconds=timeout_seconds,
    )
    wait_until(
        "neo4j",
        lambda: _check_neo4j(
            env["NEO4J_TEST_URI"],
            env["NEO4J_TEST_USERNAME"],
            env["NEO4J_TEST_PASSWORD"],
            env["NEO4J_TEST_DATABASE"],
        ),
        timeout_seconds=timeout_seconds,
    )
    wait_until(
        "qdrant",
        lambda: _check_qdrant(env["QDRANT_TEST_URL"]),
        timeout_seconds=timeout_seconds,
    )


def wait_until(
    name: str,
    check: Callable[[], bool],
    *,
    timeout_seconds: int,
    interval_seconds: float = 2.0,
) -> None:
    """Poll one readiness check until it succeeds or times out."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if check():
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(interval_seconds)
    message = f"{name} did not become ready within {timeout_seconds}s"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise TimeoutError(message)


def run_pytest(env: dict[str, str]) -> subprocess.CompletedProcess[Any]:
    """Run the env-gated production backend integration tests."""
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_postgres_state_store.py",
            "tests/integration/test_neo4j_graph_backend.py",
            "tests/integration/test_qdrant_vector_backend.py",
        ],
        cwd=ROOT,
        env=env,
        check=False,
    )


def _check_postgres(dsn: str) -> bool:
    with psycopg.connect(dsn, connect_timeout=5) as conn:
        row = conn.execute("SELECT 1").fetchone()
    return row is not None


def _check_neo4j(uri: str, username: str, password: str, database: str) -> bool:
    driver = GraphDatabase.driver(uri, auth=(username, password))
    try:
        with driver.session(database=database) as session:
            record = session.run("RETURN 1 AS ok").single()
        return record is not None and int(record["ok"]) == 1
    finally:
        driver.close()


def _check_qdrant(url: str) -> bool:
    with request.urlopen(f"{url}/healthz", timeout=5) as response:
        if response.status != 200:
            return False
    client = QdrantClient(url=url)
    client.get_collections()
    return True


if __name__ == "__main__":
    raise SystemExit(main())
