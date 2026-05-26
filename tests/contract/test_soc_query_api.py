"""Contract tests for SoC Knowledge query API."""

from urllib.parse import quote

from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def test_soc_query_api_returns_structured_answer_with_sources(client: TestClient) -> None:
    response = client.post(
        "/api/v1/soc/query",
        json={
            "query_id": "soc_query_api_001",
            "user_query": "Camera shot 성능 이슈는 무엇이 있었나?",
            "user_id": "architect_01",
            "session_id": "session_001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_id"] == "soc_query_api_001"
    assert payload["items"]
    assert payload["confidence"] in {"medium", "high"}
    assert payload["reasoning_log_ref"].endswith("soc_query_reasoning.json")
    assert all(item["sources"] for item in payload["items"])
    assert {item["level"] for item in payload["items"]} >= {"L3"}

    reasoning_log = client.get(
        f"/api/v1/debug/artifact?artifact_ref={quote(payload['reasoning_log_ref'])}"
    )

    assert reasoning_log.status_code == 200
    assert reasoning_log.json()["query"]["query_id"] == "soc_query_api_001"


def test_soc_query_api_accepts_explicit_slice_plan(client: TestClient) -> None:
    response = client.post(
        "/api/v1/soc/query",
        json={
            "query_id": "soc_query_api_002",
            "user_query": "SOC-N-2 thermal 관련 GPU 이슈는?",
            "user_id": "architect_01",
            "session_id": "session_001",
            "slice": {
                "pattern": "concern_slice",
                "project_keys": ["SOC-N-2"],
                "concerns": ["Thermal"],
                "components": ["GPU"],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert all("Thermal" in item["concern"] for item in payload["items"])
    assert all("GPU" in item["component"] for item in payload["items"])


def test_soc_query_api_graceful_unknown(client: TestClient) -> None:
    response = client.post(
        "/api/v1/soc/query",
        json={
            "query_id": "soc_query_api_003",
            "user_query": "Bluetooth 관련 이슈가 있었나?",
            "user_id": "architect_01",
            "session_id": "session_001",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["confidence"] == "low"
    assert "no_candidates" in payload["quality_signals"]


def test_soc_query_api_uses_configured_gateway_slice_planner(tmp_path) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            soc_query_planner_mode="model_gateway",
            soc_query_planner_model_profile_id="dummy-local",
        )
    )
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/soc/query",
            json={
                "query_id": "soc_query_api_gateway_planner",
                "user_query": "Camera shot 성능 이슈는 무엇이 있었나?",
                "user_id": "architect_01",
                "session_id": "session_001",
                "current_project": "SOC-N-1",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    traces = list(app.state.runtime.traces.llm_calls.values())
    assert len(traces) == 1
    assert traces[0].run_id == "soc_query_api_gateway_planner"
    assert traces[0].step_id.endswith("soc_slice_planning")
    assert traces[0].prompt_version_id == "pv_soc_slice_planning_v1"
    run = app.state.runtime.traces.runs["soc_query_api_gateway_planner"]
    assert run.run_type == "query"
    assert run.status == "succeeded"
    step_names = {
        step.stage_name
        for step in app.state.runtime.traces.list_steps("soc_query_api_gateway_planner")
    }
    assert "soc_rerank" in step_names


def test_soc_query_api_uses_configured_tool_planner_and_answer_assembler(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            soc_query_tool_planner_mode="model_gateway",
            soc_query_tool_planner_model_profile_id="dummy-local",
            soc_answer_assembler_mode="model_gateway",
            soc_answer_assembler_model_profile_id="dummy-local",
        )
    )
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/soc/query",
            json={
                "query_id": "soc_query_api_orchestrated",
                "user_query": "Camera shot 성능 이슈는 무엇이 있었나?",
                "user_id": "architect_01",
                "session_id": "session_001",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    trace_steps = {trace.step_id for trace in app.state.runtime.traces.llm_calls.values()}
    assert "soc_query_api_orchestrated_soc_query_tool_planning" in trace_steps
    assert "soc_answer_assembly" in trace_steps
