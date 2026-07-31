"""SQLAlchemy adapter for minimized tenant-scoped retrieval traces."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from ragflow_agent.infrastructure.database import AsyncSessionFactory
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import RetrievalTrace
from ragflow_agent.knowledge.infrastructure.database.models import RetrievalTraceRow


class SqlAlchemyRetrievalTraceStore:
    """Persist, isolate, and expire RetrievalTrace schema v2 records."""

    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save(self, trace: RetrievalTrace) -> None:
        if trace.request_id is None or trace.expires_at is None:
            raise ValueError("persisted retrieval traces require request_id and expires_at")
        row = RetrievalTraceRow(
            tenant_id=trace.tenant_id,
            trace_id=trace.trace_id,
            request_id=trace.request_id,
            expires_at=trace.expires_at,
            payload=trace.model_dump(mode="json"),
        )
        async with self._sessions() as session:
            await session.merge(row)
            await session.commit()

    async def get(
        self,
        context: AuthorizationContext,
        trace_id: str,
    ) -> RetrievalTrace | None:
        async with self._sessions() as session:
            row = await session.scalar(
                select(RetrievalTraceRow).where(
                    RetrievalTraceRow.tenant_id == context.tenant_id,
                    RetrievalTraceRow.trace_id == trace_id,
                )
            )
        return RetrievalTrace.model_validate(row.payload) if row is not None else None

    async def delete_expired(self, *, before: datetime) -> int:
        async with self._sessions() as session:
            result = await session.execute(
                delete(RetrievalTraceRow).where(RetrievalTraceRow.expires_at <= before)
            )
            await session.commit()
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
