"""Real PostgreSQL Checkpoint persistence across a high-risk HITL reconstruction."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from langgraph.checkpoint.base import BaseCheckpointSaver
from pydantic import SecretStr

from ragflow_agent.agent.application.agentic_runtime import AgenticRagRuntime
from ragflow_agent.agent.application.evidence import EvidenceSufficiencyPolicy
from ragflow_agent.agent.application.hitl import ApprovalService
from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.application.tool_policy import (
    SecureToolExecutionService,
    SecureToolRegistry,
)
from ragflow_agent.agent.domain.agentic import (
    AgenticAuthorizationSnapshot,
    AgenticResumeRequest,
    AgenticRunRequest,
    AgenticRunStatus,
    PlanStep,
    QueryPlan,
    ToolEffect,
    ToolRiskLevel,
)
from ragflow_agent.agent.graphs.agentic_rag import AgenticRagNodes
from ragflow_agent.agent.infrastructure.checkpoint import open_postgres_checkpoint_store
from ragflow_agent.agent.infrastructure.database import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyApprovalRepository,
    SqlAlchemyMemoryRepository,
)
from ragflow_agent.agent.tools.knowledge_base import AgentKnowledgeGateway, KnowledgeBaseTool
from ragflow_agent.config import DatabaseSettings
from ragflow_agent.infrastructure.database import (
    AsyncSessionFactory,
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.application.fixed_rag import FixedRagService
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from tests.fakes.agentic import EchoKnowledgeQueryService, FakeRegisteredTool
from tests.fakes.knowledge import FixedClock, SequenceIdGenerator
from tests.fakes.minimum_rag import StubChatProvider


class HighRiskPlanner:
    async def plan(self, question: str) -> QueryPlan:
        del question
        return QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(
                    step_id="q1",
                    question="approved operation",
                    preferred_tool="high_risk_action",
                ),
            ),
        )


def _database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


def _build_runtime(
    *,
    checkpointer: BaseCheckpointSaver[str],
    sessions: AsyncSessionFactory,
    action: FakeRegisteredTool,
    ids: SequenceIdGenerator,
) -> AgenticRagRuntime:
    query = cast(KnowledgeQueryService, EchoKnowledgeQueryService())
    knowledge = KnowledgeBaseTool(query, ids)
    tools = SecureToolExecutionService(registry=SecureToolRegistry((knowledge, action)))
    clock = FixedClock(datetime(2026, 7, 31, tzinfo=UTC))
    approvals = ApprovalService(
        repository=SqlAlchemyApprovalRepository(sessions),
        tools=tools,
        id_generator=ids,
        clock=clock,
    )
    return AgenticRagRuntime(
        nodes=AgenticRagNodes(
            planner=HighRiskPlanner(),
            knowledge=AgentKnowledgeGateway(
                knowledge_tool=knowledge,
                fixed_rag=FixedRagService(
                    query_service=query,
                    chat_provider=StubChatProvider(),
                    chat_model_id="fake-chat",
                    id_generator=ids,
                ),
            ),
            tools=tools,
            approvals=approvals,
            evidence_policy=EvidenceSufficiencyPolicy(),
        ),
        checkpointer=checkpointer,
        approvals=approvals,
        memory=LongTermMemoryService(
            repository=SqlAlchemyMemoryRepository(sessions),
            id_generator=ids,
            clock=clock,
        ),
        runs=SqlAlchemyAgentRunRepository(sessions),
        clock=clock,
    )


@pytest.mark.asyncio
async def test_hitl_checkpoint_resumes_after_runtime_reconstruction() -> None:
    database_url = _database_url()
    suffix = uuid4().hex
    thread_id = f"phase08-thread-{suffix}"
    run_id = f"phase08-run-{suffix}"
    action = FakeRegisteredTool(
        name="high_risk_action",
        output={"done": True},
        effect=ToolEffect.SIDE_EFFECTING,
        risk=ToolRiskLevel.HIGH,
        requires_hitl=True,
        approval_roles=("tool-approver",),
    )
    ids = SequenceIdGenerator([f"phase08-id-{suffix}-{index}" for index in range(20)])
    engine = create_database_engine(DatabaseSettings(url=SecretStr(database_url)))
    sessions = create_session_factory(engine)
    try:
        async with open_postgres_checkpoint_store(database_url) as store:
            first = _build_runtime(
                checkpointer=store.checkpointer,
                sessions=sessions,
                action=action,
                ids=ids,
            )
            paused = await first.run(
                AgenticRunRequest(
                    run_id=run_id,
                    thread_id=thread_id,
                    context=AgenticAuthorizationSnapshot(
                        tenant_id=f"tenant-{suffix}",
                        user_id="user-a",
                        request_id=f"request-{suffix}",
                        knowledge_base_ids=("kb-a",),
                    ),
                    question="run the approved operation",
                )
            )
            assert paused.interrupted
            assert paused.state.approval_id is not None

            reconstructed = _build_runtime(
                checkpointer=store.checkpointer,
                sessions=sessions,
                action=action,
                ids=ids,
            )
            resumed = await reconstructed.resume(
                AgenticResumeRequest(
                    run_id=run_id,
                    thread_id=thread_id,
                    approval_id=paused.state.approval_id,
                    tenant_id=f"tenant-{suffix}",
                    approver_id="approver-a",
                    approver_request_id=f"approve-{suffix}",
                    approver_roles=("tool-approver",),
                    decision="approve",
                )
            )
            assert resumed.state.final_status is AgenticRunStatus.COMPLETED
            assert len(action.calls) == 1
    finally:
        await engine.dispose()
