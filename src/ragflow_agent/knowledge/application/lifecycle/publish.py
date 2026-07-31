"""Safe publication and rollback of immutable document versions."""

from datetime import timedelta
from hashlib import sha256

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, PermissionAction
from ragflow_agent.knowledge.domain.document import (
    Document,
    DocumentStatus,
    DocumentVersion,
    DocumentVersionStatus,
    activate_document_version,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOperationStatus,
    LifecycleStep,
    LifecycleStepStatus,
    update_step,
)
from ragflow_agent.knowledge.ports.permission import PermissionChecker
from ragflow_agent.knowledge.ports.search import LifecycleSearchPort
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock


class DocumentVersionPublisher:
    """Use PostgreSQL CAS as authority while Elasticsearch remains a projection."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        search: LifecycleSearchPort,
        clock: Clock,
        id_generator: IdGenerator,
        permission_checker: PermissionChecker,
        history_retention_days: int = 30,
    ) -> None:
        self._uow = unit_of_work_factory
        self._search = search
        self._clock = clock
        self._ids = id_generator
        self._permission = permission_checker
        self._retention = timedelta(days=history_retention_days)

    async def complete_ingestion(
        self,
        context: AuthorizationContext,
        *,
        operation_id: str,
        index_version_id: str,
    ) -> LifecycleOperation:
        operation, document, version, previous = await self._load(context, operation_id)
        if operation.status is LifecycleOperationStatus.SUCCEEDED:
            return operation
        if document.status is not DocumentStatus.ACTIVE:
            raise KnowledgeConflictError("document is not active", error_code="document_deleted")
        if document.revision != operation.expected_document_revision:
            raise KnowledgeConflictError(
                "stale lifecycle operation", error_code="document_revision_conflict"
            )
        now = self._clock.now()
        count = await self._search.validate_document_version(
            context,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=version.id,
        )
        if count < 1:
            raise KnowledgeConflictError(
                "candidate version has no searchable chunks",
                error_code="lifecycle_candidate_empty",
            )
        operation = update_step(
            operation,
            LifecycleStep.VALIDATE,
            LifecycleStepStatus.SUCCEEDED,
            changed_at=now,
        )
        await self._search.promote_document_version(
            context,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            document_version_id=version.id,
            fencing_token=operation.fencing_token,
        )
        operation = update_step(
            operation,
            LifecycleStep.PROMOTE,
            LifecycleStepStatus.SUCCEEDED,
            changed_at=now,
        )
        ready = version
        if ready.status is not DocumentVersionStatus.READY:
            ready = transition_document_version(ready, DocumentVersionStatus.READY, changed_at=now)
        ready = ready.model_copy(update={"index_version_id": index_version_id, "activated_at": now})
        active = activate_document_version(
            document,
            ready,
            changed_at=now,
            expected_revision=operation.expected_document_revision,
        )
        retired = None
        if previous is not None and previous.id != ready.id:
            retired = transition_document_version(
                previous, DocumentVersionStatus.SUPERSEDED, changed_at=now
            ).model_copy(update={"retired_at": now, "purge_after": now + self._retention})
        operation = update_step(
            operation,
            LifecycleStep.ACTIVATE,
            LifecycleStepStatus.SUCCEEDED,
            changed_at=now,
        ).model_copy(
            update={
                "status": LifecycleOperationStatus.SUCCEEDED,
                "progress": 1.0,
                "index_version_id": index_version_id,
                "updated_at": now,
            }
        )
        async with self._uow() as unit_of_work:
            await unit_of_work.document_versions.save(tenant_id=context.tenant_id, entity=ready)
            if retired is not None:
                await unit_of_work.document_versions.save(
                    tenant_id=context.tenant_id, entity=retired
                )
            await unit_of_work.documents.save_if_revision(
                tenant_id=context.tenant_id,
                entity=active,
                expected_revision=document.revision,
            )
            await unit_of_work.lifecycle_operations.save(
                tenant_id=context.tenant_id, entity=operation
            )
            await unit_of_work.commit()
        if retired is not None:
            await self._search.retire_document_version(
                context,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                document_version_id=retired.id,
            )
        return operation

    async def rollback(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        target_version_id: str,
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
            target = await unit_of_work.document_versions.get(
                tenant_id=context.tenant_id, resource_id=target_version_id
            )
        if document is None or target is None:
            raise KnowledgeNotFoundError("document_version", target_version_id)
        self._permission.require(context, document.authorization, PermissionAction.WRITE)
        fingerprint = sha256(
            "\x1f".join(
                (
                    LifecycleOperationKind.ROLLBACK.value,
                    document_id,
                    target_version_id,
                    reason,
                )
            ).encode()
        ).hexdigest()
        if duplicate is not None:
            if (
                duplicate.kind is not LifecycleOperationKind.ROLLBACK
                or duplicate.document_id != document_id
                or duplicate.version_id != target_version_id
                or duplicate.metadata.get("command_fingerprint") != fingerprint
            ):
                raise KnowledgeConflictError(
                    "idempotency key was already used for a different command",
                    error_code="lifecycle_idempotency_conflict",
                )
            return duplicate
        if (
            target.document_id != document.id
            or target.status is not DocumentVersionStatus.SUPERSEDED
        ):
            raise KnowledgeConflictError(
                "rollback target is not a retained historical version",
                error_code="rollback_target_invalid",
            )
        now = self._clock.now()
        operation = LifecycleOperation(
            id=self._ids.new_id(),
            tenant_id=context.tenant_id,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            version_id=target.id,
            kind=LifecycleOperationKind.ROLLBACK,
            idempotency_key=idempotency_key,
            actor_id=context.actor_id,
            reason=reason,
            request_id=context.request_id,
            expected_document_revision=document.revision,
            fencing_token=document.revision + 1,
            previous_version_id=document.current_version_id,
            metadata={"command_fingerprint": fingerprint},
            created_at=now,
            updated_at=now,
        )
        async with self._uow() as unit_of_work:
            await unit_of_work.lifecycle_operations.add(
                tenant_id=context.tenant_id, entity=operation
            )
            await unit_of_work.commit()
        return await self.complete_ingestion(
            context,
            operation_id=operation.id,
            index_version_id=target.index_version_id or f"idx_{target.id}",
        )

    async def _load(
        self, context: AuthorizationContext, operation_id: str
    ) -> tuple[LifecycleOperation, Document, DocumentVersion, DocumentVersion | None]:
        async with self._uow() as unit_of_work:
            operation = await unit_of_work.lifecycle_operations.get(
                tenant_id=context.tenant_id, resource_id=operation_id
            )
            if operation is None:
                raise KnowledgeNotFoundError("lifecycle_operation", operation_id)
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id, resource_id=operation.document_id
            )
            version = await unit_of_work.document_versions.get(
                tenant_id=context.tenant_id, resource_id=operation.version_id
            )
            previous = (
                await unit_of_work.document_versions.get(
                    tenant_id=context.tenant_id,
                    resource_id=operation.previous_version_id,
                )
                if operation.previous_version_id
                else None
            )
        if document is None or version is None:
            raise KnowledgeNotFoundError("document", operation.document_id)
        return operation, document, version, previous
