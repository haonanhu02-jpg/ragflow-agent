"""Agent runtime coordinating LangGraph, checkpoints, controls, and trace."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import cast

from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph

from ragflow_agent.agent.application.control import ExecutionControl, use_execution_control
from ragflow_agent.agent.application.tool_executor import ToolExecutor
from ragflow_agent.agent.domain.errors import (
    AgentCancelledError,
    AgentCheckpointError,
    AgentError,
    AgentStepLimitError,
    AgentTimeoutError,
)
from ragflow_agent.agent.domain.events import AgentEvent, AgentEventType
from ragflow_agent.agent.domain.limits import CancellationToken, RuntimeLimits
from ragflow_agent.agent.domain.state import (
    AgentGraphState,
    AgentResumeRequest,
    AgentRunIdentity,
    AgentRunRequest,
    AgentRunResult,
    AgentState,
    graph_state_from_model,
    model_from_graph_state,
)
from ragflow_agent.agent.graphs.minimal_agent import build_minimal_agent_graph
from ragflow_agent.agent.nodes.minimal import MinimalAgentNodes
from ragflow_agent.agent.ports.checkpoint import AgentCheckpointStore
from ragflow_agent.agent.ports.model import AgentModelPort
from ragflow_agent.agent.ports.trace import AgentTraceSink

LOGGER = logging.getLogger("ragflow_agent.agent.runtime")


class AgentRuntime:
    """Run or resume the minimal Agent with durable LangGraph checkpoints."""

    def __init__(
        self,
        *,
        model: AgentModelPort,
        tools: ToolExecutor,
        checkpoints: AgentCheckpointStore,
        trace_sink: AgentTraceSink,
        limits: RuntimeLimits | None = None,
    ) -> None:
        self._limits = limits or RuntimeLimits()
        self._checkpoints = checkpoints
        self._trace_sink = trace_sink
        self._graph: CompiledStateGraph[
            AgentGraphState,
            None,
            AgentGraphState,
            AgentGraphState,
        ] = build_minimal_agent_graph(
            MinimalAgentNodes(model=model, tools=tools),
            checkpoints.checkpointer,
            self._limits,
        )

    async def run(
        self,
        request: AgentRunRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> AgentRunResult:
        existing = await self._checkpoints.load(request.identity)
        if existing is not None:
            raise AgentCheckpointError(
                "thread already has a checkpoint; use resume",
                error_code="agent_checkpoint_already_exists",
            )
        initial = AgentState.initial(request.identity, request.user_input)
        return await self._execute(
            identity=request.identity,
            graph_input=graph_state_from_model(initial),
            start_event=AgentEventType.RUN_STARTED,
            initial_sequence=initial.event_sequence,
            cancellation=cancellation,
        )

    async def resume(
        self,
        request: AgentResumeRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> AgentRunResult:
        request.resume_token.validate_identity(request.identity)
        restored = await self._checkpoints.load(request.identity)
        if restored is None:
            raise AgentCheckpointError(
                "no checkpoint exists for this run",
                error_code="agent_checkpoint_not_found",
            )
        return await self._execute(
            identity=request.identity,
            graph_input=None,
            start_event=AgentEventType.RUN_RESUMED,
            initial_sequence=restored.event_sequence,
            cancellation=cancellation,
        )

    async def _execute(
        self,
        *,
        identity: AgentRunIdentity,
        graph_input: AgentGraphState | None,
        start_event: AgentEventType,
        initial_sequence: int,
        cancellation: CancellationToken | None,
    ) -> AgentRunResult:
        cancellation_token = cancellation or CancellationToken()
        publisher = _TracePublisher(self._trace_sink, identity, initial_sequence)
        await publisher.emit(start_event)
        config = self._checkpoints.config(identity)
        config["recursion_limit"] = self._limits.max_graph_steps
        control = ExecutionControl(limits=self._limits, cancellation=cancellation_token)
        try:
            cancellation_token.raise_if_cancelled()
            with use_execution_control(control):
                async with asyncio.timeout(self._limits.graph_timeout_seconds):
                    async for update in self._graph.astream(
                        graph_input,
                        config,
                        stream_mode="updates",
                    ):
                        cancellation_token.raise_if_cancelled()
                        await self._publish_update(publisher, update)
        except TimeoutError as exc:
            error = AgentTimeoutError(
                "agent_graph",
                self._limits.graph_timeout_seconds,
            )
            await publisher.emit(
                AgentEventType.RUN_FAILED,
                payload={"error_code": error.error_code},
            )
            raise error from exc
        except GraphRecursionError as exc:
            step_error = AgentStepLimitError(self._limits.max_graph_steps)
            await publisher.emit(
                AgentEventType.RUN_FAILED,
                payload={"error_code": step_error.error_code},
            )
            raise step_error from exc
        except AgentCancelledError:
            await publisher.emit(AgentEventType.RUN_CANCELLED)
            raise
        except AgentError as exc:
            await publisher.emit(
                AgentEventType.RUN_FAILED,
                payload={"error_code": exc.error_code},
            )
            raise

        snapshot = await self._graph.aget_state(config)
        values = _as_mapping(snapshot.values)
        state = model_from_graph_state(values)
        _validate_result_identity(identity, state)
        if state.termination_reason != "completed":
            raise AgentCheckpointError("graph terminated without a completed state")
        await publisher.emit(
            AgentEventType.RUN_COMPLETED,
            node=state.current_node,
            payload={"step_count": state.step_count, "retry_count": state.retry_count},
        )
        return AgentRunResult(state=state, trace_degraded=publisher.degraded)

    async def _publish_update(
        self,
        publisher: _TracePublisher,
        update: object,
    ) -> None:
        if not isinstance(update, Mapping):
            return
        for raw_node, raw_state in update.items():
            if not isinstance(raw_node, str) or not isinstance(raw_state, Mapping):
                continue
            state = model_from_graph_state(_as_mapping(raw_state))
            await publisher.emit(
                AgentEventType.NODE_COMPLETED,
                node=raw_node,
                payload={
                    "route": state.route,
                    "step_count": state.step_count,
                    "retry_count": state.retry_count,
                },
                minimum_sequence=state.event_sequence,
            )
            if raw_node == "decide":
                await publisher.emit(
                    AgentEventType.MODEL_COMPLETED,
                    node=raw_node,
                    payload={
                        "decision": state.route,
                        "tool_name": (
                            state.pending_tool_call.name if state.pending_tool_call else None
                        ),
                    },
                )
            elif raw_node == "execute_tool" and state.tool_results:
                result = state.tool_results[-1]
                await publisher.emit(
                    AgentEventType.TOOL_COMPLETED,
                    node=raw_node,
                    payload={"tool_name": result.name, "status": result.status},
                )


class _TracePublisher:
    def __init__(
        self,
        sink: AgentTraceSink,
        identity: AgentRunIdentity,
        initial_sequence: int,
    ) -> None:
        self._sink = sink
        self._identity = identity
        self._sequence = initial_sequence
        self.degraded = False

    async def emit(
        self,
        event_type: AgentEventType,
        *,
        node: str | None = None,
        payload: Mapping[str, object] | None = None,
        minimum_sequence: int | None = None,
    ) -> None:
        self._sequence = max(self._sequence + 1, minimum_sequence or 0)
        event = AgentEvent.create(
            event_type,
            self._identity,
            sequence=self._sequence,
            node=node,
            payload=payload,
        )
        try:
            await self._sink.emit(event)
        except Exception:
            self.degraded = True
            LOGGER.exception(
                "Agent trace sink failed",
                extra={
                    "trace_id": self._identity.trace_id,
                    "tenant_id": self._identity.authorization.tenant_id,
                    "run_id": self._identity.run_id,
                    "event_type": event_type.value,
                },
            )


def _as_mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AgentCheckpointError("graph returned a non-mapping state")
    return cast(Mapping[str, object], value)


def _validate_result_identity(expected: AgentRunIdentity, state: AgentState) -> None:
    actual = state.identity
    if (
        actual.authorization.tenant_id != expected.authorization.tenant_id
        or actual.thread_id != expected.thread_id
        or actual.run_id != expected.run_id
    ):
        raise AgentCheckpointError(
            "graph result identity changed during execution",
            error_code="agent_checkpoint_access_denied",
        )
