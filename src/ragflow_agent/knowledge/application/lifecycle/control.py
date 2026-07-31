"""Tenant-scoped lifecycle operation read and cooperative cancellation."""

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, PermissionAction
from ragflow_agent.knowledge.domain.errors import KnowledgeNotFoundError
from ragflow_agent.knowledge.domain.lifecycle import (
    TERMINAL_LIFECYCLE_STATUSES,
    LifecycleOperation,
    LifecycleOperationStatus,
)
from ragflow_agent.knowledge.ports.permission import PermissionChecker
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock


class LifecycleControlService:
    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        permission_checker: PermissionChecker,
        clock: Clock,
    ) -> None:
        self._uow = unit_of_work_factory
        self._permission = permission_checker
        self._clock = clock

    async def get(self, context: AuthorizationContext, operation_id: str) -> LifecycleOperation:
        async with self._uow() as unit_of_work:
            operation = await unit_of_work.lifecycle_operations.get(
                tenant_id=context.tenant_id, resource_id=operation_id
            )
            document = (
                await unit_of_work.documents.get(
                    tenant_id=context.tenant_id,
                    resource_id=operation.document_id,
                )
                if operation is not None
                else None
            )
        if operation is None or document is None:
            raise KnowledgeNotFoundError("lifecycle_operation", operation_id)
        self._permission.require(context, document.authorization, PermissionAction.READ)
        return operation

    async def cancel(self, context: AuthorizationContext, operation_id: str) -> LifecycleOperation:
        operation = await self.get(context, operation_id)
        if operation.status in TERMINAL_LIFECYCLE_STATUSES:
            return operation
        async with self._uow() as unit_of_work:
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id, resource_id=operation.document_id
            )
            if document is None:
                raise KnowledgeNotFoundError("document", operation.document_id)
            self._permission.require(context, document.authorization, PermissionAction.WRITE)
            cancelled = operation.model_copy(
                update={
                    "status": LifecycleOperationStatus.CANCEL_REQUESTED,
                    "updated_at": self._clock.now(),
                }
            )
            await unit_of_work.lifecycle_operations.save(
                tenant_id=context.tenant_id, entity=cancelled
            )
            await unit_of_work.commit()
        return cancelled
