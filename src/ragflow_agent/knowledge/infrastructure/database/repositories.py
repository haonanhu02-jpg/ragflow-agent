"""SQLAlchemy repository implementations of the Phase 03 tenant contracts."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ragflow_agent.knowledge.domain.document import Document, DocumentVersion
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.ingestion import IngestionJob, IngestionTask
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.infrastructure.database.models import (
    DocumentRow,
    DocumentVersionRow,
    IngestionJobRow,
    IngestionTaskRow,
    KnowledgeBaseRow,
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
        }


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
