"""FastAPI application factory and transport-level wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.api.middleware import TraceContextMiddleware
from ragflow_agent.api.routes.health import build_health_router
from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import create_database_engine
from ragflow_agent.observability import current_trace_context
from ragflow_agent.shared import AppError

type ReadinessProbe = Callable[[AsyncEngine], Awaitable[bool]]


async def database_readiness_probe(engine: AsyncEngine) -> bool:
    """Return whether PostgreSQL accepts a simple query."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True


def create_app(
    settings: AppSettings,
    *,
    readiness_probe: ReadinessProbe = database_readiness_probe,
) -> FastAPI:
    """Create an application without import-time resources or side effects."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(settings.database)
        app.state.database_engine = engine
        app.state.settings = settings
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="ragflow-agent",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        TraceContextMiddleware,
        service_name=settings.api.service_name,
    )
    app.include_router(build_health_router(readiness_probe))

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, error: AppError) -> JSONResponse:
        del request
        context = current_trace_context()
        if context is not None:
            error.with_trace_id(context.trace_id)
        response = JSONResponse(status_code=error.status_code, content=error.to_dict())
        if error.trace_id:
            response.headers["x-trace-id"] = error.trace_id
        return response

    return app
