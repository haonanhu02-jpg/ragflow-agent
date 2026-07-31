from typing import cast

import pytest

from ragflow_agent.agent.application.budgets import BudgetLedger
from ragflow_agent.agent.domain.agentic import BudgetLimits, ToolAuthorizationContext
from ragflow_agent.agent.tools.knowledge_base import AgentKnowledgeGateway, KnowledgeBaseTool
from ragflow_agent.knowledge.application.fixed_rag import FixedRagService
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from tests.fakes.agentic import EchoKnowledgeQueryService
from tests.fakes.knowledge import SequenceIdGenerator
from tests.fakes.minimum_rag import StubChatProvider


@pytest.mark.asyncio
async def test_gateway_and_tool_share_the_same_query_service() -> None:
    query_service = EchoKnowledgeQueryService()
    ids = SequenceIdGenerator(["tool-trace", "fixed-trace"])
    typed_query = cast(KnowledgeQueryService, query_service)
    tool = KnowledgeBaseTool(typed_query, ids)
    fixed = FixedRagService(
        query_service=typed_query,
        chat_provider=StubChatProvider(),
        chat_model_id="fake-chat",
        id_generator=ids,
    )
    gateway = AgentKnowledgeGateway(knowledge_tool=tool, fixed_rag=fixed)
    context = ToolAuthorizationContext(
        tenant_id="tenant-a",
        actor_id="user-a",
        request_id="request-a",
    )

    evidence, trace_id = await gateway.retrieve_step(
        context=context,
        step_id="q1",
        question="复位步骤",
        knowledge_base_ids=("kb-a",),
        budget=BudgetLedger(limits=tool_budget()),
    )
    direct = await gateway.direct_answer(
        context=context,
        question="复位步骤",
        knowledge_base_ids=("kb-a",),
        model_budget=BudgetLedger(limits=tool_budget()),
    )

    assert len(query_service.calls) == 2
    assert trace_id == "tool-trace"
    assert evidence[0].citation is not None
    assert evidence[0].citation.knowledge == direct.citations[0]


def tool_budget() -> BudgetLimits:
    return BudgetLimits()
