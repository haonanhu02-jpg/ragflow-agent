"""Context-local execution control propagated into LangGraph node tasks."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from ragflow_agent.agent.domain.limits import CancellationToken, RuntimeLimits


@dataclass(frozen=True, slots=True)
class ExecutionControl:
    limits: RuntimeLimits
    cancellation: CancellationToken


_EXECUTION_CONTROL: ContextVar[ExecutionControl | None] = ContextVar(
    "agent_execution_control",
    default=None,
)


def current_execution_control() -> ExecutionControl:
    control = _EXECUTION_CONTROL.get()
    if control is None:
        return ExecutionControl(RuntimeLimits(), CancellationToken())
    return control


@contextmanager
def use_execution_control(control: ExecutionControl) -> Iterator[ExecutionControl]:
    reset_handle = _EXECUTION_CONTROL.set(control)
    try:
        yield control
    finally:
        _EXECUTION_CONTROL.reset(reset_handle)
