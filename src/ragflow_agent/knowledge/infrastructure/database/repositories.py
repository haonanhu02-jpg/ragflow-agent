"""SQLAlchemy repository implementations of the Phase 03 tenant contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ragflow_agent.knowledge.domain.document import Document, DocumentStatus, DocumentVersion
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.ingestion import IngestionJob, IngestionTask
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleBatch,
    LifecycleOperation,
    LifecycleOperationStatus,
    LifecycleOutboxEvent,
    OutboxStatus,
)
from ragflow_agent.knowledge.infrastructure.database.models import (
    DocumentRow,
    DocumentVersionRow,
    IngestionJobRow,
    IngestionTaskRow,
    KnowledgeBaseRow,
    LifecycleBatchRow,
    LifecycleOperationRow,
    LifecycleOutboxRow,
)


class SqlAlchemyTenantRepository[EntityT: BaseModel]:
    """Store immutable domain snapshots behind explicit tenant lookups."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        row_type: type[Any],
        entity_type: type[EntityT],
    ) -> None:
        self._session = session
        self._row_type = row_type
        self._entity_type = entity_type

    async def get(self, *, tenant_id: str, resource_id: str) -> EntityT | None:
        row = await self._session.get(self._row_type, (tenant_id, resource_id))
        if row is None:
            return None
        return self._entity_type.model_validate(row.payload)

    async def add(self, *, tenant_id: str, entity: EntityT) -> None:
        self._require_tenant(tenant_id, entity)
        row = self._row_type(**self._row_values(entity))
        self._session.add(row)
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise KnowledgeConflictError(
                "knowledge resource already exists",
                error_code="knowledge_resource_exists",
                details={"resource_id": str(cast(Any, entity).id)},
            ) from error

    async def save(self, *, tenant_id: str, entity: EntityT) -> None:
        self._require_tenant(tenant_id, entity)
        resource_id = str(cast(Any, entity).id)
        row = await self._session.get(self._row_type, (tenant_id, resource_id))
        if row is None:
            raise KnowledgeNotFoundError("knowledge_resource", resource_id)
        values = self._row_values(entity)
        for name, value in values.items():
            setattr(row, name, value)
        await self._session.flush()

    def _require_tenant(self, tenant_id: str, entity: EntityT) -> None:
        if cast(Any, entity).tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")

    @staticmethod
    def _payload(entity: EntityT) -> dict[str, Any]:
        return entity.model_dump(mode="json")

    def _row_values(self, entity: EntityT) -> dict[str, Any]:
        return {
            "tenant_id": str(cast(Any, entity).tenant_id),
            "id": str(cast(Any, entity).id),
            "payload": self._payload(entity),
        }


class SqlAlchemyKnowledgeBaseRepository(SqlAlchemyTenantRepository[KnowledgeBase]):
    """KnowledgeBase repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=KnowledgeBaseRow, entity_type=KnowledgeBase)


class SqlAlchemyDocumentRepository(SqlAlchemyTenantRepository[Document]):
    """Document repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=DocumentRow, entity_type=Document)

    def _row_values(self, entity: Document) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "knowledge_base_id": entity.knowledge_base_id,
            "current_version_id": entity.current_version_id,
            "status": entity.status.value,
            "revision": entity.revision,
        }

    async def save_if_revision(
        self,
        *,
        tenant_id: str,
        entity: Document,
        expected_revision: int,
    ) -> None:
        self._require_tenant(tenant_id, entity)
        result = await self._session.execute(
            update(DocumentRow)
            .where(
                DocumentRow.tenant_id == tenant_id,
                DocumentRow.id == entity.id,
                DocumentRow.revision == expected_revision,
            )
            .values(**self._row_values(entity))
        )
        if cast(Any, result).rowcount != 1:
            raise KnowledgeConflictError(
                "document revision changed",
                error_code="document_revision_conflict",
                details={"expected_revision": expected_revision},
            )
        await self._session.flush()

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[DocumentStatus, ...],
        limit: int = 100,
    ) -> tuple[Document, ...]:
        rows = (
            await self._session.scalars(
                select(DocumentRow)
                .where(
                    DocumentRow.tenant_id == tenant_id,
                    DocumentRow.status.in_(tuple(item.value for item in statuses)),
                )
                .order_by(DocumentRow.id)
                .limit(limit)
            )
        ).all()
        return tuple(Document.model_validate(row.payload) for row in rows)


class SqlAlchemyDocumentVersionRepository(SqlAlchemyTenantRepository[DocumentVersion]):
    """DocumentVersion repository with tenant/document listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=DocumentVersionRow, entity_type=DocumentVersion)
        self._session = session

    def _row_values(self, entity: DocumentVersion) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "knowledge_base_id": entity.knowledge_base_id,
            "document_id": entity.document_id,
        }

    async def list_for_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
    ) -> tuple[DocumentVersion, ...]:
        rows = (
            await self._session.scalars(
                select(DocumentVersionRow)
                .where(
                    DocumentVersionRow.tenant_id == tenant_id,
                    DocumentVersionRow.document_id == document_id,
                )
                .order_by(DocumentVersionRow.id)
            )
        ).all()
        return tuple(DocumentVersion.model_validate(row.payload) for row in rows)

    async def list_for_tenant(
        self, *, tenant_id: str, limit: int = 1000
    ) -> tuple[DocumentVersion, ...]:
        rows = (
            await self._session.scalars(
                select(DocumentVersionRow)
                .where(DocumentVersionRow.tenant_id == tenant_id)
                .order_by(DocumentVersionRow.id)
                .limit(limit)
            )
        ).all()
        return tuple(DocumentVersion.model_validate(row.payload) for row in rows)


class SqlAlchemyIngestionJobRepository(SqlAlchemyTenantRepository[IngestionJob]):
    """IngestionJob repository."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=IngestionJobRow, entity_type=IngestionJob)

    def _row_values(self, entity: IngestionJob) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "knowledge_base_id": entity.knowledge_base_id,
            "document_id": entity.document_id,
            "document_version_id": entity.document_version_id,
            "idempotency_key": entity.idempotency_key,
        }


