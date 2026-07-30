"""FastAPI bootstrap integration tests."""

from collections.abc import Iterator

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.api import create_app
from ragflow_agent.api.security import require_trusted_identity
from ragflow_agent.config import AppSettings, DatabaseSettings
from ragflow_agent.shared import AppError


async def _ready(engine: AsyncEngine) -> bool:
    del engine
    return True


@pytest.fixture
def client() -> Iterator[TestClient]:
    settings = AppSettings(
        database=DatabaseSettings(
            url=SecretStr("postgresql+psycopg://test:test@localhost/test")
        )
    )
    app = create_app(settings, readiness_probe=_ready)

    @app.get("/test/error", include_in_schema=False)
    async def error_route() -> None:
        raise AppError("test failure", error_code="test_error", status_code=409)

    @app.get("/test/identity", include_in_schema=False)
    async def identity_route(request: Request) -> None:
        require_trusted_identity(request)

    with TestClient(app) as test_client:
        yield test_client


def test_health_and_openapi(client: TestClient) -> None:
    assert client.get("/health/live").json() == {"status": "live"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert "/health/live" in client.get("/openapi.json").json()["paths"]


def test_trace_id_is_created_or_propagated(client: TestClient) -> None:
    generated = client.get("/health/live").headers["x-trace-id"]
    propagated = client.get("/health/live", headers={"x-trace-id": "trace-123"})

    assert generated
    assert propagated.headers["x-trace-id"] == "trace-123"


def test_app_error_has_stable_payload_and_trace(client: TestClient) -> None:
    response = client.get("/test/error", headers={"x-trace-id": "trace-error"})

    assert response.status_code == 409
    assert response.headers["x-trace-id"] == "trace-error"
    assert response.json() == {
        "error_code": "test_error",
        "message": "test failure",
        "trace_id": "trace-error",
    }


def test_caller_headers_do_not_create_a_trusted_identity(client: TestClient) -> None:
    response = client.get(
        "/test/identity",
        headers={"x-tenant-id": "spoofed", "x-owner-id": "spoofed"},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "authentication_required"
