"""OpenAPI surface guard for production-plan endpoints."""

from fastapi.testclient import TestClient


def test_production_plan_endpoint_surface_is_registered(client: TestClient) -> None:
    """Keep the implemented API surface aligned with the production plan."""
    openapi_paths = client.app.openapi()["paths"]
    paths = set(openapi_paths)

    expected_route_methods = {
        ("GET", "/api/v1/projects"),
        ("GET", "/api/v1/graph/nodes"),
        ("GET", "/api/v1/graph/edges"),
        ("GET", "/api/v1/graph/subgraph"),
        ("GET", "/api/v1/traceability/chain/{node_id}"),
        ("GET", "/api/v1/findings"),
        ("GET", "/api/v1/findings/{finding_id}"),
        ("GET", "/api/v1/approvals"),
        ("GET", "/api/v1/audit/events"),
        ("GET", "/api/v1/runs"),
        ("GET", "/api/v1/runs/{run_id}"),
        ("GET", "/api/v1/runs/{run_id}/steps"),
        ("GET", "/api/v1/runs/{run_id}/llm-calls"),
        ("GET", "/api/v1/runs/{run_id}/artifacts"),
        ("GET", "/api/v1/runs/{run_id}/graph-delta"),
        ("GET", "/api/v1/replays/{replay_id}/diff"),
        ("GET", "/api/v1/debug/approvals/{approval_id}/lineage"),
        ("GET", "/api/v1/metrics"),
        ("GET", "/api/v1/metrics/summary"),
        ("POST", "/api/v1/runs/ingest"),
        ("POST", "/api/v1/runs/analyze"),
        ("POST", "/api/v1/runs/{run_id}/replay"),
        ("POST", "/api/v1/approvals/{approval_id}/decision"),
        ("POST", "/api/v1/findings/{finding_id}/status"),
        ("POST", "/api/v1/feedback"),
        ("POST", "/api/v1/improvements/{candidate_id}/rollback"),
        ("POST", "/api/v1/admin/prompt-versions/{prompt_version_id}/activate"),
        ("POST", "/api/v1/admin/prompt-versions/{prompt_version_id}/rollback"),
        ("POST", "/api/v1/admin/model-profiles/{model_profile_id}/activate"),
        ("POST", "/api/v1/admin/model-profiles/{model_profile_id}/rollback"),
    }
    expected_paths = {path for _, path in expected_route_methods}
    route_methods = {
        (method.upper(), path)
        for path, operations in openapi_paths.items()
        for method in operations
    }

    assert expected_paths <= paths
    assert expected_route_methods <= route_methods
