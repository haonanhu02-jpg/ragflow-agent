"""Pure-or-ported nodes for the Phase 02 minimal Agent graph."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from ragflow_agent.agent.application.control import current_execution_control
from ragflow_agent.agent.application.resilience import run_operation
from ragflow_agent.agent.application.tool_executor import ToolExecutor
from ragflow_agent.agent.domain.state import (
    AgentGraphState,
    AgentMessage,
    AgentState,
    ToolCall,
    graph_state_from_model,
    model_from_graph_state,
)
from ragflow_agent.agent.ports.model import AgentModelPort


@dataclass(frozen=True, slots=True)
class MinimalAgentNodes:
    """Dependency-injected node set; no concrete infrastructure imports."""

    model: AgentModelPort
    tools: ToolExecutor

    async def normalize_input(self, raw: AgentGraphState) -> AgentGraphState:
        state = model_from_graph_state(raw)
        return _updated(state, current_node="normalize_input")

    async def decide(self, raw: AgentGraphState) -> AgentGraphState:
        state = model_from_graph_state(raw)
        control = current_execution_control()
        outcome = await run_operation(
            "model_decision",
            lambda: self.model.decide(state.messages, self.tools.specs),
            timeout_seconds=control.limits.model_timeout_seconds,
            limits=control.limits,
            cancellation=control.cancellation,
        )
        decision = outcome.value
        common = {
            "current_node": "decide",
            "step_count": state.step_count + 1,
            "retry_count": state.retry_count + outcome.retries,
            "event_sequence": state.event_sequence + 1,
        }
        if decision.kind == "final":
            return _updated(
                state,
                **common,
                route="final",
                pending_tool_call=None,
                final_answer=decision.content,
            )
        call = ToolCall(
            call_id=_stable_call_id(state, decision.tool_name or "", decision.tool_arguments),
            name=decision.tool_name or "",
            arguments=decision.tool_arguments,
        )
        return _updated(
            state,
            **common,
            route="tool",
            pending_tool_call=call,
        )

    async def execute_tool(self, raw: AgentGraphState) -> AgentGraphState:
        state = model_from_graph_state(raw)
        call = state.pending_tool_call
        if call is None:
            raise ValueError("execute_tool requires pending_tool_call")
        control = current_execution_control()
        outcome = await run_operation(
            "tool_execution",
            lambda: self.tools.execute(call, state.identity, state.tool_results),
            timeout_seconds=control.limits.tool_timeout_seconds,
            limits=control.limits,
            cancellation=control.cancellation,
        )
        return _updated(
            state,
            current_node="execute_tool",
            tool_results=(*state.tool_results, outcome.value),
            step_count=state.step_count + 1,
            retry_count=state.retry_count + outcome.retries,
            event_sequence=state.event_sequence + 1,
        )

    async def observe(self, raw: AgentGraphState) -> AgentGraphState:
        state = model_from_graph_state(raw)
        if not state.tool_results:
            raise ValueError("observe requires a Tool result")
        result = state.tool_results[-1]
        content = json.dumps(result.model_dump(mode="json"), sort_keys=True)
        message = AgentMessage(
            role="tool",
            name=result.name,
            tool_call_id=result.call_id,
            content=content,
        )
        return _updated(
            state,
            current_node="observe",
            messages=(*state.messages, message),
            route="undecided",
            pending_tool_call=None,
            step_count=state.step_count + 1,
            event_sequence=state.event_sequence + 1,
        )

    async def finish(self, raw: AgentGraphState) -> AgentGraphState:
        state = model_from_graph_state(raw)
        if not state.final_answer:
            raise ValueError("finish requires final_answer")
        final_message = AgentMessage(role="assistant", content=state.final_answer)
        return _updated(
            state,
            current_node="finish",
            messages=(*state.messages, final_message),
            termination_reason="completed",
            step_count=state.step_count + 1,
            event_sequence=state.event_sequence + 1,
        )


def decision_route(raw: AgentGraphState) -> str:
    state = model_from_graph_state(raw)
    return "execute_tool" if state.route == "tool" else "finish"


def _updated(state: AgentState, **updates: object) -> AgentGraphState:
    return graph_state_from_model(state.model_copy(update=updates))


def _stable_call_id(
    state: AgentState,
    tool_name: str,
    arguments: dict[str, object],
) -> str:
    material = json.dumps(
        {
            "run_id": state.identity.run_id,
            "step": state.step_count,
            "tool": tool_name,
            "arguments": arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()[:32]
