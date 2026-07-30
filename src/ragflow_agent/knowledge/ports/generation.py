"""Provider-neutral fixed-answer generation boundary."""

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


@runtime_checkable
class ChatProviderPort(Protocol):
    """Generate a fixed-RAG answer without exposing a supplier SDK."""

    async def generate(
        self,
        context: AuthorizationContext,
        request: ChatGenerationRequest,
    ) -> ChatGenerationResult: ...
