"""PostgreSQL typed mirror validator tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_committed_postgres_typed_mirror_specs_match_migrations() -> None:
    validator = _load_validator_module()

    report = validator.validate_typed_mirrors()

    assert report["passed"] is True
    assert report["failure_count"] == 0
    assert "agent_runs" in report["checked_tables"]
    assert "idempotency_results" in report["checked_tables"]


def test_typed_mirror_validator_reports_missing_columns() -> None:
    validator = _load_validator_module()

    report = validator.validate_typed_mirrors(
        [
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                run_id TEXT PRIMARY KEY,
                project_key TEXT NOT NULL,
                payload_json JSONB NOT NULL
            );
            """
        ]
    )

    assert report["passed"] is False
    assert any(
        failure == "agent_runs:agent_runs:missing_column:run_type"
        for failure in report["failures"]
    )
    assert any(
        failure == "idempotency_results:idempotency_results:missing_table"
        for failure in report["failures"]
    )


def _load_validator_module() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_postgres_typed_mirrors.py")
    spec = importlib.util.spec_from_file_location("validate_postgres_typed_mirrors", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
