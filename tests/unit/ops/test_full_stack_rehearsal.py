"""Full-stack rehearsal runner tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


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


def _load_rehearsal_module() -> ModuleType:
    module_path = Path("ops/rehearsal/run_full_stack_rehearsal.py")
    spec = importlib.util.spec_from_file_location("run_full_stack_rehearsal", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