class SqlAlchemyIngestionTaskRepository(SqlAlchemyTenantRepository[IngestionTask]):
    """IngestionTask repository with tenant/job listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=IngestionTaskRow, entity_type=IngestionTask)
        self._session = session

    def _row_values(self, entity: IngestionTask) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "job_id": entity.job_id,
            "document_version_id": entity.document_version_id,
            "stage": entity.stage.value,
        }

    async def list_for_job(
        self,
        *,
        tenant_id: str,
        job_id: str,
    ) -> tuple[IngestionTask, ...]:
        rows = (
            await self._session.scalars(
                select(IngestionTaskRow)
                .where(
                    IngestionTaskRow.tenant_id == tenant_id,
                    IngestionTaskRow.job_id == job_id,
                )
                .order_by(IngestionTaskRow.id)
            )
        ).all()
        return tuple(IngestionTask.model_validate(row.payload) for row in rows)


class SqlAlchemyLifecycleOperationRepository(SqlAlchemyTenantRepository[LifecycleOperation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=LifecycleOperationRow, entity_type=LifecycleOperation)
        self._session = session

    def _row_values(self, entity: LifecycleOperation) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "knowledge_base_id": entity.knowledge_base_id,
            "document_id": entity.document_id,
            "version_id": entity.version_id,
            "kind": entity.kind.value,
            "status": entity.status.value,
            "idempotency_key": entity.idempotency_key,
            "batch_id": entity.batch_id,
            "updated_at": entity.updated_at,
        }

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleOperation | None:
        row = await self._session.scalar(
            select(LifecycleOperationRow).where(
                LifecycleOperationRow.tenant_id == tenant_id,
                LifecycleOperationRow.idempotency_key == idempotency_key,
            )
        )
        return None if row is None else LifecycleOperation.model_validate(row.payload)

    async def list_for_document(
        self, *, tenant_id: str, document_id: str
    ) -> tuple[LifecycleOperation, ...]:
        rows = (
            await self._session.scalars(
                select(LifecycleOperationRow)
                .where(
                    LifecycleOperationRow.tenant_id == tenant_id,
                    LifecycleOperationRow.document_id == document_id,
                )
                .order_by(LifecycleOperationRow.updated_at)
            )
        ).all()
        return tuple(LifecycleOperation.model_validate(row.payload) for row in rows)

    async def list_by_status(
        self,
        *,
        tenant_id: str,
        statuses: tuple[LifecycleOperationStatus, ...],
        updated_before: datetime | None = None,
        limit: int = 100,
    ) -> tuple[LifecycleOperation, ...]:
        statement = select(LifecycleOperationRow).where(
            LifecycleOperationRow.tenant_id == tenant_id,
            LifecycleOperationRow.status.in_(tuple(status.value for status in statuses)),
        )
        if updated_before is not None:
            statement = statement.where(LifecycleOperationRow.updated_at <= updated_before)
        rows = (
            await self._session.scalars(
                statement.order_by(LifecycleOperationRow.updated_at).limit(limit)
            )
        ).all()
        return tuple(LifecycleOperation.model_validate(row.payload) for row in rows)


class SqlAlchemyLifecycleOutboxRepository(SqlAlchemyTenantRepository[LifecycleOutboxEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=LifecycleOutboxRow, entity_type=LifecycleOutboxEvent)
        self._session = session

    def _row_values(self, entity: LifecycleOutboxEvent) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "operation_id": entity.operation_id,
            "aggregate_id": entity.aggregate_id,
            "status": entity.status.value,
            "idempotency_key": entity.idempotency_key,
            "available_at": entity.available_at,
        }

    async def list_due(
        self, *, tenant_id: str, now: datetime, limit: int
    ) -> tuple[LifecycleOutboxEvent, ...]:
        rows = (
            await self._session.scalars(
                select(LifecycleOutboxRow)
                .where(
                    LifecycleOutboxRow.tenant_id == tenant_id,
                    LifecycleOutboxRow.status == OutboxStatus.PENDING.value,
                    LifecycleOutboxRow.available_at <= now,
                )
                .order_by(LifecycleOutboxRow.available_at)
                .limit(limit)
            )
        ).all()
        return tuple(LifecycleOutboxEvent.model_validate(row.payload) for row in rows)


class SqlAlchemyLifecycleBatchRepository(SqlAlchemyTenantRepository[LifecycleBatch]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, row_type=LifecycleBatchRow, entity_type=LifecycleBatch)
        self._session = session

    def _row_values(self, entity: LifecycleBatch) -> dict[str, Any]:
        return {
            **super()._row_values(entity),
            "knowledge_base_id": entity.knowledge_base_id,
            "status": entity.status.value,
            "idempotency_key": entity.idempotency_key,
        }

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> LifecycleBatch | None:
        row = await self._session.scalar(
            select(LifecycleBatchRow).where(
                LifecycleBatchRow.tenant_id == tenant_id,
                LifecycleBatchRow.idempotency_key == idempotency_key,
            )
        )
        return None if row is None else LifecycleBatch.model_validate(row.payload)
