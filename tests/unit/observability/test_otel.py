"""OpenTelemetry configuration tests."""

from fastapi import FastAPI

from req_tracker.config.settings import Settings
from req_tracker.observability import otel
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


def test_opentelemetry_enabled_path_wires_exporter_and_fastapi(
    tmp_path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    calls = {
        "exporters": [],
        "processors": [],
        "providers": [],
        "instrumented": [],
        "global_provider": None,
    }

    class FakeExporter:
        def __init__(self, *, endpoint: str, insecure: bool) -> None:
            calls["exporters"].append({"endpoint": endpoint, "insecure": insecure})

    class FakeProcessor:
        def __init__(self, exporter: FakeExporter) -> None:
            calls["processors"].append(exporter)

    class FakeTracerProvider:
        def __init__(self, *, resource: object) -> None:
            self.resource = resource
            self.processors: list[FakeProcessor] = []
            calls["providers"].append(self)

        def add_span_processor(self, processor: FakeProcessor) -> None:
            self.processors.append(processor)

    class FakeInstrumentor:
        @staticmethod
        def instrument_app(app: FastAPI, *, tracer_provider: FakeTracerProvider) -> None:
            calls["instrumented"].append({"app": app, "tracer_provider": tracer_provider})

    def fake_set_tracer_provider(provider: FakeTracerProvider) -> None:
        calls["global_provider"] = provider

    monkeypatch.setattr(otel, "OTLPSpanExporter", FakeExporter)
    monkeypatch.setattr(otel, "BatchSpanProcessor", FakeProcessor)
    monkeypatch.setattr(otel, "TracerProvider", FakeTracerProvider)
    monkeypatch.setattr(otel, "FastAPIInstrumentor", FakeInstrumentor)
    monkeypatch.setattr(otel.trace, "set_tracer_provider", fake_set_tracer_provider)
    app = FastAPI()
    settings = Settings(
        artifact_root=tmp_path / "artifacts",
        environment="staging",
        otel_enabled=True,
        otel_service_name="rune-agent-staging",
        otel_exporter_otlp_endpoint="http://otel-collector:4317",
        otel_exporter_otlp_insecure=False,
    )

    result = configure_opentelemetry(app, settings)

    assert result == {
        "enabled": True,
        "service_name": "rune-agent-staging",
        "endpoint": "http://otel-collector:4317",
        "insecure": False,
        "schema_version": "v1",
    }
    assert calls["exporters"] == [
        {"endpoint": "http://otel-collector:4317", "insecure": False}
    ]
    assert calls["providers"]
    assert calls["global_provider"] is calls["providers"][0]
    assert calls["instrumented"] == [
        {"app": app, "tracer_provider": calls["providers"][0]}
    ]
