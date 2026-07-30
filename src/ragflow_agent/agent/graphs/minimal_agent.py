"""Compile the bounded Phase 02 Agent graph."""

from __future__ import annotations

from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from ragflow_agent.agent.domain.limits import RuntimeLimits
from ragflow_agent.agent.domain.state import AgentGraphState
from ragflow_agent.agent.nodes.minimal import MinimalAgentNodes, decision_route

MINIMAL_AGENT_NODES = (
    "normalize_input",
    "decide",
    "execute_tool",
    "observe",
    "finish",
)
MINIMAL_AGENT_EDGES = (
    ("__start__", "normalize_input"),
    ("normalize_input", "decide"),
    ("decide", "execute_tool|finish"),
    ("execute_tool", "observe"),
    ("observe", "decide"),
    ("finish", "__end__"),
)


def build_minimal_agent_graph(
    nodes: MinimalAgentNodes,
    checkpointer: BaseCheckpointSaver[str],
    limits: RuntimeLimits,
) -> CompiledStateGraph[AgentGraphState, None, AgentGraphState, AgentGraphState]:
    """Build a graph whose only loop returns from observation to model decision."""
    builder = StateGraph(AgentGraphState)
    builder.add_node(
        "normalize_input",
        RunnableLambda(nodes.normalize_input),
        timeout=limits.model_timeout_seconds,
    )
    builder.add_node(
        "decide",
        RunnableLambda(nodes.decide),
        timeout=limits.model_timeout_seconds,
    )
    builder.add_node(
        "execute_tool",
        RunnableLambda(nodes.execute_tool),
        timeout=limits.tool_timeout_seconds,
    )
    builder.add_node("observe", RunnableLambda(nodes.observe))
    builder.add_node("finish", RunnableLambda(nodes.finish))
    builder.add_edge(START, "normalize_input")
    builder.add_edge("normalize_input", "decide")
    builder.add_conditional_edges(
        "decide",
        decision_route,
        {"execute_tool": "execute_tool", "finish": "finish"},
    )
    builder.add_edge("execute_tool", "observe")
    builder.add_edge("observe", "decide")
    builder.add_edge("finish", END)
    return builder.compile(checkpointer=checkpointer, name="phase02_minimal_agent")
