"""OTLP-compatible OpenTelemetry provider with safe no-export fallback."""

from __future__ import annotations

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ragflow_agent.config import ObservabilitySettings


def build_tracer_provider(
    settings: ObservabilitySettings,
    *,
    service_name: str,
) -> TracerProvider:
    """Build an isolated provider; exporter outages never alter business control flow."""
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    if settings.otel_enabled and settings.otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    return provider
