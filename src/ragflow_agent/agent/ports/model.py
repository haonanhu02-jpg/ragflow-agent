"""Provider-neutral Agent model decision boundary."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from ragflow_agent.agent.domain.state import AgentMessage, ModelDecision
from ragflow_agent.agent.ports.tool import ToolSpec


@runtime_checkable
class AgentModelPort(Protocol):
    """Produce one structured decision without controlling graph execution."""

    async def decide(
        self,
        messages: Sequence[AgentMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelDecision: ...
