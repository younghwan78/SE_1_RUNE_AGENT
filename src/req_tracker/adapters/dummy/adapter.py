"""Dummy source adapter."""

from req_tracker.adapters.base import SourceFetchResult, SourceScope, SyncCursor
from req_tracker.adapters.dummy.fixtures import fixture_by_name
from req_tracker.debug.hash import stable_hash
from req_tracker.ontology.models import SourceType


class DummySourceAdapter:
    """Production-shaped source adapter backed by deterministic fixtures."""

    source_type: SourceType = "dummy"

    def fetch_incremental(
        self,
        scope: SourceScope,
        cursor: SyncCursor | None = None,
    ) -> SourceFetchResult:
        """Fetch a page of dummy artifacts."""
        artifacts = fixture_by_name(scope.scenario)
        offset = cursor.offset if cursor else 0
        page = artifacts[offset : offset + scope.limit]
        next_offset = offset + len(page)
        next_cursor = None
        if next_offset < len(artifacts):
            next_cursor = SyncCursor(offset=next_offset, content_hash=stable_hash(page))
        return SourceFetchResult(artifacts=page, next_cursor=next_cursor)
