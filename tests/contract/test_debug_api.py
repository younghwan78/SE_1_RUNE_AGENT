"""Debug workbench API tests."""

from urllib.parse import quote

from fastapi.testclient import TestClient


def test_debug_run_summary_and_artifact_read(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_debug_1",
        },
    )
    assert response.status_code == 200

    runs = client.get("/api/v1/debug/runs")
    assert runs.status_code == 200
    assert any(run["run_id"] == "run_debug_1" for run in runs.json())

    cursors = client.get("/api/v1/debug/source-cursors?project_key=RUNE_CAM_ALPHA")
    assert cursors.status_code == 200
    assert cursors.json()[0]["cursor_id"] == "src_cursor_dummy_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA"
    assert cursors.json()[0]["run_id"] == "run_debug_1"
    assert cursors.json()[0]["completed_cursor"]["offset"] == 10

    summary = client.get("/api/v1/debug/runs/run_debug_1/summary")
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["run"]["run_id"] == "run_debug_1"
    assert payload["counts"]["steps"] >= 7
    assert payload["counts"]["artifact_refs"] >= 2
    assert payload["graph_deltas"]
    llm_step = next(
        step
        for step in payload["steps"]
        if step["stage_name"] == "llm_assisted_reasoning"
    )
    assert llm_step["retrieval_context_ref"] == "candidate_edges"
    assert llm_step["validation_status"] == "passed"
    assert llm_step["validation_result"]["status"] == "passed"

    llm_calls = client.get("/api/v1/runs/run_debug_1/llm-calls")
    assert llm_calls.status_code == 200
    llm_payload = llm_calls.json()
    assert len(llm_payload) == 1
    assert llm_payload[0]["model_profile_id"] == "dummy-local"
    assert llm_payload[0]["prompt_version_id"] == "pv_edge_linking_v1"
    assert llm_payload[0]["validation_status"] == "passed"

    artifacts = client.get("/api/v1/runs/run_debug_1/artifacts")
    assert artifacts.status_code == 200
    artifact_payload = artifacts.json()
    assert artifact_payload
    assert artifact_payload[0]["run_id"] == "run_debug_1"
    assert artifact_payload[0]["artifact_ref"]
    assert artifact_payload[0]["output_hash"]

    artifact_ref = payload["artifact_refs"][0]
    artifact = client.get(f"/api/v1/debug/artifact?artifact_ref={quote(artifact_ref)}")
    assert artifact.status_code == 200
    assert artifact.json()

    diff_view = client.get("/api/v1/debug/runs/run_debug_1/diff-view")
    assert diff_view.status_code == 200
    diff_payload = diff_view.json()
    assert diff_payload["run_id"] == "run_debug_1"
    assert diff_payload["counts"]["graph_delta_previews"] >= 1
    assert diff_payload["graph_delta_previews"][0]["left"]["label"] == "approved_graph_edges"
    assert diff_payload["graph_delta_previews"][0]["right"]["operations"]
    assert diff_payload["counts"]["llm_payload_pairs"] == 1
    assert diff_payload["llm_payload_pairs"][0]["parsed"]["payload"]["candidate_edge_count"] >= 1
    assert diff_payload["llm_payload_pairs"][0]["parsed"]["payload"][
        "counter_evidence_refs"
    ] == []


def test_debug_run_summary_requires_existing_run(client: TestClient) -> None:
    response = client.get("/api/v1/debug/runs/missing/summary")
    assert response.status_code == 404

    diff_view = client.get("/api/v1/debug/runs/missing/diff-view")
    assert diff_view.status_code == 404


def test_debug_artifact_read_blocks_paths_outside_store(client: TestClient, tmp_path) -> None:  # type: ignore[no-untyped-def]
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    response = client.get(f"/api/v1/debug/artifact?artifact_ref={quote(str(outside))}")

    assert response.status_code == 403
    audit = client.get("/api/v1/audit/events?action=debug_artifact_read")
    assert audit.json()[0]["outcome"] == "blocked"
    assert audit.json()[0]["reason_code"] == "artifact_ref_outside_store"


def test_debug_approval_lineage_links_run_step_delta_feedback_and_audit(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/runs/analyze",
        json={
            "project_key": "RUNE_CAM_ALPHA",
            "scenario": "RUNE_CAM_ALPHA",
            "run_id": "run_lineage_1",
        },
    )
    assert response.status_code == 200
    approval = client.get("/api/v1/approvals").json()[0]
    decision = client.post(
        f"/api/v1/approvals/{approval['approval_id']}/decision",
        json={
            "approval_id": approval["approval_id"],
            "action": "reject",
            "decided_by": "reviewer",
            "reason_code": "wrong_relation",
        },
    )
    assert decision.status_code == 200

    lineage = client.get(f"/api/v1/debug/approvals/{approval['approval_id']}/lineage")

    assert lineage.status_code == 200
    payload = lineage.json()
    assert payload["approval"]["approval_id"] == approval["approval_id"]
    assert payload["run"]["run_id"] == "run_lineage_1"
    assert payload["step"]["step_id"] == approval["created_from_step_id"]
    assert payload["step"]["validation_status"] == "passed"
    assert payload["step"]["validation_result"]["graph_delta_preview_created"] is True
    assert payload["graph_delta"]["delta_id"] == approval["graph_delta_ref"]
    assert payload["feedback"][0]["reason_code"] == "wrong_relation"
    assert payload["audit_events"][0]["action"] == "approval_decided"
    assert payload["counts"]["graph_delta_operations"] >= 1


def test_debug_approval_lineage_requires_existing_approval(client: TestClient) -> None:
    response = client.get("/api/v1/debug/approvals/missing/lineage")
    assert response.status_code == 404
