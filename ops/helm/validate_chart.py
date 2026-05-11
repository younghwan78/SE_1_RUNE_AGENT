"""Validate the local Helm chart scaffold without requiring the Helm binary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHART_ROOT = ROOT / "ops" / "helm" / "rune-agent"

REQUIRED_FILES = {
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

REQUIRED_VALUE_SNIPPETS = {
    "name: rune-agent-secrets",
    "STATE_STORE: postgres",
    "GRAPH_BACKEND: neo4j",
    "VECTOR_BACKEND: qdrant",
    "MODEL_GATEWAY_MODE: http_json",
    "AUTH_MODE: trusted_proxy",
    "SCHEDULER_LEASE_NAME: rune-periodic-analysis",
    "OTEL_ENABLED: \"false\"",
    "OTEL_SERVICE_NAME: rune-agent-api",
}

REQUIRED_SECRET_REFS = {
    "POSTGRES_DSN",
    "NEO4J_PASSWORD",
    "QDRANT_API_KEY",
    "MODEL_GATEWAY_API_KEY",
    "TRUSTED_PROXY_SECRET",
}

FORBIDDEN_SNIPPETS = {
    "kind: secret",
    "password: secret",
    "password: changeme",
    "token: secret",
    "api_key: secret",
    "rune_jira_mcp_url",
    "rune_confluence_mcp_url",
}


def validate_chart() -> dict[str, object]:
    """Return a structured Helm chart validation result."""
    missing_files = sorted(path for path in REQUIRED_FILES if not (CHART_ROOT / path).exists())
    values = _read("values.yaml")
    deployment = _read("templates/deployment.yaml")
    combined = "\n".join(path.read_text(encoding="utf-8") for path in CHART_ROOT.rglob("*.*"))
    missing_values = sorted(
        snippet for snippet in REQUIRED_VALUE_SNIPPETS if snippet not in values
    )
    missing_secret_refs = sorted(
        snippet for snippet in REQUIRED_SECRET_REFS if snippet not in deployment
    )
    forbidden_hits = sorted(
        snippet for snippet in FORBIDDEN_SNIPPETS if snippet in combined.lower()
    )
    passed = not any(
        [missing_files, missing_values, missing_secret_refs, forbidden_hits]
    )
    return {
        "passed": passed,
        "chart_root": str(CHART_ROOT.relative_to(ROOT)),
        "missing_files": missing_files,
        "missing_values": missing_values,
        "missing_secret_refs": missing_secret_refs,
        "forbidden_hits": forbidden_hits,
        "schema_version": "v1",
    }


def _read(relative_path: str) -> str:
    path = CHART_ROOT / relative_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def main() -> int:
    """CLI entrypoint."""
    import json

    result = validate_chart()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
