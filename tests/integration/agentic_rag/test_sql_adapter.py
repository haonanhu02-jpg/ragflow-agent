"""Real PostgreSQL smoke for the AST-scoped read-only SQL adapter."""

from __future__ import annotations

import os

import pytest

from ragflow_agent.agent.domain.agentic import ToolAuthorizationContext, ToolInvocation
from ragflow_agent.agent.infrastructure.sql import SqlAlchemyReadOnlyExecutor
from ragflow_agent.agent.tools.sql import ReadOnlySqlTool, SqlAllowlist


def _database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_read_only_sql_adapter_executes_tenant_scoped_query() -> None:
    executor = SqlAlchemyReadOnlyExecutor(_database_url())
    try:
        tool = ReadOnlySqlTool(
            executor=executor,
            allowlist=SqlAllowlist(
                schema_name="public",
                tables={"knowledge_bases": ("tenant_id", "id")},
            ),
        )
        output = await tool.invoke(
            ToolInvocation(
                tool_call_id="sql-adapter-smoke",
                tool_name="readonly_sql",
                tool_version="1",
                arguments={
                    "statement": "SELECT id FROM public.knowledge_bases ORDER BY id",
                    "parameters": {},
                },
            ),
            ToolAuthorizationContext(
                tenant_id="tenant-phase08-sql-smoke",
                actor_id="user-phase08-sql-smoke",
                request_id="request-phase08-sql-smoke",
            ),
        )
    finally:
        await executor.close()

    assert output == []
