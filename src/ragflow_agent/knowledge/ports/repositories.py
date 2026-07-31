"""Tenant-scoped repository contracts for knowledge aggregates."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.document import (
    Document,
    DocumentStatus,
    DocumentVersion,
)
from ragflow_agent.knowledge.domain.ingestion import IngestionJob, IngestionTask
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleBatch,
    LifecycleOperation,
    LifecycleOperationStatus,
    LifecycleOutboxEvent,
)


class TenantRepository[Entity](Protocol):
    """Minimal aggregate repository with no tenant-free lookup."""

    async def get(self, *, tenant_id: str, resource_id: str) -> Entity | None: ...

    async def add(self, *, tenant_id: str, entity: Entity) -> None: ...

    async def save(self, *, tenant_id: str, entity: Entity) -> None: ...


@runtime_checkable
class KnowledgeBaseRepository(TenantRepository[KnowledgeBase], Protocol):
    """KnowledgeBase persistence boundary."""


@runtime_checkable
class DocumentRepository(TenantRepository[Document], Protocol):
    """Logical Document persistence boundary."""

    async def save_if_revision(
        self,
        *,
        tenant_id: str,
        entity: Document,
        expected_revision: int,
    ) -> None: ...

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[DocumentStatus, ...],
        limit: int = 100,
    ) -> tuple[Document, ...]: ...


@runtime_checkable
class DocumentVersionRepository(TenantRepository[DocumentVersion], Protocol):
    """DocumentVersion persistence and scoped listing boundary."""

    async def list_for_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
    ) -> tuple[DocumentVersion, ...]: ...

    async def list_for_tenant(
        self, *, tenant_id: str, limit: int = 1000
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


@runtime_checkable
class LifecycleOperationRepository(TenantRepository[LifecycleOperation], Protocol):
    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleOperation | None: ...

    async def list_for_document(
        self, *, tenant_id: str, document_id: str
    ) -> tuple[LifecycleOperation, ...]: ...

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[LifecycleOperationStatus, ...],
        updated_before: datetime | None = None,
        limit: int = 100,
    ) -> tuple[LifecycleOperation, ...]: ...


@runtime_checkable
class LifecycleOutboxRepository(TenantRepository[LifecycleOutboxEvent], Protocol):
    async def list_due(
        self, *, tenant_id: str, now: datetime, limit: int
    ) -> tuple[LifecycleOutboxEvent, ...]: ...


@runtime_checkable
class LifecycleBatchRepository(TenantRepository[LifecycleBatch], Protocol):
    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleBatch | None: ...
