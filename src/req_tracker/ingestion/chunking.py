"""Artifact chunking."""

from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import ArtifactChunk, EvidenceSpan, SourceArtifact


def chunk_artifact(
    artifact: SourceArtifact,
    text: str,
    evidence: EvidenceSpan,
    *,
    max_chars: int = 700,
) -> list[ArtifactChunk]:
    """Chunk text into deterministic artifact chunks."""
    chunks: list[ArtifactChunk] = []
    for index, start in enumerate(range(0, len(text), max_chars)):
        chunk_text = text[start : start + max_chars].strip()
        if not chunk_text:
            continue
        chunk_evidence = evidence.model_copy(
            update={
                "extracted_text_preview": chunk_text[:500],
                "start_offset": start,
                "end_offset": start + len(chunk_text),
                "quote_hash": stable_hash(
                    {"artifact_id": artifact.artifact_id, "text": chunk_text}
                ),
            }
        )
        chunks.append(
            ArtifactChunk(
                chunk_id=f"chk_{artifact.artifact_id}_{index}",
                artifact_id=artifact.artifact_id,
                project_key=artifact.project_key,
                text=chunk_text,
                index=index,
                evidence=chunk_evidence,
                content_hash=stable_hash(chunk_text),
            )
        )
    return chunks
