"""Tenant-scoped Agentic repositories over the shared async session factory."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update

from ragflow_agent.agent.domain.agentic import (
    AgentRunTrace,
    ApprovalRequest,
    LongTermMemory,
    MemoryConsent,
)
from ragflow_agent.agent.infrastructure.database.models import (
    AgentApprovalRow,
    AgentLongTermMemoryRow,
    AgentMemoryConsentRow,
    AgentRunRow,
)
from ragflow_agent.infrastructure.database.session import AsyncSessionFactory, session_scope


class SqlAlchemyApprovalRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save(self, request: ApprovalRequest) -> None:
        async with session_scope(self._sessions) as session:
            session.add(
                AgentApprovalRow(
                    tenant_id=request.tenant_id,
                    approval_id=request.approval_id,
                    run_id=request.run_id,
                    user_id=request.user_id,
                    status=request.status.value,
                    idempotency_key=request.idempotency_key,
                    expires_at=request.expires_at,
                    revision=request.revision,
                    payload=request.model_dump(mode="json"),
                )
            )

    async def get(self, *, tenant_id: str, approval_id: str) -> ApprovalRequest | None:
        async with session_scope(self._sessions) as session:
            row = await session.get(AgentApprovalRow, (tenant_id, approval_id))
            return ApprovalRequest.model_validate(row.payload) if row is not None else None

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> ApprovalRequest | None:
        async with session_scope(self._sessions) as session:
            row = await session.scalar(
                select(AgentApprovalRow).where(
                    AgentApprovalRow.tenant_id == tenant_id,
                    AgentApprovalRow.idempotency_key == idempotency_key,
                )
            )
            return ApprovalRequest.model_validate(row.payload) if row is not None else None

    async def compare_and_set(
        self,
        *,
        tenant_id: str,
        approval_id: str,
        expected_revision: int,
        request: ApprovalRequest,
    ) -> bool:
        async with session_scope(self._sessions) as session:
            result = await session.execute(
                update(AgentApprovalRow)
                .where(
                    AgentApprovalRow.tenant_id == tenant_id,
                    AgentApprovalRow.approval_id == approval_id,
                    AgentApprovalRow.revision == expected_revision,
                )
                .values(
                    status=request.status.value,
                    expires_at=request.expires_at,
                    revision=request.revision,
                    payload=request.model_dump(mode="json"),
                )
            )
            return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]


class SqlAlchemyMemoryRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save_consent(self, consent: MemoryConsent) -> None:
        async with session_scope(self._sessions) as session:
            row = await session.get(
                AgentMemoryConsentRow,
                (consent.tenant_id, consent.user_id),
            )
            if row is None:
                row = AgentMemoryConsentRow(
                    tenant_id=consent.tenant_id,
                    user_id=consent.user_id,
                    enabled=consent.enabled,
                    payload=consent.model_dump(mode="json"),
                )
                session.add(row)
            else:
                row.enabled = consent.enabled
                row.payload = consent.model_dump(mode="json")

    async def get_consent(self, *, tenant_id: str, user_id: str) -> MemoryConsent | None:
        async with session_scope(self._sessions) as session:
            row = await session.get(AgentMemoryConsentRow, (tenant_id, user_id))
            return MemoryConsent.model_validate(row.payload) if row is not None else None

    async def save_memory(self, memory: LongTermMemory) -> None:
        async with session_scope(self._sessions) as session:
            session.add(
                AgentLongTermMemoryRow(
                    tenant_id=memory.tenant_id,
                    user_id=memory.user_id,
                    memory_id=memory.memory_id,
                    expires_at=memory.expires_at,
                    deleted=memory.deleted_at is not None,
                    payload=memory.model_dump(mode="json"),
                )
            )

    async def list_memories(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> tuple[LongTermMemory, ...]:
        async with session_scope(self._sessions) as session:
            rows = (
                await session.scalars(
                    select(AgentLongTermMemoryRow).where(
                        AgentLongTermMemoryRow.tenant_id == tenant_id,
                        AgentLongTermMemoryRow.user_id == user_id,
                        AgentLongTermMemoryRow.deleted.is_(False),
                    )
                )
            ).all()
            return tuple(LongTermMemory.model_validate(row.payload) for row in rows)

    async def delete_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        memory_id: str,
    ) -> bool:
        async with session_scope(self._sessions) as session:
            result = await session.execute(
                delete(AgentLongTermMemoryRow).where(
                    AgentLongTermMemoryRow.tenant_id == tenant_id,
                    AgentLongTermMemoryRow.user_id == user_id,
                    AgentLongTermMemoryRow.memory_id == memory_id,
                )
            )
            return int(result.rowcount or 0) == 1  # type: ignore[attr-defined]

    async def delete_user_memories(self, *, tenant_id: str, user_id: str) -> int:
        async with session_scope(self._sessions) as session:
            result = await session.execute(
                delete(AgentLongTermMemoryRow).where(
                    AgentLongTermMemoryRow.tenant_id == tenant_id,
                    AgentLongTermMemoryRow.user_id == user_id,
                )
            )
            return int(result.rowcount)  # type: ignore[attr-defined]

    async def delete_expired(self, *, before: datetime) -> int:
        async with session_scope(self._sessions) as session:
            result = await session.execute(
                delete(AgentLongTermMemoryRow).where(AgentLongTermMemoryRow.expires_at <= before)
            )
            return int(result.rowcount)  # type: ignore[attr-defined]


class SqlAlchemyAgentRunRepository:
    def __init__(self, sessions: AsyncSessionFactory) -> None:
        self._sessions = sessions

    async def save(self, trace: AgentRunTrace) -> None:
        async with session_scope(self._sessions) as session:
            row = await session.get(AgentRunRow, (trace.tenant_id, trace.run_id))
            if row is None:
                row = AgentRunRow(
                    tenant_id=trace.tenant_id,
                    run_id=trace.run_id,
                    thread_id=trace.thread_id,
                    user_id=trace.user_id,
                    status=trace.status.value if trace.status else None,
                    updated_at=trace.updated_at,
                    payload=trace.model_dump(mode="json"),
                )
                session.add(row)
            else:
                row.status = trace.status.value if trace.status else None
                row.updated_at = trace.updated_at
                row.payload = trace.model_dump(mode="json")

    async def get(self, *, tenant_id: str, run_id: str) -> AgentRunTrace | None:
        async with session_scope(self._sessions) as session:
            row = await session.get(AgentRunRow, (tenant_id, run_id))
            return AgentRunTrace.model_validate(row.payload) if row is not None else None
