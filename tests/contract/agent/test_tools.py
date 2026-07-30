"""Tool registry and LangChain adapter contracts."""

import pytest
from langchain.tools import tool

from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.domain.state import ToolCall
from ragflow_agent.agent.infrastructure.langchain import LangChainToolAdapter
from tests.fakes.agent import FakeAgentTool, agent_identity


@tool
def uppercase(value: str) -> dict[str, str]:
    """Uppercase one value."""
    return {"value": value.upper()}


@pytest.mark.asyncio
async def test_langchain_tool_returns_stable_structured_result() -> None:
    adapter = LangChainToolAdapter(uppercase)
    call = ToolCall(call_id="call-1", name="uppercase", arguments={"value": "rail"})

    result = await adapter.invoke(call, agent_identity())

    assert adapter.spec.input_schema["type"] == "object"
    assert result.status == "success"
    assert result.output == {"value": "RAIL"}


@pytest.mark.asyncio
async def test_registry_rejects_unknown_and_forbidden_tools() -> None:
    tool_adapter = FakeAgentTool(name="echo")
    forbidden = ToolExecutor(ToolRegistry([tool_adapter], AllowListToolPolicy([])))
    allowed = ToolExecutor(ToolRegistry([tool_adapter], AllowListToolPolicy(["echo"])))
    identity = agent_identity()

    with pytest.raises(AgentToolError) as denied:
        await forbidden.execute(
            ToolCall(call_id="1", name="echo"),
            identity,
            (),
        )
    assert denied.value.error_code == "agent_tool_forbidden"

    with pytest.raises(AgentToolError) as unknown:
        await allowed.execute(
            ToolCall(call_id="2", name="missing"),
            identity,
            (),
        )
    assert unknown.value.error_code == "agent_tool_unknown"


@pytest.mark.asyncio
async def test_executor_reuses_checkpointed_call_result() -> None:
    tool_adapter = FakeAgentTool()
    executor = ToolExecutor(
        ToolRegistry([tool_adapter], AllowListToolPolicy([tool_adapter.spec.name]))
    )
    call = ToolCall(call_id="stable", name=tool_adapter.spec.name)
    first = await executor.execute(call, agent_identity(), ())
    second = await executor.execute(call, agent_identity(), (first,))

    assert second == first
    assert tool_adapter.calls == ["stable"]


def test_registry_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate Tool"):
        ToolRegistry(
            [FakeAgentTool(name="duplicate"), FakeAgentTool(name="duplicate")],
            AllowListToolPolicy(["duplicate"]),
        )
