"""Structured query transformations built on the internal chat provider."""

from __future__ import annotations

import json

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.ports.generation import (
    ChatGenerationRequest,
    ChatProviderPort,
    QueryTransformKind,
    QueryTransformRequest,
    QueryTransformResult,
)


class ChatQueryTransformProvider:
    """Use one supplier-isolated chat provider and require strict JSON output."""

    def __init__(self, chat: ChatProviderPort, *, model_id: str) -> None:
        self._chat = chat
        self._model_id = model_id

    async def transform(
        self,
        context: AuthorizationContext,
        request: QueryTransformRequest,
    ) -> QueryTransformResult:
        if request.model_id != self._model_id:
            raise KnowledgeConflictError(
                "query transform model does not match configured provider",
                error_code="query_transform_model_mismatch",
            )
        instructions = {
            QueryTransformKind.REWRITE: (
                "Rewrite the last question as one standalone question. Preserve meaning and "
                'proper nouns. Return JSON only: {"items":["question"]}.'
            ),
            QueryTransformKind.TRANSLATE: (
                "Translate the query into each requested language while preserving identifiers. "
                'Return JSON only: {"items":["translation"]}.'
            ),
            QueryTransformKind.KEYWORDS: (
                "Extract concise retrieval keywords and identifiers. Return JSON only: "
                '{"items":["keyword"]}.'
            ),
        }[request.kind]
        result = await self._chat.generate(
            context,
            ChatGenerationRequest(
                model_id=request.model_id,
                system_prompt=instructions,
                user_prompt=json.dumps(
                    {
                        "query": request.query,
                        "history": request.history,
                        "target_languages": request.target_languages,
                        "max_items": request.max_items,
                    },
                    ensure_ascii=False,
                ),
                trace_id=request.trace_id,
            ),
        )
        try:
            payload = json.loads(result.content)
            raw_items = payload["items"]
            if not isinstance(raw_items, list):
                raise TypeError("items must be a list")
            items = tuple(
                dict.fromkeys(
                    item.strip() for item in raw_items if isinstance(item, str) and item.strip()
                )
            )[: request.max_items]
        except (json.JSONDecodeError, KeyError, TypeError) as error:
            raise KnowledgeConflictError(
                "query transform provider returned invalid structured output",
                error_code="query_transform_invalid_result",
            ) from error
        return QueryTransformResult(model_id=result.model_id, items=items)
