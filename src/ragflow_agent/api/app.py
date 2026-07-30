"""FastAPI application factory and transport-level wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.api.middleware import TraceContextMiddleware
from ragflow_agent.api.routes.health import build_health_router
from ragflow_agent.api.routes.knowledge import build_knowledge_router
from ragflow_agent.api.security import DevelopmentIdentityMiddleware
from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import create_database_engine
from ragflow_agent.observability import current_trace_context
from ragflow_agent.shared import AppError

if TYPE_CHECKING:
    from ragflow_agent.knowledge.runtime import MinimumRagRuntime

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
    minimum_rag_runtime: MinimumRagRuntime | None = None,
) -> FastAPI:
    """Create an application without import-time resources or side effects."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = (
            minimum_rag_runtime.engine
            if minimum_rag_runtime is not None
            else create_database_engine(settings.database)
        )
        app.state.database_engine = engine
        app.state.settings = settings
        if minimum_rag_runtime is not None:
            app.state.minimum_rag_runtime = minimum_rag_runtime
            await minimum_rag_runtime.open()
        try:
            yield
        finally:
            if minimum_rag_runtime is not None:
                await minimum_rag_runtime.close()
            else:
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
    app.add_middleware(
        DevelopmentIdentityMiddleware,
        enabled=settings.environment != "production",
    )
    app.include_router(build_health_router(readiness_probe))
    if minimum_rag_runtime is not None:
        app.include_router(build_knowledge_router())

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
