"""Tool registry, policy enforcement, and duplicate-call protection."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.domain.state import (
    AgentRunIdentity,
    ToolCall,
    ToolExecutionResult,
)
from ragflow_agent.agent.ports.tool import AgentToolPort, ToolPolicy, ToolSpec


class AllowListToolPolicy:
    """Explicit allowlist; an empty set denies every Tool."""

    def __init__(self, allowed_names: Iterable[str]) -> None:
        self._allowed_names = frozenset(allowed_names)

    def is_allowed(self, identity: AgentRunIdentity, tool: ToolSpec) -> bool:
        del identity
        return tool.name in self._allowed_names


class ToolRegistry:
    """Unique Tool registry that never permits model-selected bypasses."""

    def __init__(self, tools: Iterable[AgentToolPort], policy: ToolPolicy) -> None:
        registered: dict[str, AgentToolPort] = {}
        for tool in tools:
            if tool.spec.name in registered:
                raise ValueError(f"duplicate Tool name: {tool.spec.name}")
            registered[tool.spec.name] = tool
        self._tools = registered
        self._policy = policy

    @property
    def specs(self) -> tuple[ToolSpec, ...]:
        return tuple(tool.spec for tool in self._tools.values())

    def resolve(self, name: str, identity: AgentRunIdentity) -> AgentToolPort:
        tool = self._tools.get(name)
        if tool is None:
            raise AgentToolError(
                "model selected an unknown Tool",
                error_code="agent_tool_unknown",
                details={"tool_name": name},
            )
        if not self._policy.is_allowed(identity, tool.spec):
            raise AgentToolError(
                "Tool is not allowed for this run",
                error_code="agent_tool_forbidden",
                status_code=403,
                details={"tool_name": name},
            )
        return tool


class ToolExecutor:
    """Execute registered Tools and reuse already checkpointed call results."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    @property
    def specs(self) -> tuple[ToolSpec, ...]:
        return self._registry.specs

    async def execute(
        self,
        call: ToolCall,
        identity: AgentRunIdentity,
        prior_results: Sequence[ToolExecutionResult],
    ) -> ToolExecutionResult:
        existing = next((item for item in prior_results if item.call_id == call.call_id), None)
        if existing is not None:
            if existing.name != call.name:
                raise AgentToolError(
                    "Tool call identity collision",
                    error_code="agent_tool_call_collision",
                )
            return existing
        tool = self._registry.resolve(call.name, identity)
        return await tool.invoke(call, identity)
