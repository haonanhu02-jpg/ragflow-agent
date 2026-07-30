"""Trace sink boundary separating event production from storage/transport."""

from typing import Protocol, runtime_checkable

from ragflow_agent.agent.domain.events import AgentEvent


@runtime_checkable
class AgentTraceSink(Protocol):
    async def emit(self, event: AgentEvent) -> None: ...
