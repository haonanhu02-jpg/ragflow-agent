"""Structured Tool contracts independent from LangChain implementation details."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.agent.domain.state import (
    AgentRunIdentity,
    ToolCall,
    ToolExecutionResult,
)


class ToolSpec(BaseModel):
    """Model-visible Tool metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    description: str
    input_schema: dict[str, object] = Field(default_factory=dict)


@runtime_checkable
class AgentToolPort(Protocol):
    """Execute one Tool call using a stable call identity."""

    @property
    def spec(self) -> ToolSpec: ...

    async def invoke(
        self,
        call: ToolCall,
        identity: AgentRunIdentity,
    ) -> ToolExecutionResult: ...


@runtime_checkable
class ToolPolicy(Protocol):
    """Authorize a registered Tool before execution."""

    def is_allowed(self, identity: AgentRunIdentity, tool: ToolSpec) -> bool: ...
