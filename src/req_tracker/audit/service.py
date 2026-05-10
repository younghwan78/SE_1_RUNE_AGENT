"""Audit service."""

from req_tracker.audit.models import AuditAction, AuditEvent, AuditOutcome
from req_tracker.debug.hash import stable_hash


class AuditService:
    """Append-only in-memory audit event registry."""

    def __init__(self) -> None:
        self.events: dict[str, AuditEvent] = {}

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
