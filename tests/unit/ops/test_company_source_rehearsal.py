"""Company source rehearsal runner tests."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult


def test_company_source_rehearsal_reports_missing_config_without_secrets() -> None:
    module = _load_module()

    report = module.run_company_source_rehearsal({}, source="all")

    assert report["passed"] is False
    assert report["source_count"] == 2
    assert {result["status"] for result in report["results"]} == {"missing_config"}
    assert "TOKEN" in str(report)
    assert "secret" not in str(report).lower()


def test_company_source_rehearsal_uses_adapters_and_masks_config(monkeypatch: Any) -> None:
    module = _load_module()

    class FakeJiraAdapter:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["base_url"] == "https://jira.example.test"
            assert kwargs["token"] == "jira-secret"

        def fetch_incremental(self, scope: Any) -> SourceFetchResult:
            assert scope.project_key == "CAM"
            return SourceFetchResult(
                artifacts=[_artifact("CAM-REQ-001", "jira", "CAM")],
                next_cursor=None,
            )

    monkeypatch.setattr(module, "JiraRestSourceAdapter", FakeJiraAdapter)

    report = module.run_company_source_rehearsal(
        {
            "JIRA_BASE_URL": "https://jira.example.test",
            "JIRA_TOKEN": "jira-secret",
            "JIRA_PROJECT_KEY": "CAM",
            "JIRA_REHEARSAL_LIMIT": "1",
        },
        source="jira",
    )

    assert report["passed"] is True
    result = report["results"][0]
    assert result["config"]["base_url"] == "<set>"
    assert result["config"]["token"] == "<set>"
    assert "jira-secret" not in str(report)
    assert result["artifacts"][0]["shape_ok"] is True


def test_company_source_rehearsal_requires_confluence_space_key() -> None:
    module = _load_module()

    report = module.run_company_source_rehearsal(
        {
            "CONFLUENCE_BASE_URL": "https://confluence.example.test",
            "CONFLUENCE_TOKEN": "confluence-secret",
        },
        source="confluence",
    )

    assert report["passed"] is False
    result = report["results"][0]
    assert result["status"] == "missing_config"
    assert "CONFLUENCE_SPACE_KEY" in result["missing"]


def _artifact(external_id: str, source_type: str, project_key: str) -> RawSourceArtifact:
    return RawSourceArtifact(
        external_id=external_id,
        source_type=source_type,
        source_url=f"https://example.test/{external_id}",
        project_key=project_key,
        title="Requirement",
        body_text="Requirement body",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        access_scope=[project_key],
        data_classification="public_internal",
    )


def _load_module() -> ModuleType:
    module_path = Path("ops/source/rehearse_company_sources.py")
    spec = importlib.util.spec_from_file_location("rehearse_company_sources", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
