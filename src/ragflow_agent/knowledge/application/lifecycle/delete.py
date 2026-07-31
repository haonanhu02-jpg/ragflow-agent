"""Fail-closed soft deletion, restoration, and idempotent physical purge."""

from datetime import timedelta
from hashlib import sha256

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, PermissionAction
from ragflow_agent.knowledge.domain.document import (
    DocumentStatus,
    DocumentVersionStatus,
    activate_document_version,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOperationStatus,
    LifecycleOutboxEvent,
    OutboxStatus,
)
from ragflow_agent.knowledge.ports.permission import PermissionChecker
from ragflow_agent.knowledge.ports.search import LifecycleSearchPort
from ragflow_agent.knowledge.ports.storage import ObjectStoragePort, StoredObject
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock


class DocumentDeletionService:
    """Make content invisible transactionally before best-effort physical cleanup."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        search: LifecycleSearchPort,
        storage: ObjectStoragePort,
        permission_checker: PermissionChecker,
        id_generator: IdGenerator,
        clock: Clock,
        retention_days: int = 30,
    ) -> None:
        self._uow = unit_of_work_factory
        self._search = search
        self._storage = storage
        self._permission = permission_checker
        self._ids = id_generator
        self._clock = clock
        self._retention = timedelta(days=retention_days)

    async def request_delete(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        idempotency_key: str,
        reason: str,
    ) -> LifecycleOperation:
        async with self._uow() as unit_of_work:
            duplicate = await unit_of_work.lifecycle_operations.get_by_idempotency_key(
                tenant_id=context.tenant_id, idempotency_key=idempotency_key
            )
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id, resource_id=document_id
            )
            if document is None:
                raise KnowledgeNotFoundError("document", document_id)
            self._permission.require(context, document.authorization, PermissionAction.DELETE)
            fingerprint = self._fingerprint(
                LifecycleOperationKind.DELETE,
                document_id,
                reason,
            )
            if duplicate is not None:
                self._require_matching_duplicate(
                    duplicate,
                    kind=LifecycleOperationKind.DELETE,
                    document_id=document_id,
                    fingerprint=fingerprint,
                )
                return duplicate
            if document.status is not DocumentStatus.ACTIVE or document.current_version_id is None:
                raise KnowledgeConflictError(
                    "document is already deleted", error_code="document_deleted"
                )
            now = self._clock.now()
            operation = LifecycleOperation(
                id=self._ids.new_id(),
                tenant_id=context.tenant_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                version_id=document.current_version_id,
                kind=LifecycleOperationKind.DELETE,
                idempotency_key=idempotency_key,
                actor_id=context.actor_id,
                reason=reason,
                request_id=context.request_id,
                expected_document_revision=document.revision,
                fencing_token=document.revision + 1,
                previous_version_id=document.current_version_id,
                purge_after=now + self._retention,
                metadata={"command_fingerprint": fingerprint},
                created_at=now,
                updated_at=now,
            )
            tombstone = document.model_copy(
                update={
                    "status": DocumentStatus.DELETE_PENDING,
                    "current_version_id": None,
                    "revision": document.revision + 1,
                    "deleted_at": now,
                    "purge_after": operation.purge_after,
                    "updated_at": now,
                }
            )
            event = LifecycleOutboxEvent(
                id=f"outbox:{operation.id}",
                tenant_id=context.tenant_id,
                operation_id=operation.id,
                aggregate_id=document.id,
                event_type="document.cleanup.requested",
                idempotency_key=f"outbox:{operation.id}:cleanup",
                payload={"document_id": document.id},
                available_at=operation.purge_after or now,
                created_at=now,
                updated_at=now,
            )
            await unit_of_work.documents.save_if_revision(
                tenant_id=context.tenant_id,
                entity=tombstone,
                expected_revision=document.revision,
            )
            await unit_of_work.lifecycle_operations.add(
                tenant_id=context.tenant_id, entity=operation
            )
            await unit_of_work.lifecycle_outbox.add(tenant_id=context.tenant_id, entity=event)
            await unit_of_work.commit()
        await self._search.retire_document_version(
            context,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=operation.version_id,
        )
        return operation

    async def restore(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        idempotency_key: str,
        reason: str,
    ) -> LifecycleOperation:
        async with self._uow() as unit_of_work:
            duplicate = await unit_of_work.lifecycle_operations.get_by_idempotency_key(
                tenant_id=context.tenant_id, idempotency_key=idempotency_key
            )
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id, resource_id=document_id
            )
            if document is None:
                raise KnowledgeNotFoundError("document", document_id)
            self._permission.require(context, document.authorization, PermissionAction.WRITE)
            fingerprint = self._fingerprint(
                LifecycleOperationKind.RESTORE,
                document_id,
                reason,
            )
            if duplicate is not None:
                self._require_matching_duplicate(
                    duplicate,
                    kind=LifecycleOperationKind.RESTORE,
                    document_id=document_id,
                    fingerprint=fingerprint,
                )
                return duplicate
            operations = await unit_of_work.lifecycle_operations.list_for_document(
                tenant_id=context.tenant_id, document_id=document_id
            )
            deletion = next(
                (
                    item
                    for item in reversed(operations)
                    if item.kind is LifecycleOperationKind.DELETE
                ),
                None,
            )
            target = (
                await unit_of_work.document_versions.get(
                    tenant_id=context.tenant_id,
                    resource_id=deletion.previous_version_id,
                )
                if deletion and deletion.previous_version_id
                else None
            )
        now = self._clock.now()
        if (
            document.status is not DocumentStatus.DELETE_PENDING
            or document.purge_after is None
            or now >= document.purge_after
            or target is None
            or target.status is DocumentVersionStatus.DELETED
        ):
            raise KnowledgeConflictError(
                "document is not recoverable", error_code="document_restore_expired"
            )
        count = await self._search.validate_document_version(
            context,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=target.id,
        )
        if count < 1:
            raise KnowledgeConflictError(
                "document projection is not healthy", error_code="rollback_target_invalid"
            )
        await self._search.promote_document_version(
            context,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=target.id,
            fencing_token=document.revision + 1,
        )
        ready = target
        if target.status is DocumentVersionStatus.SUPERSEDED:
            ready = transition_document_version(target, DocumentVersionStatus.READY, changed_at=now)
        base = document.model_copy(
            update={
                "status": DocumentStatus.ACTIVE,
                "deleted_at": None,
                "purge_after": None,
                "updated_at": now,
            }
        )
        restored = activate_document_version(
            base, ready, changed_at=now, expected_revision=document.revision
        )
        operation = LifecycleOperation(
            id=self._ids.new_id(),
            tenant_id=context.tenant_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            version_id=ready.id,
            kind=LifecycleOperationKind.RESTORE,
            idempotency_key=idempotency_key,
            actor_id=context.actor_id,
            reason=reason,
            request_id=context.request_id,
            status=LifecycleOperationStatus.SUCCEEDED,
            expected_document_revision=document.revision,
            fencing_token=document.revision + 1,
            progress=1,
            metadata={"command_fingerprint": fingerprint},
            created_at=now,
            updated_at=now,
        )
        async with self._uow() as unit_of_work:
            await unit_of_work.document_versions.save(tenant_id=context.tenant_id, entity=ready)
            await unit_of_work.documents.save_if_revision(
                tenant_id=context.tenant_id,
                entity=restored,
                expected_revision=document.revision,
            )
            await unit_of_work.lifecycle_operations.add(
                tenant_id=context.tenant_id, entity=operation
            )
            if deletion is not None:
                cleanup_event = await unit_of_work.lifecycle_outbox.get(
                    tenant_id=context.tenant_id,
                    resource_id=f"outbox:{deletion.id}",
                )
                if cleanup_event is not None and cleanup_event.status is OutboxStatus.PENDING:
                    await unit_of_work.lifecycle_outbox.save(
                        tenant_id=context.tenant_id,
                        entity=cleanup_event.model_copy(
                            update={
                                "status": OutboxStatus.CANCELLED,
                                "updated_at": now,
                            }
                        ),
                    )
            await unit_of_work.commit()
        return operation

    async def purge(
        self, context: AuthorizationContext, *, document_id: str, reason: str
    ) -> LifecycleOperation:
        return await self._purge(
            context,
            document_id=document_id,
            reason=reason,
            enforce_permission=True,
        )

    async def purge_due(
        self, context: AuthorizationContext, *, document_id: str, reason: str
    ) -> LifecycleOperation:
        """Purge only an already-authorized, expired tombstone from a maintenance worker."""
        return await self._purge(
            context,
            document_id=document_id,
            reason=reason,
            enforce_permission=False,
        )

    async def _purge(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        reason: str,
        enforce_permission: bool,
    ) -> LifecycleOperation:
        async with self._uow() as unit_of_work:
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id, resource_id=document_id
            )
            versions = await unit_of_work.document_versions.list_for_document(
                tenant_id=context.tenant_id, document_id=document_id
            )
        if document is None:
            raise KnowledgeNotFoundError("document", document_id)
        if enforce_permission:
            self._permission.require(context, document.authorization, PermissionAction.DELETE)
        now = self._clock.now()
        if document.status is DocumentStatus.DELETED:
            operations = await self._operations(context, document_id)
            prior = next(
                (
                    item
                    for item in reversed(operations)
                    if item.kind is LifecycleOperationKind.PURGE
                ),
                None,
            )
            if prior is not None:
                return prior
        if document.purge_after is None or now < document.purge_after:
            raise KnowledgeConflictError(
                "document retention has not expired", error_code="document_retention_active"
            )
        for version in versions:
            await self._search.delete_document_version(
                context,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                document_version_id=version.id,
            )
        for object_key in {version.object_key for version in versions}:
            source = next(version for version in versions if version.object_key == object_key)
            stored = StoredObject(
                tenant_id=context.tenant_id,
                object_key=object_key,
                media_type=source.media_type,
                size_bytes=source.size_bytes,
                checksum_sha256=source.content_hash,
            )
            if await self._storage.exists(context, stored):
                await self._storage.delete(context, stored)
        deleted_versions = tuple(
            version
            if version.status is DocumentVersionStatus.DELETED
            else transition_document_version(version, DocumentVersionStatus.DELETED, changed_at=now)
            for version in versions
        )
        purged = document.model_copy(
            update={
                "status": DocumentStatus.DELETED,
                "revision": document.revision + 1,
                "updated_at": now,
            }
        )
        operation = LifecycleOperation(
            id=self._ids.new_id(),
            tenant_id=context.tenant_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            version_id=(versions[-1].id if versions else "purged"),
            kind=LifecycleOperationKind.PURGE,
            idempotency_key=f"purge:{document.id}:{document.revision}",
            actor_id=context.actor_id,
            reason=reason,
            request_id=context.request_id,
            status=LifecycleOperationStatus.SUCCEEDED,
            expected_document_revision=document.revision,
            fencing_token=document.revision + 1,
            progress=1,
            created_at=now,
            updated_at=now,
        )
        async with self._uow() as unit_of_work:
            for version in deleted_versions:
                await unit_of_work.document_versions.save(
                    tenant_id=context.tenant_id, entity=version
                )
            await unit_of_work.documents.save_if_revision(
                tenant_id=context.tenant_id,
                entity=purged,
                expected_revision=document.revision,
            )
            await unit_of_work.lifecycle_operations.add(
                tenant_id=context.tenant_id, entity=operation
            )
            await unit_of_work.commit()
        return operation

    async def _operations(
        self, context: AuthorizationContext, document_id: str
    ) -> tuple[LifecycleOperation, ...]:
        async with self._uow() as unit_of_work:
            return await unit_of_work.lifecycle_operations.list_for_document(
                tenant_id=context.tenant_id, document_id=document_id
            )

    @staticmethod
    def _fingerprint(kind: LifecycleOperationKind, *parts: str) -> str:
        return sha256("\x1f".join((kind.value, *parts)).encode()).hexdigest()

    @staticmethod
    def _require_matching_duplicate(
        operation: LifecycleOperation,
        *,
        kind: LifecycleOperationKind,
        document_id: str,
        fingerprint: str,
    ) -> None:
        if (
            operation.kind is not kind
            or operation.document_id != document_id
            or operation.metadata.get("command_fingerprint") != fingerprint
        ):
            raise KnowledgeConflictError(
                "idempotency key was already used for a different command",
                error_code="lifecycle_idempotency_conflict",
            )
