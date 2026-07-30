"""Deterministic input -> Tool -> observation -> answer Agent E2E."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ragflow_agent.agent.application.runtime import AgentRuntime
from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import AgentEventType, AgentRunRequest, ModelDecision
from ragflow_agent.agent.infrastructure.checkpoint import TenantScopedCheckpointStore
from ragflow_agent.agent.infrastructure.trace import InMemoryTraceSink
from tests.fakes.agent import FakeAgentTool, ScriptedAgentModel, agent_identity


@pytest.mark.asyncio
async def test_minimal_agent_tool_loop_is_deterministic() -> None:
    model = ScriptedAgentModel(
        [
            ModelDecision(
                kind="tool",
                tool_name="inspect_status",
                tool_arguments={"asset_id": "train-01"},
            ),
            ModelDecision(kind="final", content="train-01 is nominal"),
        ]
    )
    tool_adapter = FakeAgentTool(
        name="inspect_status",
        output={"asset_id": "train-01", "status": "nominal"},
    )
    sink = InMemoryTraceSink()
    store = TenantScopedCheckpointStore(InMemorySaver())
    runtime = AgentRuntime(
        model=model,
        tools=ToolExecutor(
            ToolRegistry(
                [tool_adapter],
                AllowListToolPolicy(["inspect_status"]),
            )
        ),
        checkpoints=store,
        trace_sink=sink,
    )
    identity = agent_identity(thread_id="e2e-thread", run_id="e2e-run")

    result = await runtime.run(
        AgentRunRequest(identity=identity, user_input="inspect train-01")
    )

    restored = await store.load(identity)
    event_types = [event.event_type for event in sink.events]
    assert result.answer == "train-01 is nominal"
    assert result.state.termination_reason == "completed"
    assert restored == result.state
    assert len(tool_adapter.calls) == 1
    assert AgentEventType.TOOL_COMPLETED in event_types
    assert event_types[-1] == AgentEventType.RUN_COMPLETED
