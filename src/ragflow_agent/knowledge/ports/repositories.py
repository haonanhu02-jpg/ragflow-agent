"""Tenant-scoped repository contracts for knowledge aggregates."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.document import Document, DocumentVersion
from ragflow_agent.knowledge.domain.ingestion import IngestionJob, IngestionTask
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase


class TenantRepository[Entity](Protocol):
    """Minimal aggregate repository with no tenant-free lookup."""

    async def get(self, *, tenant_id: str, resource_id: str) -> Entity | None: ...

    async def add(self, *, tenant_id: str, entity: Entity) -> None: ...


@runtime_checkable
class KnowledgeBaseRepository(TenantRepository[KnowledgeBase], Protocol):
    """KnowledgeBase persistence boundary."""


@runtime_checkable
class DocumentRepository(TenantRepository[Document], Protocol):
    """Logical Document persistence boundary."""


@runtime_checkable
class DocumentVersionRepository(TenantRepository[DocumentVersion], Protocol):
    """DocumentVersion persistence and scoped listing boundary."""

    async def list_for_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
    ) -> tuple[DocumentVersion, ...]: ...


@runtime_checkable
class IngestionJobRepository(TenantRepository[IngestionJob], Protocol):
    """IngestionJob persistence boundary."""


@runtime_checkable
class IngestionTaskRepository(TenantRepository[IngestionTask], Protocol):
    """IngestionTask persistence boundary."""

    async def list_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
    ) -> tuple[IngestionTask, ...]: ...
