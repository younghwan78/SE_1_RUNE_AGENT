"""OpenAPI surface guard for production-plan endpoints."""

from fastapi.testclient import TestClient


def test_production_plan_endpoint_surface_is_registered(client: TestClient) -> None:
    """Keep the implemented API surface aligned with the production plan."""
    paths = set(client.app.openapi()["paths"])

    expected_paths = {
        "/api/v1/projects",
        "/api/v1/graph/nodes",
        "/api/v1/graph/edges",
        "/api/v1/graph/subgraph",
        "/api/v1/traceability/chain/{node_id}",
        "/api/v1/findings",
        "/api/v1/findings/{finding_id}",
        "/api/v1/approvals",
        "/api/v1/audit/events",
        "/api/v1/runs/ingest",
        "/api/v1/runs/analyze",
        "/api/v1/approvals/{approval_id}/decision",
        "/api/v1/findings/{finding_id}/status",
        "/api/v1/feedback",
        "/api/v1/admin/prompt-versions/{prompt_version_id}/activate",
        "/api/v1/admin/model-profiles/{model_profile_id}/activate",
    }

    assert expected_paths <= paths
