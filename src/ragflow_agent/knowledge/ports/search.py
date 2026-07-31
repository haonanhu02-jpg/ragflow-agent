"""Index, retrieval, and reranking boundaries without vendor DSLs."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel
from ragflow_agent.knowledge.domain.lifecycle import (
    IndexGeneration,
    IndexGenerationValidation,
)
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
class LifecycleSearchPort(Protocol):
    """Document projection and physical-index publication lifecycle."""

    async def validate_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> int: ...

    async def promote_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
        fencing_token: int,
    ) -> None: ...

    async def retire_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None: ...

    async def delete_document_version(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        document_id: str,
        document_version_id: str,
    ) -> None: ...

    async def list_projection_versions(
        self,
        context: AuthorizationContext,
        *,
        limit: int = 1000,
    ) -> tuple[tuple[str, str, str], ...]: ...

    async def create_staging_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> None: ...

    async def write_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        records: tuple[IndexRecord, ...],
    ) -> None: ...

    async def validate_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
    ) -> IndexGenerationValidation: ...

    async def switch_alias(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
        *,
        expected_current: str | None,
    ) -> str | None: ...

    async def resolve_alias(
        self,
        context: AuthorizationContext,
        *,
        alias: str,
    ) -> str | None: ...

    async def delete_generation(
        self,
        context: AuthorizationContext,
        generation: IndexGeneration,
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
