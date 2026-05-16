"""File-export source adapters for skill-managed production sources."""

import json
from pathlib import Path
from typing import Any, Literal

from req_tracker.adapters.base import RawSourceArtifact, SourceFetchResult, SourceScope, SyncCursor
from req_tracker.debug.hash import stable_hash
from req_tracker.ingestion.masking import mask_text
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
        self.source_type: SourceType = source_type
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
        return _page_fetch_result(
            artifacts=artifacts,
            cursor=cursor,
            limit=scope.limit,
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


def _page_fetch_result(
    *,
    artifacts: list[RawSourceArtifact],
    cursor: SyncCursor | None,
    limit: int,
    source_warnings: list[str],
    partial_failure: bool,
) -> SourceFetchResult:
    offset = cursor.offset if cursor else 0
    page = artifacts[offset : offset + limit]
    next_offset = offset + len(page)
    next_cursor = None
    if next_offset < len(artifacts):
        next_cursor = SyncCursor(offset=next_offset, content_hash=stable_hash(page))
    return SourceFetchResult(
        artifacts=page,
        next_cursor=next_cursor,
        source_warnings=source_warnings,
        partial_failure=partial_failure,
    )


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

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch only approved decision-source artifacts from restricted email exports."""
        artifacts: list[RawSourceArtifact] = []
        warnings: list[str] = [] if self.export_path.exists() else ["export_file_missing"]
        for artifact in self._load():
            if artifact.project_key != scope.project_key:
                continue
            if _is_allowed_decision_artifact(artifact):
                artifacts.append(_mask_email_decision_metadata(artifact))
                continue
            warnings.append(f"decision_email_artifact_skipped:{artifact.external_id}")
        return _page_fetch_result(
            artifacts=artifacts,
            cursor=cursor,
            limit=scope.limit,
            source_warnings=warnings,
            partial_failure=bool(warnings),
        )


def _is_allowed_decision_artifact(artifact: RawSourceArtifact) -> bool:
    if artifact.source_type == "decision_archive":
        return _artifact_is_decision(artifact)
    if artifact.source_type != "email":
        return False
    return bool(artifact.metadata.get("decision_source_approved")) and _artifact_is_decision(
        artifact
    )


def _artifact_is_decision(artifact: RawSourceArtifact) -> bool:
    labels = {label.lower() for label in artifact.labels}
    mbse_type = str(artifact.metadata.get("mbse_type", "")).lower()
    return mbse_type == "decision" or bool(labels & {"decision", "decision_archive"})


def _mask_email_decision_metadata(artifact: RawSourceArtifact) -> RawSourceArtifact:
    if artifact.source_type != "email":
        return artifact
    masked_metadata, redaction_count = _mask_metadata_value(artifact.metadata)
    if not isinstance(masked_metadata, dict):
        masked_metadata = {}
    masked_metadata["thread_metadata_masked"] = redaction_count > 0
    masked_metadata["thread_metadata_redaction_count"] = redaction_count
    return artifact.model_copy(update={"metadata": masked_metadata})


def _mask_metadata_value(value: Any) -> tuple[Any, int]:
    if isinstance(value, str):
        masked = mask_text(value)
        return masked.text, masked.redaction_count
    if isinstance(value, list):
        masked_items: list[Any] = []
        total = 0
        for item in value:
            masked_item, count = _mask_metadata_value(item)
            masked_items.append(masked_item)
            total += count
        return masked_items, total
    if isinstance(value, dict):
        masked_dict: dict[str, Any] = {}
        total = 0
        for key, item in value.items():
            masked_item, count = _mask_metadata_value(item)
            masked_dict[str(key)] = masked_item
            total += count
        return masked_dict, total
    return value, 0


def _infer_format(path: Path) -> ExportFormat:
    return "jsonl" if path.suffix.lower() == ".jsonl" else "json"
