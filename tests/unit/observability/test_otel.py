"""OpenTelemetry configuration tests."""

from fastapi import FastAPI

from req_tracker.config.settings import Settings
from req_tracker.observability.otel import configure_opentelemetry


def test_opentelemetry_configuration_is_disabled_by_default(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(artifact_root=tmp_path / "artifacts")

    result = configure_opentelemetry(FastAPI(), settings)

    assert result == {
        "enabled": False,
        "reason": "disabled",
        "service_name": "rune-agent-api",
        "schema_version": "v1",
    }


def test_opentelemetry_requires_endpoint_when_enabled(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        otel_enabled=True,
        otel_exporter_otlp_endpoint="",
    )

    result = configure_opentelemetry(FastAPI(), settings)

    assert result == {
        "enabled": False,
        "reason": "missing_otlp_endpoint",
        "service_name": "rune-agent-api",
        "schema_version": "v1",
    }
