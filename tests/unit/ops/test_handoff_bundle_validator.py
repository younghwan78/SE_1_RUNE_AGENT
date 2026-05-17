"""Handoff bundle validator tests."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def test_handoff_bundle_validator_accepts_generated_bundle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is True
    assert report["summary"]["failed"] == 0
    assert report["artifact_count"] == 4


def test_handoff_bundle_validator_rejects_missing_artifact(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    (bundle_dir / "goal-completion-report.json").unlink()

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "missing_artifact:goal-completion-report.json" in report["failures"]


def test_handoff_bundle_validator_rejects_manifest_summary_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["readiness_summary"] = {"failed": 0, "manual_required": 0, "passed": 99}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "readiness_summary_mismatch" in report["failures"]


def test_handoff_bundle_validator_rejects_manifest_blocker_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["remaining_blocker_count"] = 0
    manifest["remaining_blockers"] = []
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert "remaining_blocker_count_mismatch" in report["failures"]
    assert "remaining_blockers_mismatch" in report["failures"]


def test_handoff_bundle_validator_rejects_missing_manual_template_gate(tmp_path) -> None:  # type: ignore[no-untyped-def]
    builder = _load_module("build_handoff_bundle", "ops/rehearsal/build_handoff_bundle.py")
    validator = _load_module(
        "validate_handoff_bundle",
        "ops/rehearsal/validate_handoff_bundle.py",
    )
    bundle_dir = tmp_path / "bundle"
    builder.build_handoff_bundle(bundle_dir, run_local_gates=False)
    template_path = bundle_dir / "manual-evidence-template.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template["checks"] = [
        check
        for check in template["checks"]
        if check["check_id"] != "company_jira_sandbox_rehearsal"
    ]
    template_path.write_text(json.dumps(template), encoding="utf-8")

    report = validator.validate_handoff_bundle(bundle_dir)

    assert report["passed"] is False
    assert (
        "manual_template_missing_gate:company_jira_sandbox_rehearsal"
        in report["failures"]
    )


def _load_module(module_name: str, path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
