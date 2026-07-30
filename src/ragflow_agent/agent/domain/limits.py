"""Finite runtime limits and cooperative cancellation primitives."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from ragflow_agent.agent.domain.errors import AgentCancelledError


@dataclass(frozen=True, slots=True)
class RuntimeLimits:
    """Technical safety limits for Phase 02.

    Token, cost, and user-configurable business budgets remain Phase 08 scope.
    """

    graph_timeout_seconds: float = 30.0
    model_timeout_seconds: float = 10.0
    tool_timeout_seconds: float = 10.0
    max_attempts: int = 3
    retry_initial_seconds: float = 0.01
    retry_backoff_factor: float = 2.0
    max_graph_steps: int = 12

    def __post_init__(self) -> None:
        positive = (
            self.graph_timeout_seconds,
            self.model_timeout_seconds,
            self.tool_timeout_seconds,
            self.retry_initial_seconds,
            self.retry_backoff_factor,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("runtime timeouts and retry intervals must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.max_graph_steps < 2:
            raise ValueError("max_graph_steps must be at least two")


@dataclass(slots=True)
class CancellationToken:
    """Process-local cooperative cancellation token."""

    _event: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    _reason: str = field(default="cancelled by caller", init=False)

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def cancel(self, reason: str = "cancelled by caller") -> None:
        if not reason:
            raise ValueError("cancellation reason must not be empty")
        self._reason = reason
        self._event.set()

    async def wait(self) -> None:
        await self._event.wait()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise AgentCancelledError(self.reason)
