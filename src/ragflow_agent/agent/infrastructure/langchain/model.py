"""Adapt a LangChain ChatModel to the structured Agent decision port."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import cast

from langchain.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import Runnable

from ragflow_agent.agent.domain.errors import AgentModelError
from ragflow_agent.agent.domain.state import AgentMessage, ModelDecision
from ragflow_agent.agent.ports.tool import ToolSpec


class LangChainStructuredModelAdapter:
    """Use LangChain structured output without granting the model graph control."""

    def __init__(self, model: BaseChatModel) -> None:
        self._model = model
        self._structured: Runnable[object, object] = cast(
            Runnable[object, object],
            model.with_structured_output(ModelDecision),
        )

    async def decide(
        self,
        messages: Sequence[AgentMessage],
        tools: Sequence[ToolSpec],
    ) -> ModelDecision:
        prompt = [
            SystemMessage(
                content=(
                    "Return one Agent decision matching the required schema. "
                    "Available Tools: "
                    + json.dumps(
                        [tool.model_dump(mode="json") for tool in tools],
                        sort_keys=True,
                    )
                )
            ),
            *(_to_langchain(message) for message in messages),
        ]
        raw = await self._structured.ainvoke(prompt)
        try:
            return raw if isinstance(raw, ModelDecision) else ModelDecision.model_validate(raw)
        except (TypeError, ValueError) as exc:
            raise AgentModelError("model returned an invalid structured decision") from exc


def _to_langchain(message: AgentMessage) -> BaseMessage:
    if message.role == "system":
        return SystemMessage(content=message.content)
    if message.role == "user":
        return HumanMessage(content=message.content)
    if message.role == "assistant":
        return AIMessage(content=message.content)
    return ToolMessage(
        content=message.content,
        tool_call_id=message.tool_call_id or "",
        name=message.name,
    )
