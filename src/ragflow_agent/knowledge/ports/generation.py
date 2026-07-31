"""Provider-neutral fixed-answer generation boundary."""

from enum import StrEnum
from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class ChatGenerationRequest(KnowledgeModel):
    """Versioned prompt passed to an isolated chat provider."""

    model_id: NonEmptyStr
    system_prompt: NonEmptyStr
    user_prompt: NonEmptyStr
    trace_id: NonEmptyStr


class ChatGenerationResult(KnowledgeModel):
    """Provider-neutral answer and model identity."""

    model_id: NonEmptyStr
    content: NonEmptyStr
    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class ChatProviderPort(Protocol):
    """Generate a fixed-RAG answer without exposing a supplier SDK."""

    async def generate(
        self,
        context: AuthorizationContext,
        request: ChatGenerationRequest,
    ) -> ChatGenerationResult: ...


class QueryTransformKind(StrEnum):
    """Supported structured query transformations."""

    REWRITE = "rewrite"
    TRANSLATE = "translate"
    KEYWORDS = "keywords"


class QueryTransformRequest(KnowledgeModel):
    """Provider-neutral, bounded query transformation request."""

    model_id: NonEmptyStr
    kind: QueryTransformKind
    query: NonEmptyStr
    history: tuple[str, ...] = ()
    target_languages: tuple[str, ...] = ()
    max_items: int = 4
    trace_id: NonEmptyStr


class QueryTransformResult(KnowledgeModel):
    """Validated structured strings returned by a query model."""

    model_id: NonEmptyStr
    items: tuple[NonEmptyStr, ...]


@runtime_checkable
class QueryTransformProviderPort(Protocol):
    """Rewrite, translate, or expand without exposing a supplier SDK."""

    async def transform(
        self,
        context: AuthorizationContext,
        request: QueryTransformRequest,
    ) -> QueryTransformResult: ...
