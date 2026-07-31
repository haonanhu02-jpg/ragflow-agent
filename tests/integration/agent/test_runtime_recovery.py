"""Fault injection for persistent recovery, retries, and trace continuity."""

import pytest

from ragflow_agent.agent.application.runtime import AgentRuntime
from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import (
    AgentCheckpointError,
    AgentResumeRequest,
    AgentResumeToken,
    AgentRetryExhaustedError,
    AgentRunRequest,
    ModelDecision,
    RuntimeLimits,
)
from ragflow_agent.agent.infrastructure.checkpoint import open_postgres_checkpoint_store
from ragflow_agent.agent.infrastructure.trace import InMemoryTraceSink
from tests.fakes.agent import FakeAgentTool, ScriptedAgentModel, agent_identity
from tests.integration.agent.helpers import checkpoint_database_url


def _runtime(
    store: object,
    *,
    model: ScriptedAgentModel,
    tool_adapter: FakeAgentTool,
    sink: InMemoryTraceSink,
) -> AgentRuntime:
    return AgentRuntime(
        model=model,
        tools=ToolExecutor(
            ToolRegistry(
                [tool_adapter],
                AllowListToolPolicy([tool_adapter.spec.name]),
            )
        ),
        checkpoints=store,  # type: ignore[arg-type]
        trace_sink=sink,
        limits=RuntimeLimits(max_attempts=2),
    )


@pytest.mark.asyncio
async def test_failed_tool_node_resumes_after_process_reconstruction() -> None:
    identity = agent_identity(thread_id="recovery-thread", run_id="recovery-run")
    token = AgentResumeToken.from_identity(identity)
    first_sink = InMemoryTraceSink()
    second_sink = InMemoryTraceSink()
    failing_tool = FakeAgentTool(name="recoverable", transient_failures=99)
    healthy_tool = FakeAgentTool(name="recoverable", output={"recovered": True})

    async with open_postgres_checkpoint_store(checkpoint_database_url()) as store:
        await store.delete(identity)
        first_runtime = _runtime(
            store,
            model=ScriptedAgentModel([ModelDecision(kind="tool", tool_name="recoverable")]),
            tool_adapter=failing_tool,
            sink=first_sink,
        )
        with pytest.raises(AgentRetryExhaustedError):
            await first_runtime.run(AgentRunRequest(identity=identity, user_input="recover"))

        failed_state = await store.load(identity)
        assert failed_state is not None
        assert failed_state.current_node == "decide"

        reconstructed_runtime = _runtime(
            store,
            model=ScriptedAgentModel([ModelDecision(kind="final", content="recovered answer")]),
            tool_adapter=healthy_tool,
            sink=second_sink,
        )
        result = await reconstructed_runtime.resume(
            AgentResumeRequest(identity=identity, resume_token=token)
        )
        repeated = await reconstructed_runtime.resume(
            AgentResumeRequest(identity=identity, resume_token=token)
        )

        assert result.answer == "recovered answer"
        assert repeated.answer == result.answer
        assert len(healthy_tool.calls) == 1
        assert {event.trace_id for event in (*first_sink.events, *second_sink.events)} == {
            identity.trace_id
        }
        await store.delete(identity)


def test_cross_tenant_resume_token_fails_closed() -> None:
    owner = agent_identity(tenant_id="tenant-a")
    attacker = agent_identity(tenant_id="tenant-b")

    with pytest.raises(AgentCheckpointError, match="does not own"):
        AgentResumeRequest(
            identity=attacker,
            resume_token=AgentResumeToken.from_identity(owner),
        )
