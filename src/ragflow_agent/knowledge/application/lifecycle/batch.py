"""Tenant-scoped batch aggregation with child-operation fault isolation."""

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleBatch,
    LifecycleBatchStatus,
    LifecycleOperationKind,
    LifecycleOperationStatus,
)
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock


class LifecycleBatchService:
    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        id_generator: IdGenerator,
        clock: Clock,
        max_concurrency: int = 3,
    ) -> None:
        self._uow = unit_of_work_factory
        self._ids = id_generator
        self._clock = clock
        self._max_concurrency = max_concurrency

    async def create(
        self,
        context: AuthorizationContext,
        *,
        knowledge_base_id: str,
        kind: LifecycleOperationKind,
        operation_ids: tuple[str, ...],
        idempotency_key: str,
        concurrency: int | None = None,
    ) -> LifecycleBatch:
        async with self._uow() as unit_of_work:
            duplicate = await unit_of_work.lifecycle_batches.get_by_idempotency_key(
                tenant_id=context.tenant_id, idempotency_key=idempotency_key
            )
            requested_concurrency = min(
                self._max_concurrency if concurrency is None else concurrency,
                self._max_concurrency,
            )
            if duplicate is not None:
                if (
                    duplicate.requested_by != context.actor_id
                    or duplicate.knowledge_base_id != knowledge_base_id
                    or duplicate.kind is not kind
                    or duplicate.operation_ids != operation_ids
                    or duplicate.concurrency != requested_concurrency
                ):
                    raise KnowledgeConflictError(
                        "idempotency key was already used for a different batch",
                        error_code="lifecycle_idempotency_conflict",
                    )
                return duplicate
            for operation_id in operation_ids:
                operation = await unit_of_work.lifecycle_operations.get(
                    tenant_id=context.tenant_id, resource_id=operation_id
                )
                if (
                    operation is None
                    or operation.knowledge_base_id != knowledge_base_id
                    or operation.kind is not kind
                    or operation.actor_id != context.actor_id
                ):
                    raise KnowledgeConflictError(
                        "batch child crosses tenant or knowledge-base scope",
                        error_code="batch_scope_mismatch",
                    )
            now = self._clock.now()
            batch = LifecycleBatch(
                id=self._ids.new_id(),
                tenant_id=context.tenant_id,
                knowledge_base_id=knowledge_base_id,
                kind=kind,
                requested_by=context.actor_id,
                idempotency_key=idempotency_key,
                operation_ids=operation_ids,
                concurrency=requested_concurrency,
                created_at=now,
                updated_at=now,
            )
            await unit_of_work.lifecycle_batches.add(tenant_id=context.tenant_id, entity=batch)
            await unit_of_work.commit()
        return batch

    async def refresh(self, context: AuthorizationContext, batch_id: str) -> LifecycleBatch:
        async with self._uow() as unit_of_work:
            batch = await unit_of_work.lifecycle_batches.get(
                tenant_id=context.tenant_id, resource_id=batch_id
            )
            if batch is None:
                raise KnowledgeNotFoundError("lifecycle_batch", batch_id)
            if batch.requested_by != context.actor_id:
                raise KnowledgeAuthorizationError(
                    reason_code="lifecycle_batch_owner_required",
                    trace_id=context.request_id,
                )
            operations = []
            for operation_id in batch.operation_ids:
                operation = await unit_of_work.lifecycle_operations.get(
                    tenant_id=context.tenant_id, resource_id=operation_id
                )
                if operation is not None:
                    operations.append(operation)
            succeeded = sum(
                item.status is LifecycleOperationStatus.SUCCEEDED for item in operations
            )
            failed = sum(
                item.status
                in {LifecycleOperationStatus.FAILED, LifecycleOperationStatus.DEAD_LETTER}
                for item in operations
            )
            cancelled = sum(
                item.status is LifecycleOperationStatus.CANCELLED for item in operations
            )
            terminal = succeeded + failed + cancelled
            if terminal < len(batch.operation_ids):
                status = LifecycleBatchStatus.RUNNING
            elif cancelled == len(batch.operation_ids):
                status = LifecycleBatchStatus.CANCELLED
            elif succeeded == len(batch.operation_ids):
                status = LifecycleBatchStatus.SUCCEEDED
            elif succeeded:
                status = LifecycleBatchStatus.PARTIAL_SUCCESS
            else:
                status = LifecycleBatchStatus.FAILED
            refreshed = batch.model_copy(
                update={
                    "status": status,
                    "succeeded": succeeded,
                    "failed": failed,
                    "cancelled": cancelled,
                    "updated_at": self._clock.now(),
                }
            )
            await unit_of_work.lifecycle_batches.save(tenant_id=context.tenant_id, entity=refreshed)
            await unit_of_work.commit()
        return refreshed
