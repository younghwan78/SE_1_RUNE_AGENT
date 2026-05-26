"""Tests for the SoC real-source switch readiness rehearsal."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[3]


def test_soc_real_source_switch_rehearsal_dry_run_is_skip_safe() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "ops/rehearsal/run_soc_real_source_switch_rehearsal.py",
            "--dry-run",
            "--format",
            "json",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)

    assert payload["status"] == "skipped"
    assert payload["requires_live"] is True
    assert payload["checks"]["source_skills"]["status"] == "passed"
    assert payload["checks"]["adapter_boundaries"]["status"] == "passed"
    assert payload["checks"]["live_source_access"]["status"] == "skipped"
    assert payload["sources"]["jira"]["skill_status"] == "present"
    assert payload["sources"]["confluence"]["skill_status"] == "present"
    assert payload["sources"]["email"]["skill_status"] == "present"
    assert "secret" not in result.stdout.lower()


def test_soc_real_source_switch_rehearsal_reports_missing_live_config_without_secrets() -> None:
    module = _load_rehearsal()

    report = module.run_soc_real_source_switch_rehearsal(env={}, live=True)

    assert report["status"] == "failed"
    assert report["requires_live"] is True
    assert report["checks"]["live_source_access"]["status"] == "failed"
    assert "JIRA_BASE_URL" in report["sources"]["jira"]["missing"]
    assert "CONFLUENCE_SPACE_KEY" in report["sources"]["confluence"]["missing"]
    assert "DECISION_EMAIL_EXPORT_PATH" in report["sources"]["email"]["missing"]
    assert "secret" not in str(report).lower()


def test_soc_real_source_switch_rehearsal_accepts_complete_config_without_fetching() -> None:
    module = _load_rehearsal()

    report = module.run_soc_real_source_switch_rehearsal(
        env={
            "JIRA_BASE_URL": "https://jira.example.invalid",
            "JIRA_TOKEN": "jira-secret",
            "JIRA_PROJECT_KEY": "SOC-N-1",
            "CONFLUENCE_BASE_URL": "https://confluence.example.invalid",
            "CONFLUENCE_TOKEN": "confluence-secret",
            "CONFLUENCE_SPACE_KEY": "SOC",
            "DECISION_EMAIL_EXPORT_PATH": "E:/restricted/decision-email-export.jsonl",
            "POSTGRES_TEST_DSN": "postgresql://user:secret@example.invalid/soc",
        },
        live=True,
    )

    assert report["status"] == "passed"
    assert report["checks"]["live_source_access"]["status"] == "passed"
    assert report["checks"]["database_target"]["status"] == "passed"
    assert report["sources"]["jira"]["config"]["token"] == "<set>"
    assert report["sources"]["confluence"]["config"]["token"] == "<set>"
    assert "jira-secret" not in str(report)
    assert "confluence-secret" not in str(report)
    assert "postgresql://user:secret" not in str(report)


def _load_rehearsal() -> ModuleType:
    module_path = ROOT / "ops/rehearsal/run_soc_real_source_switch_rehearsal.py"
    spec = importlib.util.spec_from_file_location(
        "run_soc_real_source_switch_rehearsal",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
