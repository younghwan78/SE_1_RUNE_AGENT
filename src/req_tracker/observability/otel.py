"""OpenTelemetry wiring for production-shaped deployments."""

from typing import Any

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def configure_opentelemetry(app: FastAPI, settings: Any) -> dict[str, Any]:
    """Configure OTLP trace export when explicitly enabled."""
    if not settings.otel_enabled:
        return {
            "enabled": False,
            "reason": "disabled",
            "service_name": settings.otel_service_name,
            "schema_version": "v1",
        }
    if not settings.otel_exporter_otlp_endpoint:
        return {
            "enabled": False,
            "reason": "missing_otlp_endpoint",
            "service_name": settings.otel_service_name,
            "schema_version": "v1",
        }

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.environment,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            )
        )
    )
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    return {
        "enabled": True,
        "service_name": settings.otel_service_name,
        "endpoint": settings.otel_exporter_otlp_endpoint,
        "insecure": settings.otel_exporter_otlp_insecure,
        "schema_version": "v1",
    }
