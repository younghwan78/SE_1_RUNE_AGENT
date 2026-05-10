"""Dummy source adapter tests."""

from req_tracker.adapters.base import SourceScope, SyncCursor
from req_tracker.adapters.dummy.adapter import DummySourceAdapter


def test_dummy_adapter_fetches_incrementally() -> None:
    adapter = DummySourceAdapter()
    first = adapter.fetch_incremental(SourceScope(project_key="RUNE_CAM_ALPHA", limit=3))
    assert len(first.artifacts) == 3
    assert first.next_cursor is not None

    second = adapter.fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA", limit=3),
        SyncCursor(offset=first.next_cursor.offset),
    )
    assert len(second.artifacts) == 3
    assert first.artifacts[0].external_id != second.artifacts[0].external_id


def test_dummy_adapter_supports_multi_source_fixture() -> None:
    adapter = DummySourceAdapter()

    result = adapter.fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA", scenario="RUNE_MULTI_SOURCE", limit=100)
    )

    assert {artifact.source_type for artifact in result.artifacts} >= {
        "confluence",
        "email",
        "decision_archive",
        "dummy",
    }
    assert any(artifact.data_classification == "restricted" for artifact in result.artifacts)


def test_dummy_adapter_supports_scale_fixture() -> None:
    adapter = DummySourceAdapter()

    result = adapter.fetch_incremental(
        SourceScope(project_key="RUNE_CAM_ALPHA", scenario="RUNE_SCALE_150", limit=200)
    )

    assert len(result.artifacts) == 150
    assert any(not artifact.links for artifact in result.artifacts)
