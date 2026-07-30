"""Adapt LangChain BaseTool to the project's structured Tool port."""

from __future__ import annotations

from langchain.tools import BaseTool
from pydantic import ValidationError

from ragflow_agent.agent.domain.errors import AgentTransientError
from ragflow_agent.agent.domain.state import (
    AgentRunIdentity,
    ToolCall,
    ToolExecutionResult,
)
from ragflow_agent.agent.ports.tool import ToolSpec


class LangChainToolAdapter:
    """Keep LangChain Tool mechanics behind the Agent Tool port."""

    def __init__(self, tool: BaseTool) -> None:
        self._tool = tool
        schema = tool.get_input_jsonschema()
        self._spec = ToolSpec(
            name=tool.name,
            description=tool.description,
            input_schema=schema,
        )

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    async def invoke(
        self,
        call: ToolCall,
        identity: AgentRunIdentity,
    ) -> ToolExecutionResult:
        del identity
        try:
            output = await self._tool.ainvoke(call.arguments)
            return ToolExecutionResult(
                call_id=call.call_id,
                name=call.name,
                status="success",
                output=_json_safe(output),
            )
        except ValidationError as exc:
            return ToolExecutionResult(
                call_id=call.call_id,
                name=call.name,
                status="error",
                error_code="agent_tool_input_invalid",
                error_message=str(exc),
            )
        except AgentTransientError:
            raise
        except Exception as exc:
            return ToolExecutionResult(
                call_id=call.call_id,
                name=call.name,
                status="error",
                error_code="agent_tool_execution_failed",
                error_message=type(exc).__name__,
            )


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)
