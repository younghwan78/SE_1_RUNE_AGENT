"""File-export source adapters for skill-managed production sources."""

import json
from pathlib import Path
from typing import Literal

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult, SourceScope, SyncCursor
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import SourceType

ExportFormat = Literal["json", "jsonl"]


class ExportFileSourceAdapter:
    """Read source artifacts exported by Claude Code source skills.

    The app depends on this stable file contract instead of MCP tool names,
    REST endpoints, or vendor SDK details.
    """

    def __init__(
        self,
        *,
        source_type: SourceType,
        export_path: Path | str,
        export_format: ExportFormat | None = None,
    ) -> None:
        self.source_type = source_type
        self.export_path = Path(export_path)
        self.export_format = export_format or _infer_format(self.export_path)

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch a page of exported artifacts."""
        artifacts = [
            artifact
            for artifact in self._load()
            if artifact.project_key == scope.project_key
        ]
        offset = cursor.offset if cursor else 0
        page = artifacts[offset : offset + scope.limit]
        next_offset = offset + len(page)
        next_cursor = None
        if next_offset < len(artifacts):
            next_cursor = SyncCursor(offset=next_offset, content_hash=stable_hash(page))
        return SourceFetchResult(
            artifacts=page,
            next_cursor=next_cursor,
            source_warnings=[] if self.export_path.exists() else ["export_file_missing"],
            partial_failure=not self.export_path.exists(),
        )

    def _load(self) -> list[RawSourceArtifact]:
        if not self.export_path.exists():
            return []
        if self.export_format == "jsonl":
            return [
                RawSourceArtifact.model_validate(json.loads(line))
                for line in self.export_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        payload = json.loads(self.export_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("artifacts", [])
        if not isinstance(payload, list):
            raise ValueError("export payload must be a list or an object with artifacts")
        return [RawSourceArtifact.model_validate(item) for item in payload]


class JiraExportSourceAdapter(ExportFileSourceAdapter):
    """JIRA export adapter."""

    def __init__(self, export_path: Path | str) -> None:
        super().__init__(source_type="jira", export_path=export_path)


class ConfluenceExportSourceAdapter(ExportFileSourceAdapter):
    """Confluence export adapter."""

    def __init__(self, export_path: Path | str) -> None:
        super().__init__(source_type="confluence", export_path=export_path)


class DecisionEmailExportSourceAdapter(ExportFileSourceAdapter):
    """Restricted decision/email export adapter."""

    def __init__(self, export_path: Path | str) -> None:
        super().__init__(source_type="decision_archive", export_path=export_path)


def _infer_format(path: Path) -> ExportFormat:
    return "jsonl" if path.suffix.lower() == ".jsonl" else "json"
