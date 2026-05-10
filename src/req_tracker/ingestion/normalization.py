"""Normalize raw source artifacts."""

from datetime import datetime

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import SourceArtifact


def normalize_raw_artifact(raw: RawSourceArtifact) -> SourceArtifact:
    """Normalize a raw source artifact into the shared contract."""
    content_hash = stable_hash(
        {
            "external_id": raw.external_id,
            "title": raw.title,
            "body_text": raw.body_text,
            "updated_at": raw.updated_at,
        }
    )
    return SourceArtifact(
        artifact_id=f"src_{raw.source_type}_{stable_hash(raw.external_id)[:12]}",
        source_type=raw.source_type,
        source_url=raw.source_url,
        external_id=raw.external_id,
        project_key=raw.project_key,
        title=raw.title,
        body_text_ref=f"artifact://source/{raw.external_id}/body",
        author_id=raw.author_id,
        created_at=datetime.fromisoformat(raw.created_at),
        updated_at=datetime.fromisoformat(raw.updated_at),
        content_hash=content_hash,
        access_scope=raw.access_scope,
        data_classification=raw.data_classification,
    )

