"""Audit service tests."""

import json
from datetime import UTC, datetime

from req_tracker.audit.archive import LocalAuditArchiveStore
from req_tracker.audit.models import AuditRetentionPolicy
from req_tracker.audit.service import AuditService


def test_audit_service_records_and_filters_events() -> None:
    service = AuditService()
    service.record(
        action="approval_decided",
        actor_id="reviewer",
        actor_role="System Architect",
        project_key="RUNE_CAM_ALPHA",
        target_type="approval",
        target_id="apv_1",
        reason_code="wrong_relation",
    )
    service.record(
        action="feedback_recorded",
        actor_id="reviewer",
        project_key="OTHER",
        target_type="edge",
        target_id="edge_1",
    )

    filtered = service.list_events(project_key="RUNE_CAM_ALPHA")

    assert len(filtered) == 1
    assert filtered[0].action == "approval_decided"
    assert filtered[0].reason_code == "wrong_relation"


def test_audit_service_reports_retention_status() -> None:
    service = AuditService(AuditRetentionPolicy(retention_days=30, max_events=1))
    event = service.record(
        action="run_completed",
        actor_id="system",
        target_type="run",
        target_id="run_1",
    )
    service.events[event.audit_id] = event.model_copy(
        update={"created_at": datetime(2026, 1, 1, tzinfo=UTC)}
    )
    service.record(
        action="feedback_recorded",
        actor_id="reviewer",
        target_type="edge",
        target_id="edge_1",
    )

    report = service.retention_report(datetime(2026, 2, 15, tzinfo=UTC))

    assert report["policy"]["retention_days"] == 30
    assert report["total_events"] == 2
    assert report["expired_events"] == 1
    assert report["overflow_events"] == 0
    assert report["expired_audit_ids"] == [event.audit_id]
    assert report["overflow_audit_ids"] == []


def test_audit_service_archives_and_prunes_retention_candidates(tmp_path) -> None:  # type: ignore[no-untyped-def]
    service = AuditService(AuditRetentionPolicy(retention_days=30, max_events=1))
    expired = service.record(
        action="run_completed",
        actor_id="system",
        target_type="run",
        target_id="run_old",
    )
    current = service.record(
        action="run_completed",
        actor_id="system",
        target_type="run",
        target_id="run_current",
    )
    service.events[expired.audit_id] = expired.model_copy(
        update={"created_at": datetime(2026, 1, 1, tzinfo=UTC)}
    )

    result = service.archive_and_prune(
        archive_writer=LocalAuditArchiveStore(tmp_path),
        now=datetime(2026, 2, 15, tzinfo=UTC),
    )

    assert result["archived_events"] == 1
    assert result["pruned_events"] == 1
    assert result["remaining_events"] == 1
    assert expired.audit_id not in service.events
    assert current.audit_id in service.events
    archive_ref = result["archive_ref"]
    assert archive_ref is not None
    rows = [
        json.loads(line)
        for line in (tmp_path / archive_ref.split("/")[-1]).read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["event"]["audit_id"] == expired.audit_id
