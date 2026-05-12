"""Skill/export source rehearsal tests."""

import importlib.util
from pathlib import Path
from types import ModuleType


def test_skill_export_rehearsal_runs_all_export_modes() -> None:
    module = _load_module()

    report = module.run_skill_export_rehearsal()

    assert report["passed"] is True
    assert {result["mode"] for result in report["results"]} == {
        "jira_export",
        "confluence_export",
        "decision_email_export",
    }
    assert {result["artifact_count"] for result in report["results"]} == {1}
    assert {
        result["cursor_id"] for result in report["results"]
    } == {
        "src_cursor_jira_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA",
        "src_cursor_confluence_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA",
        "src_cursor_decision_archive_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA",
    }


def _load_module() -> ModuleType:
    module_path = Path("ops/source/rehearse_skill_export_sources.py")
    spec = importlib.util.spec_from_file_location("rehearse_skill_export_sources", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
