"""Helm chart structure tests."""

from pathlib import Path

CHART_ROOT = Path("ops/helm/rune-agent")


def test_helm_chart_has_required_release_artifacts() -> None:
    required_paths = {
        "Chart.yaml",
        "values.yaml",
        "templates/_helpers.tpl",
        "templates/configmap.yaml",
        "templates/deployment.yaml",
        "templates/service.yaml",
        "templates/ingress.yaml",
        "templates/hpa.yaml",
        "templates/pvc.yaml",
        "templates/serviceaccount.yaml",
    }

    missing = [path for path in required_paths if not (CHART_ROOT / path).exists()]

    assert missing == []


def test_helm_chart_maps_production_env_and_secret_refs() -> None:
    values = (CHART_ROOT / "values.yaml").read_text(encoding="utf-8")
    deployment = (CHART_ROOT / "templates/deployment.yaml").read_text(encoding="utf-8")

    for key in [
        "name: rune-agent-secrets",
        "STATE_STORE: postgres",
        "GRAPH_BACKEND: neo4j",
        "VECTOR_BACKEND: qdrant",
        "MODEL_GATEWAY_MODE: http_json",
        "AUTH_MODE: trusted_proxy",
        "SCHEDULER_LEASE_NAME: rune-periodic-analysis",
    ]:
        assert key in values
    for key in [
        "POSTGRES_DSN",
        "NEO4J_PASSWORD",
        "QDRANT_API_KEY",
        "MODEL_GATEWAY_API_KEY",
        "TRUSTED_PROXY_SECRET",
    ]:
        assert key in deployment
        assert "secretKeyRef" in deployment


def test_helm_chart_does_not_hardcode_secret_values_or_mcp_transport_names() -> None:
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CHART_ROOT.rglob("*.*"))
    forbidden = [
        "kind: Secret",
        "password: secret",
        "password: changeme",
        "token: secret",
        "api_key: secret",
        "RUNE_JIRA_MCP_URL",
        "RUNE_CONFLUENCE_MCP_URL",
    ]

    lowered = combined.lower()

    assert all(item.lower() not in lowered for item in forbidden)
    assert "existingSecret.name is required" in combined
