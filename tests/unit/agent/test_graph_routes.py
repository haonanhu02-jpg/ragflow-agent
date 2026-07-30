"""Static and executable route tests for the minimal graph."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import ModelDecision, RuntimeLimits
from ragflow_agent.agent.domain.state import AgentState, graph_state_from_model
from ragflow_agent.agent.graphs.minimal_agent import (
    MINIMAL_AGENT_EDGES,
    MINIMAL_AGENT_NODES,
    build_minimal_agent_graph,
)
from ragflow_agent.agent.nodes import MinimalAgentNodes
from tests.fakes.agent import FakeAgentTool, ScriptedAgentModel, agent_identity


def _executor(tool: FakeAgentTool) -> ToolExecutor:
    return ToolExecutor(ToolRegistry([tool], AllowListToolPolicy([tool.spec.name])))


def test_minimal_topology_has_only_one_bounded_loop_and_two_terminal_routes() -> None:
    assert MINIMAL_AGENT_NODES == (
        "normalize_input",
        "decide",
        "execute_tool",
        "observe",
        "finish",
    )
    assert ("observe", "decide") in MINIMAL_AGENT_EDGES
    assert ("finish", "__end__") in MINIMAL_AGENT_EDGES
    assert ("decide", "execute_tool|finish") in MINIMAL_AGENT_EDGES


@pytest.mark.asyncio
async def test_direct_answer_route_terminates() -> None:
    identity = agent_identity()
    tool_adapter = FakeAgentTool()
    model = ScriptedAgentModel([ModelDecision(kind="final", content="ready")])
    graph = build_minimal_agent_graph(
        MinimalAgentNodes(model, _executor(tool_adapter)),
        InMemorySaver(),
        RuntimeLimits(),
    )

    output = await graph.ainvoke(
        graph_state_from_model(AgentState.initial(identity, "status")),
        {"configurable": {"thread_id": "direct", "checkpoint_ns": "test"}},
    )

    assert output["termination_reason"] == "completed"
    assert output["final_answer"] == "ready"
    assert tool_adapter.calls == []


@pytest.mark.asyncio
async def test_tool_route_observes_then_terminates() -> None:
    identity = agent_identity()
    tool_adapter = FakeAgentTool(output={"status": "nominal"})
    model = ScriptedAgentModel(
        [
            ModelDecision(kind="tool", tool_name="echo", tool_arguments={"value": "x"}),
            ModelDecision(kind="final", content="observed"),
        ]
    )
    graph = build_minimal_agent_graph(
        MinimalAgentNodes(model, _executor(tool_adapter)),
        InMemorySaver(),
        RuntimeLimits(),
    )

    output = await graph.ainvoke(
        graph_state_from_model(AgentState.initial(identity, "use Tool")),
        {"configurable": {"thread_id": "tool", "checkpoint_ns": "test"}},
    )

    assert output["termination_reason"] == "completed"
    assert output["final_answer"] == "observed"
    assert len(tool_adapter.calls) == 1
