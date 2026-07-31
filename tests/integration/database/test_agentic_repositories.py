"""Real PostgreSQL persistence, tenant isolation, CAS, and memory cleanup."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import SecretStr

from ragflow_agent.agent.domain.agentic import (
    AgentRunTrace,
    ApprovalRequest,
    ApprovalStatus,
    BudgetLimits,
    BudgetUsage,
    LongTermMemory,
    MemoryConsent,
)
from ragflow_agent.agent.infrastructure.database import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyApprovalRepository,
    SqlAlchemyMemoryRepository,
)
from ragflow_agent.config import DatabaseSettings
from ragflow_agent.infrastructure.database import create_database_engine, create_session_factory


def _database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_agentic_repositories_isolate_tenant_and_execute_cleanup() -> None:
    engine = create_database_engine(DatabaseSettings(url=SecretStr(_database_url())))
    sessions = create_session_factory(engine)
    approvals = SqlAlchemyApprovalRepository(sessions)
    memories = SqlAlchemyMemoryRepository(sessions)
    runs = SqlAlchemyAgentRunRepository(sessions)
    suffix = uuid4().hex
    now = datetime.now(UTC)
    tenant = f"tenant-phase08-{suffix}"
    try:
        approval = ApprovalRequest(
            approval_id=f"approval-{suffix}",
            run_id=f"run-{suffix}",
            thread_id=f"thread-{suffix}",
            tool_call_id=f"call-{suffix}",
            tool_name="fake_high_risk",
            tool_version="1",
            argument_digest="a" * 64,
            tenant_id=tenant,
            user_id="user-a",
            reason="high risk",
            required_roles=("tool-approver",),
            created_at=now,
            expires_at=now + timedelta(minutes=30),
            idempotency_key=f"idem-{suffix}",
        )
        await approvals.save(approval)
        other_tenant = await approvals.get(
            tenant_id="other-tenant", approval_id=approval.approval_id
        )
        assert other_tenant is None
        approved = approval.model_copy(update={"status": ApprovalStatus.APPROVED, "revision": 1})
        assert await approvals.compare_and_set(
            tenant_id=tenant,
            approval_id=approval.approval_id,
            expected_revision=0,
            request=approved,
        )
        assert not await approvals.compare_and_set(
            tenant_id=tenant,
            approval_id=approval.approval_id,
            expected_revision=0,
            request=approved,
        )

        await memories.save_consent(
            MemoryConsent(
                tenant_id=tenant,
                user_id="user-a",
                enabled=True,
                consent_version="v1",
                consented_at=now,
            )
        )
        memory = LongTermMemory(
            memory_id=f"memory-{suffix}",
            tenant_id=tenant,
            user_id="user-a",
            content="Use metric units",
            source="explicit_user_request",
            consent_version="v1",
            consented_at=now,
            created_at=now,
            expires_at=now - timedelta(seconds=1),
        )
        await memories.save_memory(memory)
        assert await memories.list_memories(tenant_id="other-tenant", user_id="user-a") == ()
        assert await memories.delete_expired(before=now) >= 1
        assert await memories.list_memories(tenant_id=tenant, user_id="user-a") == ()

        trace = AgentRunTrace(
            run_id=f"run-{suffix}",
            thread_id=f"thread-{suffix}",
            request_id=f"request-{suffix}",
            tenant_id=tenant,
            user_id="user-a",
            status=None,
            retrieval_trace_ids=(f"retrieval-{suffix}",),
            model_provider_ids=("chat:fake",),
            tool_calls=(),
            budget_limits=BudgetLimits(),
            budget_usage=BudgetUsage(),
            stop_reason=None,
            started_at=now,
            updated_at=now,
        )
        await runs.save(trace)
        assert await runs.get(tenant_id=tenant, run_id=trace.run_id) == trace
        assert await runs.get(tenant_id="other-tenant", run_id=trace.run_id) is None
    finally:
        await engine.dispose()
