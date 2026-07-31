"""LangChain-backed OpenAI-compatible model adapters."""

from ragflow_agent.knowledge.infrastructure.models.bge_reranker import (
    BgeRerankerAdapter,
    UnconfiguredReranker,
    build_reranker,
)
from ragflow_agent.knowledge.infrastructure.models.langchain_openai import (
    LangChainChatProvider,
    LangChainEmbeddingAdapter,
    UnconfiguredChatProvider,
    build_chat_provider,
    build_embedding_adapter,
)
from ragflow_agent.knowledge.infrastructure.models.query_transform import (
    ChatQueryTransformProvider,
)

__all__ = [
    "BgeRerankerAdapter",
    "ChatQueryTransformProvider",
    "LangChainChatProvider",
    "LangChainEmbeddingAdapter",
    "UnconfiguredChatProvider",
    "UnconfiguredReranker",
    "build_chat_provider",
    "build_embedding_adapter",
    "build_reranker",
]
