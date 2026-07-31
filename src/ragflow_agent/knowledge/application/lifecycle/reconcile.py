"""Bounded, tenant-scoped lifecycle reconciliation."""

from datetime import datetime

from pydantic import Field

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.document import DocumentStatus
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperationStatus,
    OutboxStatus,
)
from ragflow_agent.knowledge.ports.search import LifecycleSearchPort
from ragflow_agent.knowledge.ports.storage import ObjectStoragePort, StoredObject
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock


class ReconciliationFinding(KnowledgeModel):
    tenant_id: NonEmptyStr
    kind: NonEmptyStr
    resource_id: NonEmptyStr
    repaired: bool = False
    detail: str | None = None


class ReconciliationReport(KnowledgeModel):
    tenant_id: NonEmptyStr
    dry_run: bool
    scanned: int = Field(ge=0)
    findings: tuple[ReconciliationFinding, ...]


class LifecycleReconciler:
    """Detect stale operations and cross-store drift; default to non-destructive dry-run."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        search: LifecycleSearchPort,
        storage: ObjectStoragePort,
        clock: Clock,
        limit: int = 100,
    ) -> None:
        self._uow = unit_of_work_factory
        self._search = search
        self._storage = storage
        self._clock = clock
        self._limit = limit

    async def run(
        self,
        context: AuthorizationContext,
        *,
        stale_before: datetime,
        dry_run: bool = True,
    ) -> ReconciliationReport:
        statuses = (
            LifecycleOperationStatus.PENDING,
            LifecycleOperationStatus.RUNNING,
            LifecycleOperationStatus.WAITING_RETRY,
            LifecycleOperationStatus.CANCEL_REQUESTED,
        )
        async with self._uow() as unit_of_work:
            operations = await unit_of_work.lifecycle_operations.list_by_status(
                tenant_id=context.tenant_id,
                statuses=statuses,
                updated_before=stale_before,
                limit=self._limit,
            )
            outbox = await unit_of_work.lifecycle_outbox.list_due(
                tenant_id=context.tenant_id,
                now=self._clock.now(),
                limit=self._limit,
            )
            versions = await unit_of_work.document_versions.list_for_tenant(
                tenant_id=context.tenant_id, limit=self._limit * 10
            )
            documents = await unit_of_work.documents.list_by_status(
                tenant_id=context.tenant_id,
                statuses=(DocumentStatus.ACTIVE, DocumentStatus.DELETE_PENDING),
                limit=self._limit,
            )
        findings: list[ReconciliationFinding] = []
        for operation in operations:
            async with self._uow() as unit_of_work:
                document = await unit_of_work.documents.get(
                    tenant_id=context.tenant_id, resource_id=operation.document_id
                )
                version = await unit_of_work.document_versions.get(
                    tenant_id=context.tenant_id, resource_id=operation.version_id
                )
            if document is None or version is None:
                findings.append(
                    ReconciliationFinding(
                        tenant_id=context.tenant_id,
                        kind="missing_authoritative_state",
                        resource_id=operation.id,
                        detail="document or version is missing",
                    )
                )
                continue
            projection_count = await self._search.validate_document_version(
                context,
                knowledge_base_id=operation.knowledge_base_id,
                document_id=operation.document_id,
                document_version_id=operation.version_id,
            )
            source = StoredObject(
                tenant_id=context.tenant_id,
                object_key=version.object_key,
                media_type=version.media_type,
                size_bytes=version.size_bytes,
                checksum_sha256=version.content_hash,
            )
            source_exists = await self._storage.exists(context, source)
            if projection_count == 0 or not source_exists:
                findings.append(
                    ReconciliationFinding(
                        tenant_id=context.tenant_id,
                        kind="cross_store_drift",
                        resource_id=operation.id,
                        detail=f"projection={projection_count}, object={source_exists}",
                    )
                )
        for event in outbox:
            findings.append(
                ReconciliationFinding(
                    tenant_id=context.tenant_id,
                    kind="outbox_due",
                    resource_id=event.id,
                    repaired=False,
                    detail=event.status.value,
                )
            )
        authoritative_versions = {item.id for item in versions}
        authoritative_objects = {item.object_key for item in versions}
        prefix = f"tenants/{context.tenant_id}/"
        for object_key in await self._storage.list_prefix(
            context, tenant_id=context.tenant_id, prefix=prefix
        ):
            if object_key in authoritative_objects:
                continue
            repaired = False
            if not dry_run:
                await self._storage.delete(
                    context,
                    StoredObject(
                        tenant_id=context.tenant_id,
                        object_key=object_key,
                        media_type="application/octet-stream",
                        size_bytes=0,
                        checksum_sha256="reconciliation",
                    ),
                )
                repaired = True
            findings.append(
                ReconciliationFinding(
                    tenant_id=context.tenant_id,
                    kind="orphan_object",
                    resource_id=object_key,
                    repaired=repaired,
                )
            )
        for (
            knowledge_base_id,
            document_id,
            version_id,
        ) in await self._search.list_projection_versions(context, limit=self._limit * 10):
            if version_id in authoritative_versions:
                continue
            repaired = False
            if not dry_run:
                await self._search.delete_document_version(
                    context,
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    document_version_id=version_id,
                )
                repaired = True
            findings.append(
                ReconciliationFinding(
                    tenant_id=context.tenant_id,
                    kind="orphan_projection",
                    resource_id=version_id,
                    repaired=repaired,
                )
            )
        now = self._clock.now()
        for document in documents:
            if (
                document.status is DocumentStatus.DELETE_PENDING
                and document.purge_after is not None
                and document.purge_after <= now
            ):
                findings.append(
                    ReconciliationFinding(
                        tenant_id=context.tenant_id,
                        kind="expired_physical_cleanup",
                        resource_id=document.id,
                    )
                )
        return ReconciliationReport(
            tenant_id=context.tenant_id,
            dry_run=dry_run,
            scanned=len(operations) + len(outbox) + len(documents),
            findings=tuple(findings),
        )


def mark_outbox_published(event, *, changed_at: datetime):  # type: ignore[no-untyped-def]
    return event.model_copy(
        update={
            "status": OutboxStatus.PUBLISHED,
            "attempts": event.attempts + 1,
            "published_at": changed_at,
            "updated_at": changed_at,
            "last_error": None,
        }
    )
