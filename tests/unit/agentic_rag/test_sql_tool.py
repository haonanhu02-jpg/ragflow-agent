import pytest

from ragflow_agent.agent.domain.agentic import ToolAuthorizationContext, ToolInvocation
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.tools.sql import ReadOnlySqlTool, SqlAllowlist, validate_and_scope_sql
from tests.fakes.agentic import FakeSqlExecutor

ALLOWLIST = SqlAllowlist(
    schema_name="public",
    tables={"work_orders": ("tenant_id", "order_id", "status")},
)


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE work_orders SET status = :status",
        "DELETE FROM work_orders",
        "DROP TABLE work_orders",
        "SELECT tenant_id FROM work_orders; SELECT tenant_id FROM work_orders",
        "SELECT tenant_id FROM secrets",
        "SELECT * FROM work_orders",
        "SELECT tenant_id, password FROM work_orders",
        "SELECT tenant_id FROM work_orders WHERE status = 'closed'",
        "SELECT tenant_id, pg_read_file(:path) FROM work_orders",
        "SELECT tenant_id FROM work_orders",
        "SELECT tenant_id FROM private.work_orders",
        "SELECT tenant_id FROM other.public.work_orders",
    ],
)
def test_sql_ast_rejects_writes_multiple_statements_scope_and_literals(statement: str) -> None:
    with pytest.raises(AgentToolError):
        validate_and_scope_sql(statement, allowlist=ALLOWLIST)


@pytest.mark.asyncio
async def test_sql_tool_injects_tenant_limit_and_uses_bound_parameters() -> None:
    executor = FakeSqlExecutor(({"tenant_id": "tenant-a", "order_id": "wo-1"},))
    tool = ReadOnlySqlTool(executor=executor, allowlist=ALLOWLIST)
    context = ToolAuthorizationContext(
        tenant_id="tenant-a", actor_id="user-a", request_id="request-a"
    )

    output = await tool.invoke(
        ToolInvocation(
            tool_call_id="sql-1",
            tool_name="readonly_sql",
            tool_version="1",
            arguments={
                "statement": (
                    "SELECT tenant_id, order_id FROM public.work_orders WHERE status = :status"
                ),
                "parameters": {"status": "closed"},
            },
        ),
        context,
    )

    assert output == [{"tenant_id": "tenant-a", "order_id": "wo-1"}]
    call = executor.calls[0]
    assert call["parameters"] == {
        "status": "closed",
        "_agent_tenant_id": "tenant-a",
        "_agent_limit": 200,
    }
    assert ":_agent_tenant_id" in str(call["statement"])
    assert 'FROM (SELECT * FROM public.work_orders WHERE "tenant_id" = :_agent_tenant_id)' in str(
        call["statement"]
    )


def test_sql_tenant_filter_is_applied_before_aggregation() -> None:
    statement = validate_and_scope_sql(
        "SELECT status, count(order_id) AS total FROM public.work_orders GROUP BY status",
        allowlist=ALLOWLIST,
    )

    tenant_filter = statement.index('WHERE "tenant_id" = :_agent_tenant_id')
    aggregation = statement.index("GROUP BY")
    assert tenant_filter < aggregation


@pytest.mark.asyncio
async def test_model_cannot_override_reserved_tenant_parameter() -> None:
    tool = ReadOnlySqlTool(executor=FakeSqlExecutor(), allowlist=ALLOWLIST)
    with pytest.raises(AgentToolError, match="reserved"):
        await tool.invoke(
            ToolInvocation(
                tool_call_id="sql-1",
                tool_name="readonly_sql",
                tool_version="1",
                arguments={
                    "statement": "SELECT tenant_id FROM public.work_orders",
                    "parameters": {"_agent_tenant_id": "tenant-b"},
                },
            ),
            ToolAuthorizationContext(
                tenant_id="tenant-a", actor_id="user-a", request_id="request-a"
            ),
        )
