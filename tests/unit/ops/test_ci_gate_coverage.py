"""CI gate coverage validator tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_current_ci_gate_coverage_passes() -> None:
    validator = _load_validator_module()

    report = validator.validate_ci_gate_coverage()

    assert report["passed"] is True
    assert report["missing_required"] == []
    assert report["unexpected_omissions"] == []
    assert "uv run python ops/integration/run_backend_integration.py" in report[
        "allowed_omissions"
    ]


def test_ci_gate_coverage_reports_missing_required_command(tmp_path) -> None:  # type: ignore[no-untyped-def]
    validator = _load_validator_module()
    workflow_path = tmp_path / "ci.yml"
    workflow_path.write_text(
        """
        jobs:
          verify:
            steps:
              - run: uv run ruff check .
        """,
        encoding="utf-8",
    )

    report = validator.validate_ci_gate_coverage(
        workflow_path,
        local_gate_commands=[
            "uv run ruff check .",
            "uv run mypy src",
            "uv run python ops/integration/run_backend_integration.py",
        ],
    )

    assert report["passed"] is False
    assert "uv run mypy src" in report["missing_required"]
    assert "uv run python ops/integration/run_backend_integration.py" not in report[
        "missing_required"
    ]
    assert (
        "uv run python ops/rehearsal/check_production_readiness.py --write-evidence-template -"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/build_staging_evidence_plan.py --format markdown"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/build_staging_evidence_plan.py "
        "--env-file .env.example --format markdown"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/validate_release_scope_artifacts.py"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py --allow-incomplete"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--allow-incomplete --env-file .env.example"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/build_staging_evidence_plan.py "
        "--env-file ops/rehearsal/staging.env.example --format markdown"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/check_goal_completion.py "
        "--allow-incomplete --env-file ops/rehearsal/staging.env.example"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/build_handoff_bundle.py "
        "--allow-incomplete --env-file ops/rehearsal/staging.env.example "
        "--output-dir .local_artifacts/staging-handoff-bundle"
        in report["missing_required"]
    )
    assert (
        "uv run python ops/rehearsal/validate_handoff_bundle.py "
        ".local_artifacts/staging-handoff-bundle"
        in report["missing_required"]
    )


def _load_validator_module() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_ci_gate_coverage.py")
    spec = importlib.util.spec_from_file_location("validate_ci_gate_coverage", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
