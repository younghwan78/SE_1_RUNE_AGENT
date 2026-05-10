"""Masking and chunking tests."""

from req_tracker.adapters.dummy.fixtures import fixture_by_name
from req_tracker.evidence.spans import build_artifact_evidence
from req_tracker.ingestion.chunking import chunk_artifact
from req_tracker.ingestion.masking import mask_text
from req_tracker.ingestion.normalization import normalize_raw_artifact


def test_masking_redacts_email_and_serial() -> None:
    raw = fixture_by_name("RUNE_SECURITY")[0]
    result = mask_text(raw.body_text)
    assert "owner@example.com" not in result.text
    assert "SN-IMX789-SECRET" not in result.text
    assert result.redaction_count == 2


def test_chunking_preserves_evidence() -> None:
    raw = fixture_by_name("RUNE_CAM_ALPHA")[0]
    artifact = normalize_raw_artifact(raw)
    evidence = build_artifact_evidence(artifact.artifact_id, raw)
    chunks = chunk_artifact(artifact, raw.body_text, evidence, max_chars=40)
    assert len(chunks) >= 2
    assert chunks[0].evidence.artifact_id == artifact.artifact_id

