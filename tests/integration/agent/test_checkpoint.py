"""Real PostgreSQL Checkpointer persistence and tenant scope tests."""

import asyncio

import pytest

from ragflow_agent.agent.application.runtime import AgentRuntime
from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import AgentRunRequest, ModelDecision
from ragflow_agent.agent.infrastructure.checkpoint import open_postgres_checkpoint_store
from ragflow_agent.agent.infrastructure.trace import InMemoryTraceSink
from tests.fakes.agent import FakeAgentTool, ScriptedAgentModel, agent_identity
from tests.integration.agent.helpers import checkpoint_database_url


def _runtime(store: object, answer: str) -> AgentRuntime:
    tool_adapter = FakeAgentTool()
    return AgentRuntime(
        model=ScriptedAgentModel([ModelDecision(kind="final", content=answer)]),
        tools=ToolExecutor(
            ToolRegistry([tool_adapter], AllowListToolPolicy([tool_adapter.spec.name]))
        ),
        checkpoints=store,  # type: ignore[arg-type]
        trace_sink=InMemoryTraceSink(),
    )


@pytest.mark.asyncio
async def test_postgres_checkpoint_survives_runtime_reconstruction() -> None:
    identity = agent_identity(thread_id="postgres-thread", run_id="postgres-run")
    async with open_postgres_checkpoint_store(checkpoint_database_url()) as store:
        await store.delete(identity)
        result = await _runtime(store, "durable").run(
            AgentRunRequest(identity=identity, user_input="persist")
        )

        reconstructed = await store.load(identity)
        checkpoint_ids = await store.list_checkpoint_ids(identity)

        assert reconstructed == result.state
        assert checkpoint_ids
        await store.delete(identity)
        assert await store.load(identity) is None


@pytest.mark.asyncio
async def test_postgres_checkpoint_keys_isolate_tenants_and_threads() -> None:
    identity_a = agent_identity(
        tenant_id="tenant-a",
        thread_id="shared-logical-thread",
        run_id="run-a-postgres",
    )
    identity_b = agent_identity(
        tenant_id="tenant-b",
        thread_id="shared-logical-thread",
        run_id="run-b-postgres",
    )
    async with open_postgres_checkpoint_store(checkpoint_database_url()) as store:
        await store.delete(identity_a)
        await store.delete(identity_b)
        await asyncio.gather(
            _runtime(store, "answer-a").run(
                AgentRunRequest(identity=identity_a, user_input="a")
            ),
            _runtime(store, "answer-b").run(
                AgentRunRequest(identity=identity_b, user_input="b")
            ),
        )

        state_a = await store.load(identity_a)
        state_b = await store.load(identity_b)
        assert state_a is not None and state_a.final_answer == "answer-a"
        assert state_b is not None and state_b.final_answer == "answer-b"
        assert store.config(identity_a) != store.config(identity_b)
        await store.delete(identity_a)
        await store.delete(identity_b)
