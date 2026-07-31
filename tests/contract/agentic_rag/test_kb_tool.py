from typing import Any, cast

import pytest

from ragflow_agent.agent.domain.agentic import ToolAuthorizationContext, ToolInvocation
from ragflow_agent.agent.tools.knowledge_base import (
    KnowledgeBaseTool,
    KnowledgeBaseToolOutput,
)
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from tests.fakes.agentic import EchoKnowledgeQueryService
from tests.fakes.knowledge import SequenceIdGenerator


@pytest.mark.asyncio
async def test_knowledge_tool_injects_trusted_tenant_and_returns_citations() -> None:
    query_service = EchoKnowledgeQueryService()
    tool = KnowledgeBaseTool(
        cast(KnowledgeQueryService, query_service),
        SequenceIdGenerator(["retrieval-1"]),
    )
    context = ToolAuthorizationContext(
        tenant_id="tenant-a",
        actor_id="user-a",
        request_id="request-a",
    )

    raw = await tool.invoke(
        ToolInvocation(
            tool_call_id="call-1",
            tool_name="knowledge_base",
            tool_version="1",
            arguments={"query": "设备如何复位", "knowledge_base_ids": ["kb-a"]},
        ),
        context,
    )

    output = KnowledgeBaseToolOutput.model_validate(raw)
    called_context, query = query_service.calls[0]
    assert called_context.tenant_id == context.tenant_id
    assert called_context.actor_id == context.actor_id
    assert called_context.request_id == context.request_id
    assert query.tenant_id == "tenant-a"
    assert output.retrieval_trace_id == "retrieval-1"
    assert output.evidence[0].citation.tenant_id == "tenant-a"
    assert output.citations == (output.evidence[0].citation,)


def test_knowledge_tool_is_a_real_langchain_structured_tool() -> None:
    query_service = EchoKnowledgeQueryService()
    tool = KnowledgeBaseTool(
        cast(KnowledgeQueryService, query_service),
        SequenceIdGenerator(["call-1"]),
    )
    context = ToolAuthorizationContext(
        tenant_id="tenant-a",
        actor_id="user-a",
        request_id="request-a",
    )

    structured = cast(Any, tool.as_langchain_tool(context))

    assert structured.name == "knowledge_base"
    assert "tenant_id" not in structured.args
