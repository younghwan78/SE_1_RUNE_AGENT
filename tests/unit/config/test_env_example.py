from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _env_example_keys() -> set[str]:
    keys: set[str] = set()
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _value = stripped.split("=", 1)
        keys.add(key)
    return keys


def _env_file_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def test_env_example_covers_production_readiness_inputs() -> None:
    required_keys = {
        "STATE_STORE",
        "POSTGRES_DSN",
        "POSTGRES_TEST_DSN",
        "GRAPH_BACKEND",
        "NEO4J_URI",
        "NEO4J_USERNAME",
        "NEO4J_PASSWORD",
        "NEO4J_TEST_URI",
        "VECTOR_BACKEND",
        "QDRANT_URL",
        "QDRANT_COLLECTION",
        "QDRANT_TEST_URL",
        "MODEL_GATEWAY_MODE",
        "MODEL_GATEWAY_ENDPOINT_URL",
        "MODEL_GATEWAY_API_KEY",
        "MODEL_GATEWAY_PROVIDER",
        "MODEL_GATEWAY_PROFILE_ID",
        "MODEL_GATEWAY_MODEL_NAME",
        "MODEL_GATEWAY_PROMPT_VERSION_ID",
        "MODEL_GATEWAY_TIMEOUT_SECONDS",
        "AUTH_MODE",
        "TRUSTED_PROXY_SECRET",
        "TRUSTED_GROUP_ROLE_MAP",
        "RUNE_API_BASE_URL",
        "ARTIFACT_ROOT",
        "OTEL_ENABLED",
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_EXPORTER_OTLP_INSECURE",
        "JIRA_BASE_URL",
        "JIRA_TOKEN",
        "JIRA_PROJECT_KEY",
        "JIRA_REHEARSAL_LIMIT",
        "CONFLUENCE_BASE_URL",
        "CONFLUENCE_TOKEN",
        "CONFLUENCE_SPACE_KEY",
        "CONFLUENCE_REHEARSAL_LIMIT",
        "RUNE_EMAIL_EXPORT_PATH",
        "RUNE_EMAIL_EXPORT_LIMIT",
    }

    assert required_keys <= _env_example_keys()


def test_staging_env_example_sets_production_modes_without_fake_secrets() -> None:
    values = _env_file_values(ROOT / "ops/rehearsal/staging.env.example")

    assert values["STATE_STORE"] == "postgres"
    assert values["GRAPH_BACKEND"] == "neo4j"
    assert values["VECTOR_BACKEND"] == "qdrant"
    assert values["MODEL_GATEWAY_MODE"] == "http_json"
    assert values["AUTH_MODE"] == "trusted_proxy"
    assert values["OTEL_ENABLED"] == "true"
    assert values["ARTIFACT_ROOT"] == "/var/lib/rune-agent/artifacts"

    for secret_key in [
        "POSTGRES_DSN",
        "NEO4J_PASSWORD",
        "QDRANT_API_KEY",
        "MODEL_GATEWAY_API_KEY",
        "TRUSTED_PROXY_SECRET",
        "JIRA_TOKEN",
        "CONFLUENCE_TOKEN",
    ]:
        assert values[secret_key] == ""
