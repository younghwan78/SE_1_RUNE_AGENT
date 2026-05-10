"""Audit service tests."""

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
