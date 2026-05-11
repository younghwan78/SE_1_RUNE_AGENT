"""Audit archive storage."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from req_tracker.audit.models import AuditEvent, AuditRetentionPolicy
from req_tracker.debug.hash import stable_hash


@runtime_checkable
class AuditArchiveWriter(Protocol):
    """Archive writer contract used by retention jobs."""

    def write_archive(
        self,
        *,
        events: list[AuditEvent],
        policy: AuditRetentionPolicy,
    ) -> str | None:
        """Archive events and return an archive reference."""


class LocalAuditArchiveStore:
    """Write audit archive batches as JSONL files under a configured root."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write_archive(
        self,
        *,
        events: list[AuditEvent],
        policy: AuditRetentionPolicy,
    ) -> str | None:
        """Archive events and return an archive reference."""
        if not events:
            return None
        payload = {
            "policy": policy.model_dump(mode="json"),
            "event_ids": [event.audit_id for event in events],
            "created_at": datetime.now(UTC).isoformat(),
        }
        archive_id = stable_hash(payload)[:16]
        path = self.root / f"audit_archive_{archive_id}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(
                {
                    "archive": payload,
                    "event": event.model_dump(mode="json"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            for event in events
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(path.as_posix())


class PostgresAuditArchiveStore:
    """Write audit archive batches through PostgreSQLStateStore."""

    def __init__(self, state_store: object) -> None:
        self.state_store = state_store

    def write_archive(
        self,
        *,
        events: list[AuditEvent],
        policy: AuditRetentionPolicy,
    ) -> str | None:
        """Archive events and return a PostgreSQL archive reference."""
        writer = getattr(self.state_store, "write_audit_archive", None)
        if not callable(writer):
            raise TypeError("state_store must implement write_audit_archive")
        result = writer(events=events, policy=policy)
        if result is not None and not isinstance(result, str):
            raise TypeError("write_audit_archive must return a string reference or None")
        return result
