"""Deterministic trace sinks for tests and local composition."""

from __future__ import annotations

import asyncio

from ragflow_agent.agent.domain.events import AgentEvent


class InMemoryTraceSink:
    """Concurrent-safe event collector; not a production persistence claim."""

    def __init__(self) -> None:
        self._events: list[AgentEvent] = []
        self._lock = asyncio.Lock()

    @property
    def events(self) -> tuple[AgentEvent, ...]:
        return tuple(self._events)

    async def emit(self, event: AgentEvent) -> None:
        async with self._lock:
            self._events.append(event)


class FailingTraceSink:
    """Fault-injection sink."""

    async def emit(self, event: AgentEvent) -> None:
        del event
        raise RuntimeError("trace sink unavailable")
