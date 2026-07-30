"""Deterministic Agent adapters used by Phase 02 tests."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Sequence

from ragflow_agent.agent.domain import (
    AgentAuthorizationContext,
    AgentRunIdentity,
    AgentTransientError,
    ModelDecision,
    ToolCall,
    ToolExecutionResult,
)
from ragflow_agent.agent.domain.state import AgentMessage
from ragflow_agent.agent.ports.tool import ToolSpec


def agent_identity(
    *,
    tenant_id: str = "tenant-a",
    thread_id: str = "thread-a",
    run_id: str = "run-a",
) -> AgentRunIdentity:
    return AgentRunIdentity(
        authorization=AgentAuthorizationContext(
            tenant_id=tenant_id,
            user_id="user-a",
            request_id=f"request-{run_id}",
        ),
        thread_id=thread_id,
        run_id=run_id,
        trace_id=f"trace-{run_id}",
    )


class ScriptedAgentModel:
    """Return a finite sequence of decisions or injected exceptions."""

    def __init__(self, outcomes: Sequence[ModelDecision | Exception]) -> None:
        self._outcomes = deque(outcomes)
        self.calls = 0

    async def decide(
        self,
        messages: Sequence[AgentMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelDecision:
        del messages, tools
        self.calls += 1
        if not self._outcomes:
            raise AssertionError("scripted model has no remaining outcome")
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class RepeatingToolModel:
    """Always request the same Tool to exercise the graph step limit."""

    async def decide(
        self,
        messages: Sequence[AgentMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelDecision:
        del messages
        if not tools:
            raise AssertionError("a registered Tool is required")
        return ModelDecision(
            kind="tool",
            tool_name=tools[0].name,
            tool_arguments={"value": "loop"},
        )


class FakeAgentTool:
    """Controllable Tool port with stable call tracking."""

    def __init__(
        self,
        *,
        name: str = "echo",
        output: object = "ok",
        transient_failures: int = 0,
        delay_seconds: float = 0,
    ) -> None:
        self._spec = ToolSpec(
            name=name,
            description="Deterministic side-effect-free test Tool.",
            input_schema={"type": "object"},
        )
        self._output = output
        self._transient_failures = transient_failures
        self._delay_seconds = delay_seconds
        self.calls: list[str] = []

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def invoke(
        self,
        call: ToolCall,
        identity: AgentRunIdentity,
    ) -> ToolExecutionResult:
        del identity
        self.calls.append(call.call_id)
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        if self._transient_failures:
            self._transient_failures -= 1
            raise AgentTransientError("temporary Tool failure")
        return ToolExecutionResult(
            call_id=call.call_id,
            name=call.name,
            status="success",
            output=self._output,
        )
