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

