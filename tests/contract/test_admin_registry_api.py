"""Admin registry activation API contract tests."""

from fastapi.testclient import TestClient


def _activation_payload() -> dict[str, object]:
    return {
        "activated_by": "admin@example.com",
        "eval_passed": True,
        "reviewer_approved": True,
        "canary_passed": True,
        "reason_code": "local_baseline",
        "comment": "Local registry activation smoke.",
    }


def test_admin_can_record_model_profile_activation_idempotently(
    client: TestClient,
) -> None:
    payload = _activation_payload()
    first = client.post(
        "/api/v1/admin/model-profiles/dummy-local/activate",
        json=payload,
        headers={"Idempotency-Key": "idem-model-activation-1"},
    )
    second = client.post(
        "/api/v1/admin/model-profiles/dummy-local/activate",
        json=payload,
        headers={"Idempotency-Key": "idem-model-activation-1"},
    )
    conflict = client.post(
        "/api/v1/admin/model-profiles/dummy-local/activate",
        json={**payload, "comment": "Different request body."},
        headers={"Idempotency-Key": "idem-model-activation-1"},
    )

    assert first.status_code == 200
    assert first.json()["activation_id"] == "model_profile:dummy-local"
    assert first.json()["item"]["endpoint_alias"] == "local-fixture"
    assert second.status_code == 200
    assert second.json() == first.json()
    assert conflict.status_code == 409

    audit = client.get("/api/v1/audit/events?action=model_profile_activated")
    assert audit.status_code == 200
    assert len(audit.json()) == 1
    assert audit.json()[0]["actor_id"] == "admin@example.com"


def test_admin_can_record_prompt_version_activation_idempotently(
    client: TestClient,
) -> None:
    payload = _activation_payload()
    first = client.post(
        "/api/v1/admin/prompt-versions/pv_edge_linking_v1/activate",
        json=payload,
        headers={"Idempotency-Key": "idem-prompt-activation-1"},
    )
    second = client.post(
        "/api/v1/admin/prompt-versions/pv_edge_linking_v1/activate",
        json=payload,
        headers={"Idempotency-Key": "idem-prompt-activation-1"},
    )

    assert first.status_code == 200
    assert first.json()["activation_id"] == "prompt_version:pv_edge_linking_v1"
    assert first.json()["task_name"] == "edge_linking"
    assert second.status_code == 200
    assert second.json() == first.json()

    audit = client.get("/api/v1/audit/events?action=prompt_version_activated")
    assert audit.status_code == 200
    assert len(audit.json()) == 1


def test_admin_activation_requires_eval_review_and_canary_gates(
    client: TestClient,
) -> None:
    blocked = client.post(
        "/api/v1/admin/model-profiles/dummy-local/activate",
        json={"activated_by": "admin@example.com", "eval_passed": True},
    )
    missing = client.post(
        "/api/v1/admin/model-profiles/missing-profile/activate",
        json=_activation_payload(),
    )

    assert blocked.status_code == 409
    assert blocked.json()["detail"]["message"] == "activation gates are not satisfied"
    assert blocked.json()["detail"]["missing_gates"] == [
        "reviewer_approved",
        "canary_passed",
    ]
    assert missing.status_code == 404
