"""Backend integration runner tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_integration_env_sets_disposable_backend_variables() -> None:
    runner = _load_runner()

    env = runner.integration_env()

    assert env["POSTGRES_TEST_DSN"].endswith("@127.0.0.1:16432/rune_agent_test")
    assert env["POSTGRES_MIGRATION_PROFILE"] == "core"
    assert env["NEO4J_TEST_URI"] == "bolt://127.0.0.1:17687"
    assert env["NEO4J_TEST_PASSWORD"] == "rune_integration_password"
    assert env["QDRANT_TEST_URL"] == "http://127.0.0.1:16333"


def test_wait_until_retries_until_success() -> None:
    runner = _load_runner()
    attempts = {"count": 0}

    def check() -> bool:
        attempts["count"] += 1
        return attempts["count"] == 2

    runner.wait_until("unit", check, timeout_seconds=1, interval_seconds=0.01)

    assert attempts["count"] == 2


def _load_runner() -> ModuleType:
    module_path = Path("ops/integration/run_backend_integration.py")
    spec = importlib.util.spec_from_file_location("run_backend_integration", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
