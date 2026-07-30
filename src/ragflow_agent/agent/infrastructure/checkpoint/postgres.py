"""Official asynchronous PostgreSQL Checkpointer lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from ragflow_agent.agent.infrastructure.checkpoint.scoped import (
    TenantScopedCheckpointStore,
)


@asynccontextmanager
async def open_postgres_checkpoint_store(
    database_url: str,
) -> AsyncIterator[TenantScopedCheckpointStore]:
    """Open and migrate the official LangGraph PostgreSQL saver."""
    connection_string = _normalize_psycopg_url(database_url)
    async with AsyncPostgresSaver.from_conn_string(connection_string) as saver:
        await saver.setup()
        yield TenantScopedCheckpointStore(saver)


def _normalize_psycopg_url(database_url: str) -> str:
    if not database_url:
        raise ValueError("database_url must not be empty")
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
