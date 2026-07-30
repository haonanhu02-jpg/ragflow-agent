"""Liveness and readiness routes."""

from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

type ReadinessProbe = Callable[[AsyncEngine], Awaitable[bool]]


def build_health_router(readiness_probe: ReadinessProbe) -> APIRouter:
    """Build health routes with an injectable infrastructure probe."""
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live")
    async def live() -> dict[str, str]:
        return {"status": "live"}

    @router.get("/ready")
    async def ready(request: Request) -> JSONResponse:
        engine: AsyncEngine = request.app.state.database_engine
        is_ready = await readiness_probe(engine)
        status_code = 200 if is_ready else 503
        status = "ready" if is_ready else "not_ready"
        return JSONResponse(status_code=status_code, content={"status": status})

    return router
