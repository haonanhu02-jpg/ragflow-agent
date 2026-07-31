"""Real PostgreSQL Retrieval Trace tenant isolation and TTL cleanup."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from ragflow_agent.config import DatabaseSettings
from ragflow_agent.infrastructure.database import create_database_engine, create_session_factory
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import (
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    RetrievalTraceStatus,
)
from ragflow_agent.knowledge.infrastructure.database import SqlAlchemyRetrievalTraceStore

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


def _database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


def _context(tenant: str) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant,
        actor_id="operator-a",
        request_id="request-a",
        roles=("retrieval_debug",),
    )


@pytest.mark.asyncio
async def test_trace_store_minimizes_content_isolates_tenants_and_cleans_expiry() -> None:
    engine = create_database_engine(DatabaseSettings(url=SecretStr(_database_url())))
    sessions = create_session_factory(engine)
    store = SqlAlchemyRetrievalTraceStore(sessions)
    suffix = NOW.strftime("%Y%m%d%H%M%S")
    trace_id = f"trace-phase06-{suffix}"
    trace = RetrievalTrace(
        trace_id=trace_id,
        request_id="request-a",
        tenant_id="tenant-phase06-a",
        original_query="sensitive user query",
        canonical_query="sensitive user query",
        authorization_applied=True,
        events=(
            RetrievalTraceEvent(
                sequence=0,
                stage=RetrievalStage.AUTHORIZATION,
                elapsed_ms=0,
                candidate_count=0,
            ),
        ),
        status=RetrievalTraceStatus.NO_EVIDENCE,
        started_at=NOW,
        completed_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    try:
        await store.save(trace)

        loaded = await store.get(_context("tenant-phase06-a"), trace_id)
        denied = await store.get(_context("tenant-phase06-b"), trace_id)
        assert loaded is not None
        assert loaded.original_query is None
        assert loaded.query_digest
        assert denied is None
        async with sessions() as session:
            payload = await session.scalar(
                text(
                    "select payload from knowledge_retrieval_traces "
                    "where tenant_id=:tenant_id and trace_id=:trace_id"
                ),
                {"tenant_id": "tenant-phase06-a", "trace_id": trace_id},
            )
        assert isinstance(payload, dict)
        assert "original_query" not in payload
        assert "sensitive user query" not in str(payload)

        assert await store.delete_expired(before=NOW + timedelta(days=29)) == 0
        assert await store.delete_expired(before=NOW + timedelta(days=31)) == 1
        assert await store.get(_context("tenant-phase06-a"), trace_id) is None
    finally:
        async with sessions() as session:
            await session.execute(
                text("delete from knowledge_retrieval_traces where trace_id=:trace_id"),
                {"trace_id": trace_id},
            )
            await session.commit()
        await engine.dispose()
