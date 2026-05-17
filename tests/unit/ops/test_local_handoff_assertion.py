"""Local handoff completion assertion tests."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType


def test_local_handoff_assertion_passes_when_no_local_blockers(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    _write_manifest(
        bundle_dir,
        {
            "goal_complete": False,
            "remaining_blocker_count": 20,
            "missing_env_count": 2,
            "missing_env": ["MODEL_GATEWAY_ENDPOINT_URL", "POSTGRES_DSN"],
            "blocker_summary": {
                "company_or_staging_evidence_required": 20,
                "local_action_required": 0,
                "by_status": {
                    "company_evidence_required": 4,
                    "failed": 6,
                    "manual_required": 10,
                },
                "local_action_blockers": [],
            },
        },
    )

    report = module.assert_local_handoff_complete(bundle_dir)

    assert report["passed"] is True
    assert report["remaining_blocker_count"] == 20
    assert report["missing_env_count"] == 2
    assert report["missing_env"] == ["MODEL_GATEWAY_ENDPOINT_URL", "POSTGRES_DSN"]
    assert report["blocker_summary"]["local_action_required"] == 0
    assert report["failures"] == []


def test_local_handoff_assertion_fails_when_local_blocker_remains(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    _write_manifest(
        bundle_dir,
        {
            "goal_complete": False,
            "remaining_blocker_count": 21,
            "blocker_summary": {
                "company_or_staging_evidence_required": 20,
                "local_action_required": 1,
                "by_status": {
                    "company_evidence_required": 4,
                    "failed": 6,
                    "manual_required": 11,
                },
                "local_action_blockers": ["production_readiness:local_regression_gates"],
            },
        },
    )

    report = module.assert_local_handoff_complete(bundle_dir)

    assert report["passed"] is False
    assert "local_action_required:1" in report["failures"]
    assert (
        "local_action_blockers_present:production_readiness:local_regression_gates"
        in report["failures"]
    )


def test_local_handoff_assertion_fails_on_summary_count_drift(tmp_path) -> None:  # type: ignore[no-untyped-def]
    module = _load_module()
    bundle_dir = tmp_path / "bundle"
    bundle_dir.mkdir()
    _write_manifest(
        bundle_dir,
        {
            "goal_complete": False,
            "remaining_blocker_count": 19,
            "blocker_summary": {
                "company_or_staging_evidence_required": 20,
                "local_action_required": 0,
                "by_status": {},
                "local_action_blockers": [],
            },
        },
    )

    report = module.assert_local_handoff_complete(bundle_dir)

    assert report["passed"] is False
    assert "remaining_blocker_count_mismatch" in report["failures"]


def _write_manifest(bundle_dir: Path, values: dict[str, object]) -> None:
    payload = {
        "schema_version": "v1",
        "goal_complete": values["goal_complete"],
        "remaining_blocker_count": values["remaining_blocker_count"],
        "missing_env_count": values.get("missing_env_count", 0),
        "missing_env": values.get("missing_env", []),
        "blocker_summary": values["blocker_summary"],
    }
    (bundle_dir / "manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_module() -> ModuleType:
    module_path = Path("ops/rehearsal/assert_local_handoff_complete.py")
    spec = importlib.util.spec_from_file_location(
        "assert_local_handoff_complete",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
