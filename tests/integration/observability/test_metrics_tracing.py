from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import generate_latest

from ragflow_agent.config import ObservabilitySettings
from ragflow_agent.observability.metrics import MetricsMiddleware
from ragflow_agent.observability.tracing import build_tracer_provider


def test_http_metrics_are_exposed_without_sensitive_labels() -> None:
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/safe/{item_id}")
    async def safe(item_id: str) -> dict[str, str]:
        return {"item": item_id}

    with TestClient(app) as client:
        assert client.get("/safe/tenant-secret").status_code == 200
    metrics = generate_latest().decode()
    assert 'route="/safe/{item_id}"' in metrics
    assert "tenant-secret" not in metrics


def test_otel_provider_can_run_without_exporter_or_credentials() -> None:
    provider = build_tracer_provider(ObservabilitySettings(), service_name="test")
    with provider.get_tracer("test").start_as_current_span("parser"):
        pass
    provider.shutdown()


def test_observability_configs_exist() -> None:
    assert Path("deploy/observability/prometheus.yml").is_file()
    assert Path("deploy/observability/alerts.yml").is_file()
    assert Path("deploy/observability/dashboards/ragflow-agent.json").is_file()
