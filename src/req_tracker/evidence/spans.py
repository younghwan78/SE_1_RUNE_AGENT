"""Evidence span construction."""

from req_tracker.adapters.base import RawSourceArtifact
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import EvidenceSpan


def build_artifact_evidence(artifact_id: str, raw: RawSourceArtifact) -> EvidenceSpan:
    """Build a broad evidence span for a source artifact."""
    preview = raw.body_text[:500] or raw.title
    return EvidenceSpan(
        artifact_id=artifact_id,
        source_url=raw.source_url,
        quote_hash=stable_hash({"external_id": raw.external_id, "preview": preview}),
        extracted_text_preview=preview,
        start_offset=0,
        end_offset=len(preview),
    )

