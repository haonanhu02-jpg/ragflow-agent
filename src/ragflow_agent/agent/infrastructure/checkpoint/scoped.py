"""Tenant-scoped facade over the official LangGraph Checkpointer protocol."""

from __future__ import annotations

from urllib.parse import quote

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver

from ragflow_agent.agent.domain.errors import AgentCheckpointError
from ragflow_agent.agent.domain.state import (
    AgentRunIdentity,
    AgentState,
    checkpoint_fields,
    model_from_graph_state,
)

CHECKPOINT_NAMESPACE = "ragflow-agent:agent-state:v1"
AGENTIC_CHECKPOINT_NAMESPACE = "ragflow-agent:agentic-rag:v1"


class TenantScopedCheckpointStore:
    """Map logical thread IDs to tenant-qualified physical Checkpointer keys."""

    def __init__(self, checkpointer: BaseCheckpointSaver[str]) -> None:
        self._checkpointer = checkpointer

    @property
    def checkpointer(self) -> BaseCheckpointSaver[str]:
        return self._checkpointer

    def config(self, identity: AgentRunIdentity) -> RunnableConfig:
        return {
            "configurable": {
                "thread_id": _storage_thread_id(identity),
            }
        }

    async def load(self, identity: AgentRunIdentity) -> AgentState | None:
        checkpoint_tuple = await self._checkpointer.aget_tuple(self.config(identity))
        if checkpoint_tuple is None:
            return None
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        if not isinstance(channel_values, dict):
            raise AgentCheckpointError("checkpoint channel values are invalid")
        state = model_from_graph_state(checkpoint_fields(channel_values))
        _validate_owner(identity, state)
        return state

    async def list_checkpoint_ids(self, identity: AgentRunIdentity) -> tuple[str, ...]:
        checkpoint_ids: list[str] = []
        async for item in self._checkpointer.alist(self.config(identity)):
            checkpoint_id = item.config.get("configurable", {}).get("checkpoint_id")
            if isinstance(checkpoint_id, str):
                checkpoint_ids.append(checkpoint_id)
        return tuple(checkpoint_ids)

    async def delete(self, identity: AgentRunIdentity) -> None:
        state = await self.load(identity)
        if state is not None:
            _validate_owner(identity, state)
        await self._checkpointer.adelete_thread(_storage_thread_id(identity))


def _storage_thread_id(identity: AgentRunIdentity) -> str:
    tenant_id = quote(identity.authorization.tenant_id, safe="")
    thread_id = quote(identity.thread_id, safe="")
    return f"{CHECKPOINT_NAMESPACE}/tenant/{tenant_id}/thread/{thread_id}"


def agentic_checkpoint_config(*, tenant_id: str, thread_id: str) -> RunnableConfig:
    """Create a physically isolated tenant/thread key for Agentic RAG state."""
    tenant = quote(tenant_id, safe="")
    thread = quote(thread_id, safe="")
    return {
        "configurable": {
            "thread_id": f"{AGENTIC_CHECKPOINT_NAMESPACE}/tenant/{tenant}/thread/{thread}"
        }
    }


def _validate_owner(expected: AgentRunIdentity, state: AgentState) -> None:
    actual = state.identity
    if (
        actual.authorization.tenant_id != expected.authorization.tenant_id
        or actual.thread_id != expected.thread_id
        or actual.run_id != expected.run_id
    ):
        raise AgentCheckpointError(
            "checkpoint identity does not match the requested run",
            error_code="agent_checkpoint_access_denied",
        )
