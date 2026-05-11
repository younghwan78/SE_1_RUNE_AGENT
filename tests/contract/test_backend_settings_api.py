"""Backend setting contract tests."""

import json

import pytest
from fastapi.testclient import TestClient

from req_tracker.api.app import create_app
from req_tracker.config.settings import Settings


def test_create_app_rejects_unsupported_graph_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported GRAPH_BACKEND"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", graph_backend="other"))


def test_create_app_rejects_unsupported_datasource_mode(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported DATASOURCE_MODE"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", datasource_mode="other"))


def test_create_app_requires_jira_rest_settings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="JIRA_BASE_URL and JIRA_TOKEN"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", datasource_mode="jira_rest"))


def test_create_app_uses_skill_export_source_adapter(tmp_path) -> None:  # type: ignore[no-untyped-def]
    export_path = tmp_path / "jira_export.json"
    export_path.write_text(
        json.dumps(
            {
                "artifacts": [
                    {
                        "external_id": "CAM-REQ-900",
                        "source_type": "jira",
                        "source_url": "export://jira/CAM-REQ-900",
                        "project_key": "RUNE_CAM_ALPHA",
                        "title": "Exported latency requirement",
                        "body_text": "Camera shall preserve traceability from exported JIRA.",
                        "created_at": "2026-01-01T00:00:00Z",
                        "updated_at": "2026-01-02T00:00:00Z",
                        "labels": ["requirement"],
                        "links": [],
                        "access_scope": ["RUNE_CAM_ALPHA"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    app = create_app(
        Settings(
            artifact_root=tmp_path / "artifacts",
            datasource_mode="jira_export",
            source_export_path=export_path,
        )
    )

    with TestClient(app) as client:
        ingest = client.post(
            "/api/v1/runs/ingest",
            json={
                "project_key": "RUNE_CAM_ALPHA",
                "scenario": "RUNE_CAM_ALPHA",
                "run_id": "run_jira_export_ingest",
            },
        )
        cursors = client.get("/api/v1/debug/source-cursors?project_key=RUNE_CAM_ALPHA")

    assert ingest.status_code == 200
    assert ingest.json()["counts"]["artifacts"] == 1
    assert cursors.status_code == 200
    assert cursors.json()[0]["cursor_id"] == "src_cursor_jira_RUNE_CAM_ALPHA_RUNE_CAM_ALPHA"


def test_create_app_requires_neo4j_connection_settings(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="NEO4J_URI and NEO4J_PASSWORD"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", graph_backend="neo4j"))


def test_create_app_rejects_unsupported_vector_backend(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported VECTOR_BACKEND"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", vector_backend="other"))


def test_create_app_requires_qdrant_url(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="QDRANT_URL"):
        create_app(Settings(artifact_root=tmp_path / "artifacts", vector_backend="qdrant"))
