"""Run a local feedback, eval gate, review, and canary rehearsal."""

import argparse
import json
from typing import Any

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def run_feedback_eval_rehearsal() -> dict[str, Any]:
    """Exercise controlled self-improvement promotion with dummy feedback."""
    app = create_app(Settings(auth_mode="local"))
    with TestClient(app) as client:
        for index in range(2):
            response = client.post(
                "/api/v1/feedback",
                json={
                    "feedback_id": f"fb_eval_rehearsal_{index}",
                    "target_type": "edge",
                    "target_id": f"edge_eval_rehearsal_{index}",
                    "action": "rejected",
                    "user_id": "reviewer",
                    "user_role": "System Architect",
                    "reason_code": "wrong_relation",
                },
            )
            response.raise_for_status()
        gate = client.get("/api/v1/eval/gate")
        gate.raise_for_status()
        improvements = client.get("/api/v1/improvements/candidates")
        improvements.raise_for_status()
        candidate_id = improvements.json()[0]["candidate_id"]
        review_ready = client.post(f"/api/v1/improvements/{candidate_id}/activate")
        review_ready.raise_for_status()
        canary = client.post(
            f"/api/v1/improvements/{candidate_id}/activate",
            json={"reviewer_approved": True, "canary_passed": False},
        )
        canary.raise_for_status()
        active = client.post(
            f"/api/v1/improvements/{candidate_id}/activate",
            json={"reviewer_approved": True, "canary_passed": True},
        )
        active.raise_for_status()
        security_feedback = client.post(
            "/api/v1/feedback",
            json={
                "feedback_id": "fb_eval_rehearsal_security",
                "target_type": "edge",
                "target_id": "edge_eval_rehearsal_security",
                "action": "marked_low_quality",
                "user_id": "security_reviewer",
                "user_role": "Security",
                "reason_code": "security_concern",
            },
        )
        security_feedback.raise_for_status()
        security_gate = client.get("/api/v1/eval/gate")
        security_gate.raise_for_status()

    gate_payload = gate.json()
    active_payload = active.json()
    security_gate_payload = security_gate.json()
    passed = (
        gate_payload["status"] == "passed"
        and review_ready.json()["status"] == "review_ready"
        and canary.json()["status"] == "canary"
        and active_payload["status"] == "active"
        and security_gate_payload["status"] == "blocked"
    )
    return {
        "passed": passed,
        "candidate_id": candidate_id,
        "initial_gate_status": gate_payload["status"],
        "review_status": review_ready.json()["status"],
        "canary_status": canary.json()["status"],
        "active_status": active_payload["status"],
        "security_gate_status": security_gate_payload["status"],
        "security_blockers": security_gate_payload["blockers"],
        "schema_version": "v1",
    }


def main() -> int:
    """Run the feedback eval rehearsal."""
    argparse.ArgumentParser(description=__doc__).parse_args()
    result = run_feedback_eval_rehearsal()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
