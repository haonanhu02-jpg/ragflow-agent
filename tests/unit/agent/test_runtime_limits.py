"""Retry, timeout, cancellation, and graph safety limits."""

import asyncio

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ragflow_agent.agent.application.resilience import run_operation
from ragflow_agent.agent.application.runtime import AgentRuntime
from ragflow_agent.agent.application.tool_executor import (
    AllowListToolPolicy,
    ToolExecutor,
    ToolRegistry,
)
from ragflow_agent.agent.domain import (
    AgentCancelledError,
    AgentRetryExhaustedError,
    AgentRunRequest,
    AgentStepLimitError,
    AgentTimeoutError,
    AgentTransientError,
    CancellationToken,
    RuntimeLimits,
)
from ragflow_agent.agent.infrastructure.checkpoint import TenantScopedCheckpointStore
from ragflow_agent.agent.infrastructure.trace import InMemoryTraceSink
from tests.fakes.agent import FakeAgentTool, RepeatingToolModel, agent_identity


@pytest.mark.asyncio
async def test_transient_operation_retries_then_succeeds() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise AgentTransientError("not yet")
        return "ok"

    result = await run_operation(
        "test_operation",
        operation,
        timeout_seconds=1,
        limits=RuntimeLimits(max_attempts=3),
        cancellation=CancellationToken(),
    )

    assert result.value == "ok"
    assert result.retries == 2


@pytest.mark.asyncio
async def test_retry_exhaustion_has_stable_error() -> None:
    async def operation() -> str:
        raise AgentTransientError("still failing")

    with pytest.raises(AgentRetryExhaustedError) as captured:
        await run_operation(
            "test_operation",
            operation,
            timeout_seconds=1,
            limits=RuntimeLimits(max_attempts=2),
            cancellation=CancellationToken(),
        )

    assert captured.value.error_code == "agent_retry_exhausted"
    assert captured.value.details["attempts"] == 2


@pytest.mark.asyncio
async def test_operation_timeout_terminates_task() -> None:
    async def operation() -> str:
        await asyncio.sleep(1)
        return "late"

    with pytest.raises(AgentTimeoutError):
        await run_operation(
            "slow",
            operation,
            timeout_seconds=0.01,
            limits=RuntimeLimits(),
            cancellation=CancellationToken(),
        )


@pytest.mark.asyncio
async def test_cancellation_terminates_in_flight_operation() -> None:
    token = CancellationToken()

    async def operation() -> str:
        await asyncio.sleep(1)
        return "late"

    async def cancel() -> None:
        await asyncio.sleep(0.01)
        token.cancel("test cancellation")

    cancel_task = asyncio.create_task(cancel())
    with pytest.raises(AgentCancelledError) as captured:
        await run_operation(
            "cancelled",
            operation,
            timeout_seconds=1,
            limits=RuntimeLimits(),
            cancellation=token,
        )
    await cancel_task

    assert captured.value.details["reason"] == "test cancellation"


@pytest.mark.asyncio
async def test_graph_loop_is_stopped_by_finite_recursion_limit() -> None:
    tool_adapter = FakeAgentTool()
    executor = ToolExecutor(
        ToolRegistry([tool_adapter], AllowListToolPolicy([tool_adapter.spec.name]))
    )
    runtime = AgentRuntime(
        model=RepeatingToolModel(),
        tools=executor,
        checkpoints=TenantScopedCheckpointStore(InMemorySaver()),
        trace_sink=InMemoryTraceSink(),
        limits=RuntimeLimits(max_graph_steps=6),
    )

    with pytest.raises(AgentStepLimitError):
        await runtime.run(AgentRunRequest(identity=agent_identity(), user_input="loop"))
