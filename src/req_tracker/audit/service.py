"""Audit service."""

from datetime import UTC, datetime, timedelta
from typing import Any

from req_tracker.audit.models import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    AuditRetentionPolicy,
)
from req_tracker.debug.hash import stable_hash


class AuditService:
    """Append-only in-memory audit event registry."""

    def __init__(self, policy: AuditRetentionPolicy | None = None) -> None:
        self.events: dict[str, AuditEvent] = {}
        self.policy = policy or AuditRetentionPolicy()

    def record(
        self,
        *,
        action: AuditAction,
        actor_id: str,
        target_type: str,
        target_id: str,
        project_key: str | None = None,
        actor_role: str | None = None,
        outcome: AuditOutcome = "succeeded",
        reason_code: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> AuditEvent:
        """Record an audit event."""
        payload = {
            "action": action,
            "actor_id": actor_id,
            "target_type": target_type,
            "target_id": target_id,
            "project_key": project_key,
            "outcome": outcome,
            "reason_code": reason_code,
            "metadata": metadata or {},
            "sequence": len(self.events),
        }
        event = AuditEvent(
            audit_id=f"aud_{stable_hash(payload)[:16]}",
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            project_key=project_key,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            reason_code=reason_code,
            metadata=dict(metadata or {}),
        )
        self.events[event.audit_id] = event
        return event

    def list_events(
        self,
        *,
        project_key: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        """List audit events newest first."""
        events = list(self.events.values())
        if project_key is not None:
            events = [event for event in events if event.project_key == project_key]
        if action is not None:
            events = [event for event in events if event.action == action]
        return sorted(events, key=lambda event: event.created_at, reverse=True)[:limit]

    def retention_report(self, now: datetime | None = None) -> dict[str, Any]:
        """Return non-destructive retention status for operator review."""
        reference_time = now or datetime.now(UTC)
        cutoff, expired, overflow = self._retention_candidates(reference_time)
        return {
            "policy": self.policy.model_dump(mode="json"),
            "cutoff_at": cutoff.isoformat(),
            "total_events": len(self.events),
            "expired_events": len(expired),
            "overflow_events": len(overflow),
            "expired_audit_ids": [
                event.audit_id
                for event in sorted(expired, key=lambda event: event.created_at)
            ],
            "overflow_audit_ids": [
                event.audit_id
                for event in sorted(overflow, key=lambda event: event.created_at)
            ],
            "schema_version": "v1",
        }

    def archive_and_prune(
        self,
        *,
        archive_writer: Any,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """Archive and remove events selected by the retention policy."""
        reference_time = now or datetime.now(UTC)
        _cutoff, expired, overflow = self._retention_candidates(reference_time)
        candidates_by_id = {
            event.audit_id: event
            for event in [*expired, *overflow]
        }
        events_to_archive = sorted(candidates_by_id.values(), key=lambda event: event.created_at)
        archive_ref = archive_writer.write_archive(
            events=events_to_archive,
            policy=self.policy,
        )
        for event in events_to_archive:
            self.events.pop(event.audit_id, None)
        return {
            "archive_ref": archive_ref,
            "archived_events": len(events_to_archive),
            "pruned_events": len(events_to_archive),
            "pruned_audit_ids": [event.audit_id for event in events_to_archive],
            "remaining_events": len(self.events),
            "schema_version": "v1",
        }

    def _retention_candidates(
        self,
        reference_time: datetime,
    ) -> tuple[datetime, list[AuditEvent], list[AuditEvent]]:
        cutoff = reference_time - timedelta(days=self.policy.retention_days)
        events = sorted(self.events.values(), key=lambda event: event.created_at)
        expired = [event for event in events if event.created_at < cutoff]
        remaining_after_expired = [
            event for event in events if event.audit_id not in {item.audit_id for item in expired}
        ]
        overflow_count = max(len(remaining_after_expired) - self.policy.max_events, 0)
        overflow = remaining_after_expired[:overflow_count]
        return cutoff, expired, overflow
