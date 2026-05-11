"""Source adapter factory for runtime datasource modes."""

from req_tracker.adapters.base import SourceAdapter
from req_tracker.adapters.confluence_rest import ConfluenceRestSourceAdapter
from req_tracker.adapters.dummy.adapter import DummySourceAdapter
from req_tracker.adapters.export_file import (
    ConfluenceExportSourceAdapter,
    DecisionEmailExportSourceAdapter,
    JiraExportSourceAdapter,
)
from req_tracker.adapters.jira_rest import JiraRestSourceAdapter
from req_tracker.config.settings import Settings


def create_source_adapter(settings: Settings) -> SourceAdapter:
    """Create the configured source adapter without leaking transport details."""
    mode = settings.datasource_mode
    if mode == "dummy":
        return DummySourceAdapter()
    if mode == "jira_export":
        _require_source_export_path(settings, mode)
        return JiraExportSourceAdapter(settings.source_export_path)
    if mode == "confluence_export":
        _require_source_export_path(settings, mode)
        return ConfluenceExportSourceAdapter(settings.source_export_path)
    if mode == "decision_email_export":
        _require_source_export_path(settings, mode)
        return DecisionEmailExportSourceAdapter(settings.source_export_path)
    if mode == "jira_rest":
        if not settings.jira_base_url or not settings.jira_token:
            raise ValueError(
                "JIRA_BASE_URL and JIRA_TOKEN are required for DATASOURCE_MODE=jira_rest"
            )
        return JiraRestSourceAdapter(
            base_url=settings.jira_base_url,
            token=settings.jira_token,
            jql=settings.jira_jql or None,
        )
    if mode == "confluence_rest":
        if (
            not settings.confluence_base_url
            or not settings.confluence_token
            or not settings.confluence_space_key
        ):
            raise ValueError(
                "CONFLUENCE_BASE_URL, CONFLUENCE_TOKEN, and CONFLUENCE_SPACE_KEY "
                "are required for DATASOURCE_MODE=confluence_rest"
            )
        return ConfluenceRestSourceAdapter(
            base_url=settings.confluence_base_url,
            token=settings.confluence_token,
            space_key=settings.confluence_space_key,
            cql=settings.confluence_cql or None,
        )
    raise ValueError(f"unsupported DATASOURCE_MODE: {mode}")


def _require_source_export_path(settings: Settings, mode: str) -> None:
    if str(settings.source_export_path) == ".":
        raise ValueError(f"SOURCE_EXPORT_PATH is required for DATASOURCE_MODE={mode}")
