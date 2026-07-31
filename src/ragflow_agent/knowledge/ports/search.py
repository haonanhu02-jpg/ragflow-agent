"""Index, retrieval, and reranking boundaries without vendor DSLs."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel
from ragflow_agent.knowledge.domain.retrieval import (
    IndexRecord,
    IndexVersion,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
)


@runtime_checkable
class SearchIndexPort(Protocol):
    """Write and activate versioned search records."""

    async def upsert(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
        records: tuple[IndexRecord, ...],
    ) -> None: ...

    async def delete(
        self,
        context: AuthorizationContext,
        *,
        index_version_id: str,
        chunk_ids: tuple[str, ...],
    ) -> None: ...

    async def activate(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
    ) -> None: ...


@runtime_checkable
class RetrieverPort(Protocol):
    """Run a tenant-authorized structured retrieval request."""

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult: ...


@runtime_checkable
class SearchChannelPort(Protocol):
    """Expose independently auditable full-text and vector retrieval channels."""

    async def retrieve_full_text(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]: ...

    async def retrieve_vector(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]: ...


class RerankRequest(KnowledgeModel):
    """Provider-neutral rerank input."""

    query: RetrievalQuery
    candidates: tuple[RetrievalCandidate, ...]


@runtime_checkable
class RerankerPort(Protocol):
    """Rerank candidates without changing their source identity."""

    async def rerank(
        self,
        context: AuthorizationContext,
        request: RerankRequest,
    ) -> tuple[RetrievalCandidate, ...]: ...
