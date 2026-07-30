"""LangChain adapters for DeepSeek Chat and OpenAI-compatible BGE-M3."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from ragflow_agent.config import ModelSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
)
from ragflow_agent.knowledge.ports.embedding import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingVector,
)
from ragflow_agent.knowledge.ports.generation import (
    ChatGenerationRequest,
    ChatGenerationResult,
)
from ragflow_agent.shared import AppError


class LangChainEmbeddingAdapter:
    """Map the internal EmbeddingPort to one LangChain Embeddings instance."""

    def __init__(
        self,
        embeddings: Embeddings,
        *,
        model_id: str,
        expected_dimensions: int,
        normalized: bool = True,
    ) -> None:
        self._embeddings = embeddings
        self._model_id = model_id
        self._expected_dimensions = expected_dimensions
        self._normalized = normalized

    async def embed(
        self,
        context: AuthorizationContext,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        if context.tenant_id != request.tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        if request.model_id != self._model_id:
            raise KnowledgeConflictError(
                "embedding request model does not match the configured adapter",
                error_code="embedding_model_mismatch",
            )
        values = await self._embeddings.aembed_documents([item.text for item in request.inputs])
        if len(values) != len(request.inputs):
            raise KnowledgeConflictError(
                "embedding provider returned a partial batch",
                error_code="embedding_partial_result",
            )
        dimension_errors = [
            {"input_id": item.id, "actual_dimensions": len(vector)}
            for item, vector in zip(request.inputs, values, strict=True)
            if len(vector) != self._expected_dimensions
        ]
        if dimension_errors:
            raise KnowledgeConflictError(
                "embedding provider returned an unexpected dimension",
                error_code="embedding_dimension_mismatch",
                details={
                    "expected_dimensions": self._expected_dimensions,
                    "inputs": dimension_errors,
                },
            )
        return EmbeddingResult(
            model_id=self._model_id,
            dimensions=self._expected_dimensions,
            normalized=self._normalized,
            vectors=tuple(
                EmbeddingVector(input_id=item.id, values=tuple(vector))
                for item, vector in zip(request.inputs, values, strict=True)
            ),
        )


class LangChainChatProvider:
    """Map an internal generation request to a LangChain ChatModel."""

    def __init__(self, model: BaseChatModel, *, model_id: str) -> None:
        self._model = model
        self._model_id = model_id

    async def generate(
        self,
        context: AuthorizationContext,
        request: ChatGenerationRequest,
    ) -> ChatGenerationResult:
        del context
        if request.model_id != self._model_id:
            raise KnowledgeConflictError(
                "chat request model does not match the configured adapter",
                error_code="chat_model_mismatch",
            )
        response = await self._model.ainvoke(
            [
                SystemMessage(content=request.system_prompt),
                HumanMessage(content=request.user_prompt),
            ]
        )
        if not isinstance(response.content, str) or not response.content.strip():
            raise KnowledgeConflictError(
                "chat provider returned no text",
                error_code="chat_empty_result",
            )
        return ChatGenerationResult(model_id=self._model_id, content=response.content.strip())


class UnconfiguredChatProvider:
    """Fail explicitly when a real API credential was not configured."""

    def __init__(self, *, model_id: str) -> None:
        self._model_id = model_id

    async def generate(
        self,
        context: AuthorizationContext,
        request: ChatGenerationRequest,
    ) -> ChatGenerationResult:
        del context, request
        raise AppError(
            "chat provider credential is not configured",
            error_code="chat_provider_unconfigured",
            status_code=503,
        )


def build_embedding_adapter(settings: ModelSettings) -> LangChainEmbeddingAdapter:
    """Build the default OpenAI-compatible BGE-M3 adapter."""
    api_key = settings.embedding_api_key or SecretStr("local-endpoint-no-key")
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url,
        api_key=api_key,
        dimensions=settings.embedding_dimensions,
        timeout=settings.request_timeout_seconds,
    )
    return LangChainEmbeddingAdapter(
        embeddings,
        model_id=settings.embedding_model,
        expected_dimensions=settings.embedding_dimensions,
    )


def build_chat_provider(
    settings: ModelSettings,
) -> LangChainChatProvider | UnconfiguredChatProvider:
    """Build DeepSeek when configured, otherwise an explicit unavailable adapter."""
    if settings.chat_api_key is None:
        return UnconfiguredChatProvider(model_id=settings.chat_model)
    model = ChatOpenAI(
        model=settings.chat_model,
        base_url=settings.chat_base_url,
        api_key=settings.chat_api_key,
        timeout=settings.request_timeout_seconds,
        temperature=0,
    )
    return LangChainChatProvider(model, model_id=settings.chat_model)
