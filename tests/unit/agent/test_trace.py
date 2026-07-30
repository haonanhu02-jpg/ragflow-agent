"""Agent event ordering, redaction, and degraded-sink behavior."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ragflow_agent.agent.application.runtime import AgentRuntime
from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import AgentEvent, AgentEventType, AgentRunRequest, ModelDecision
from ragflow_agent.agent.domain.events import REDACTED
from ragflow_agent.agent.infrastructure.checkpoint import TenantScopedCheckpointStore
from ragflow_agent.agent.infrastructure.trace import FailingTraceSink, InMemoryTraceSink
from tests.fakes.agent import FakeAgentTool, ScriptedAgentModel, agent_identity


def _runtime(trace_sink: InMemoryTraceSink | FailingTraceSink) -> AgentRuntime:
    tool_adapter = FakeAgentTool()
    return AgentRuntime(
        model=ScriptedAgentModel([ModelDecision(kind="final", content="done")]),
        tools=ToolExecutor(
            ToolRegistry([tool_adapter], AllowListToolPolicy([tool_adapter.spec.name]))
        ),
        checkpoints=TenantScopedCheckpointStore(InMemorySaver()),
        trace_sink=trace_sink,
    )


def test_event_payload_is_recursively_redacted() -> None:
    identity = agent_identity()
    event = AgentEvent.create(
        AgentEventType.NODE_COMPLETED,
        identity,
        sequence=1,
        payload={
            "api_key": "secret-value",
            "nested": {"token": "secret-token", "safe": "visible"},
        },
    )

    assert event.payload["api_key"] == REDACTED
    assert event.payload["nested"] == {"token": REDACTED, "safe": "visible"}
    assert "secret-value" not in event.model_dump_json()


@pytest.mark.asyncio
async def test_trace_reconstructs_node_path_and_correlation() -> None:
    sink = InMemoryTraceSink()

    result = await _runtime(sink).run(
        AgentRunRequest(identity=agent_identity(), user_input="answer")
    )

    sequences = [event.sequence for event in sink.events]
    node_path = [
        event.node for event in sink.events if event.event_type == AgentEventType.NODE_COMPLETED
    ]
    assert result.trace_degraded is False
    assert sequences == sorted(sequences)
    assert len(sequences) == len(set(sequences))
    assert node_path == ["normalize_input", "decide", "finish"]
    assert {event.trace_id for event in sink.events} == {"trace-run-a"}


@pytest.mark.asyncio
async def test_trace_sink_failure_is_explicitly_degraded() -> None:
    result = await _runtime(FailingTraceSink()).run(
        AgentRunRequest(identity=agent_identity(), user_input="answer")
    )

    assert result.answer == "done"
    assert result.trace_degraded is True
