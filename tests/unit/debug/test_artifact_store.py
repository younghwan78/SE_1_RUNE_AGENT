"""Local artifact store tests."""

import pytest

from req_tracker.debug.artifacts import ArtifactAccessError, LocalArtifactStore


def test_write_and_read_json_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path)
    payload = {"stage": "source_fetch", "items": [{"id": "CAM-REQ-001"}]}

    ref = store.write_json("run_001", "source_fetch", payload)
    loaded = store.read_json(ref.artifact_ref)

    assert loaded == payload
    assert ref.content_hash
    assert ref.artifact_ref.endswith("source_fetch.json")


def test_same_payload_hash_is_stable(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path)
    first = store.write_json("run_001", "a", {"b": 1, "a": 2})
    second = store.write_json("run_001", "b", {"a": 2, "b": 1})
    assert first.content_hash == second.content_hash


def test_read_json_blocks_paths_outside_store(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = LocalArtifactStore(tmp_path / "artifacts")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ArtifactAccessError):
        store.read_json(str(outside))
