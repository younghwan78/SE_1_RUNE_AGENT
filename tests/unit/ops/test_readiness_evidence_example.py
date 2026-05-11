"""Readiness evidence example safety validation tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_committed_readiness_evidence_example_is_not_passable() -> None:
    validator = _load_validator_module()

    report = validator.validate_example()

    assert report["passed"] is True
    assert report["check_count"] > 0
    assert report["failures"] == []


def test_validator_rejects_passed_fake_run_id_example(tmp_path) -> None:  # type: ignore[no-untyped-def]
    validator = _load_validator_module()
    path = tmp_path / "bad_evidence.json"
    path.write_text(
        """
        {
          "schema_version": "v1",
          "checks": [
            {
              "check_id": "company_postgres_rehearsal",
              "status": "passed",
              "summary": "TODO: placeholder",
              "evidence": ["staging-ci:postgres:run-12345"]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    report = validator.validate_example(path)

    assert report["passed"] is False
    assert "company_postgres_rehearsal:status_passed" in report["failures"]
    assert "company_postgres_rehearsal:fake_run_id" in report["failures"]


def _load_validator_module() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_evidence_example.py")
    spec = importlib.util.spec_from_file_location("validate_evidence_example", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
