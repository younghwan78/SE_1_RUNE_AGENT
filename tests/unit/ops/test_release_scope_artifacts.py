"""Release-scope artifact verifier tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_release_scope_artifact_report_is_valid_but_not_release_ready() -> None:
    module = _load_module()

    report = module.build_release_scope_report()

    assert report["schema_version"] == "v1"
    assert report["passed"] is True
    assert report["release_ready"] is False
    assert report["summary"]["missing_artifacts"] == 0
    statuses = {item["status"] for item in report["items"]}
    assert "company_evidence_required" in statuses
    assert "decision_pending" not in statuses


def test_graph_ui_release_scope_is_resolved_locally() -> None:
    module = _load_module()

    report = module.build_release_scope_report()
    graph_item = next(
        item for item in report["items"] if item["item_id"] == "production_graph_ui"
    )

    assert graph_item["status"] == "local_complete"
    assert "src/req_tracker/ui/graph_workbench.js" in graph_item["evidence_paths"]
    assert "ops/ui/smoke_operator_ui.py" in graph_item["verification_commands"][0]


def test_release_scope_requirements_match_production_plan() -> None:
    module = _load_module()

    plan_requirements = module.load_first_release_requirements_from_plan()
    verifier_requirements = [item.requirement for item in module.RELEASE_SCOPE_ITEMS]

    assert verifier_requirements == plan_requirements


def test_release_scope_artifact_report_flags_missing_paths() -> None:
    module = _load_module()

    item = module.ReleaseScopeItem(
        item_id="missing_test",
        requirement="missing test artifact",
        status="local_complete",
        evidence_paths=("does/not/exist.py",),
        verification_commands=("uv run pytest tests/unit/ops/test_release_scope_artifacts.py",),
        notes="test fixture",
    )

    report = module.build_release_scope_report(items=(item,))

    assert report["passed"] is False
    assert report["release_ready"] is False
    assert report["summary"]["missing_artifacts"] == 1
    assert report["items"][0]["missing_paths"] == ["does/not/exist.py"]


def test_release_scope_artifact_report_rejects_empty_guidance() -> None:
    module = _load_module()

    item = module.ReleaseScopeItem(
        item_id="empty_guidance",
        requirement="empty guidance test",
        status="local_complete",
        evidence_paths=("PRODUCTION_EXECUTION_PLAN.md",),
        verification_commands=(),
        notes="",
    )

    report = module.build_release_scope_report(items=(item,))

    assert report["passed"] is False
    assert "empty_guidance:missing_verification_command" in report["failures"]
    assert "empty_guidance:missing_notes" in report["failures"]


def _load_module() -> ModuleType:
    module_path = Path("ops/rehearsal/validate_release_scope_artifacts.py")
    spec = importlib.util.spec_from_file_location("validate_release_scope_artifacts", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
