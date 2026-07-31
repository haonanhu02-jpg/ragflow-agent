"""Production composition for Phase 08 Agentic RAG services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from ragflow_agent.agent.application.agentic_runtime import AgenticRagRuntime
from ragflow_agent.agent.application.evidence import EvidenceSufficiencyPolicy
from ragflow_agent.agent.application.hitl import ApprovalService
from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.application.tool_policy import (
    SecureToolExecutionService,
    SecureToolRegistry,
)
from ragflow_agent.agent.graphs.agentic_rag import AgenticRagNodes
from ragflow_agent.agent.infrastructure.checkpoint import open_postgres_checkpoint_store
from ragflow_agent.agent.infrastructure.database import (
    SqlAlchemyAgentRunRepository,
    SqlAlchemyApprovalRepository,
    SqlAlchemyMemoryRepository,
)
from ragflow_agent.agent.infrastructure.langchain.planner import build_query_planner
from ragflow_agent.agent.tools.knowledge_base import AgentKnowledgeGateway, KnowledgeBaseTool
from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import create_session_factory
from ragflow_agent.knowledge.runtime import MinimumRagRuntime
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock


@dataclass(frozen=True, slots=True)
class AgenticRuntimeBundle:
    """Services exposed to the HTTP boundary while owned resources remain open."""

    runtime: AgenticRagRuntime
    memory: LongTermMemoryService
    tools: SecureToolRegistry


@asynccontextmanager
async def open_agentic_runtime(
    settings: AppSettings,
    minimum_rag: MinimumRagRuntime,
) -> AsyncIterator[AgenticRuntimeBundle]:
    """Open the official persistent checkpointer and compose the existing RAG core."""
    ids = Uuid4Generator()
    clock = SystemClock()
    sessions = create_session_factory(minimum_rag.engine)
    knowledge_tool = KnowledgeBaseTool(minimum_rag.query_service, ids)
    registry = SecureToolRegistry((knowledge_tool,))
    tool_execution = SecureToolExecutionService(registry=registry)
    approvals = ApprovalService(
        repository=SqlAlchemyApprovalRepository(sessions),
        tools=tool_execution,
        id_generator=ids,
        clock=clock,
        ttl_minutes=settings.agentic_rag.approval_ttl_minutes,
    )
    memory = LongTermMemoryService(
        repository=SqlAlchemyMemoryRepository(sessions),
        id_generator=ids,
        clock=clock,
        ttl_days=settings.agentic_rag.memory_ttl_days,
    )
    nodes = AgenticRagNodes(
        planner=build_query_planner(
            settings,
            allowed_tools=tuple(item.tool_name for item in registry.registrations),
        ),
        knowledge=AgentKnowledgeGateway(
            knowledge_tool=knowledge_tool,
            fixed_rag=minimum_rag.fixed_rag_service,
        ),
        tools=tool_execution,
        approvals=approvals,
        evidence_policy=EvidenceSufficiencyPolicy(
            minimum_normalized_score=settings.agentic_rag.evidence_min_score
        ),
    )
    database_url = settings.database.url.get_secret_value()
    async with open_postgres_checkpoint_store(database_url) as checkpoint_store:
        yield AgenticRuntimeBundle(
            runtime=AgenticRagRuntime(
                nodes=nodes,
                checkpointer=checkpoint_store.checkpointer,
                approvals=approvals,
                memory=memory,
                runs=SqlAlchemyAgentRunRepository(sessions),
                clock=clock,
            ),
            memory=memory,
            tools=registry,
        )
