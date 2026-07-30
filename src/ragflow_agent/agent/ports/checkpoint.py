"""Tenant-scoped Checkpointer boundary consumed by AgentRuntime."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from ragflow_agent.agent.domain.state import AgentRunIdentity, AgentState


@runtime_checkable
class AgentCheckpointStore(Protocol):
    """Expose the official LangGraph saver through a tenant-safe facade."""

    @property
    def checkpointer(self) -> BaseCheckpointSaver[str]: ...

    def config(self, identity: AgentRunIdentity) -> RunnableConfig: ...

    async def load(self, identity: AgentRunIdentity) -> AgentState | None: ...

    async def list_checkpoint_ids(self, identity: AgentRunIdentity) -> tuple[str, ...]: ...

    async def delete(self, identity: AgentRunIdentity) -> None: ...
