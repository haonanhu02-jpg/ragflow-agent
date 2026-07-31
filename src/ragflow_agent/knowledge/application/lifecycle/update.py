"""Immutable document update/reparse registration with transactional outbox."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import datetime
from hashlib import sha256

from pydantic import Field

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, PermissionAction
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.document import DocumentVersion
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError, KnowledgeNotFoundError
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionJob,
    IngestionStage,
    IngestionTask,
)
from ragflow_agent.knowledge.domain.lifecycle import (
    LifecycleOperation,
    LifecycleOperationKind,
    LifecycleOutboxEvent,
    LifecycleStep,
    LifecycleStepState,
    LifecycleStepStatus,
)
from ragflow_agent.knowledge.ports.permission import PermissionChecker
from ragflow_agent.knowledge.ports.storage import (
    ObjectStoragePort,
    StorageWriteRequest,
    StoredObject,
)
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class UpdateDocumentCommand(KnowledgeModel):
    context: AuthorizationContext
    document_id: NonEmptyStr
    file_name: NonEmptyStr
    media_type: NonEmptyStr
    content: bytes = Field(min_length=1)
    idempotency_key: NonEmptyStr
    reason: NonEmptyStr
    batch_id: str | None = None


class ReparseDocumentCommand(KnowledgeModel):
    context: AuthorizationContext
    document_id: NonEmptyStr
    idempotency_key: NonEmptyStr
    reason: NonEmptyStr
    batch_id: str | None = None


class SubmittedLifecycle(KnowledgeModel):
    operation: LifecycleOperation
    job: IngestionJob
    outbox_event: LifecycleOutboxEvent
    stored_object: StoredObject | None = None
    duplicate: bool = False


class DocumentUpdateService:
    """Create a new immutable version while leaving the active version untouched."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        storage: ObjectStoragePort,
        permission_checker: PermissionChecker,
        id_generator: IdGenerator,
        clock: Clock,
        max_upload_bytes: int,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._storage = storage
        self._permission_checker = permission_checker
        self._id_generator = id_generator
        self._clock = clock
        self._max_upload_bytes = max_upload_bytes

    async def update(self, command: UpdateDocumentCommand) -> SubmittedLifecycle:
        if len(command.content) > self._max_upload_bytes:
            raise KnowledgeConflictError(
                "update exceeds the configured byte limit",
                error_code="upload_too_large",
            )
        digest = sha256(command.content).hexdigest()
        fingerprint = self._fingerprint(
            LifecycleOperationKind.UPDATE,
            command.document_id,
            command.file_name,
            command.media_type,
            digest,
            command.reason,
            command.batch_id or "",
        )
        existing = await self._existing(
            command.context,
            document_id=command.document_id,
            idempotency_key=command.idempotency_key,
            kind=LifecycleOperationKind.UPDATE,
            fingerprint=fingerprint,
        )
        if existing is not None:
            return existing
        await self._require_document_write(command.context, command.document_id)
        version_id = self._id_generator.new_id()
        safe_name = _SAFE_NAME.sub("_", command.file_name).strip("._") or "source"
        object_key = (
            f"tenants/{command.context.tenant_id}/documents/{command.document_id}/"
            f"versions/{version_id}/{safe_name}"
        )
        stored = await self._storage.put(
            command.context,
            StorageWriteRequest(
                tenant_id=command.context.tenant_id,
                object_key=object_key,
                media_type=command.media_type,
                size_bytes=len(command.content),
                checksum_sha256=digest,
                trace_id=command.context.request_id,
            ),
            self._content(command.content),
        )
        return await self._register(
            context=command.context,
            document_id=command.document_id,
            version_id=version_id,
            object_key=object_key,
            media_type=command.media_type,
            content_hash=digest,
            size_bytes=len(command.content),
            idempotency_key=command.idempotency_key,
            reason=command.reason,
            kind=LifecycleOperationKind.UPDATE,
            stored_object=stored,
            batch_id=command.batch_id,
            command_fingerprint=fingerprint,
        )

    async def reparse(self, command: ReparseDocumentCommand) -> SubmittedLifecycle:
        fingerprint = self._fingerprint(
            LifecycleOperationKind.REPARSE,
            command.document_id,
            command.reason,
            command.batch_id or "",
        )
        existing = await self._existing(
            command.context,
            document_id=command.document_id,
            idempotency_key=command.idempotency_key,
            kind=LifecycleOperationKind.REPARSE,
            fingerprint=fingerprint,
        )
        if existing is not None:
            return existing
        async with self._unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.get(
                tenant_id=command.context.tenant_id,
                resource_id=command.document_id,
            )
            if document is None or document.current_version_id is None:
                raise KnowledgeNotFoundError("document", command.document_id)
            self._permission_checker.require(
                command.context,
                document.authorization,
                PermissionAction.WRITE,
            )
            current = await unit_of_work.document_versions.get(
                tenant_id=command.context.tenant_id,
                resource_id=document.current_version_id,
            )
        if current is None:
            raise KnowledgeNotFoundError("document_version", document.current_version_id)
        return await self._register(
            context=command.context,
            document_id=command.document_id,
            version_id=self._id_generator.new_id(),
            object_key=current.object_key,
            media_type=current.media_type,
            content_hash=current.content_hash,
            size_bytes=current.size_bytes,
            idempotency_key=command.idempotency_key,
            reason=command.reason,
            kind=LifecycleOperationKind.REPARSE,
            stored_object=None,
            batch_id=command.batch_id,
            command_fingerprint=fingerprint,
        )

    async def _register(
        self,
        *,
        context: AuthorizationContext,
        document_id: str,
        version_id: str,
        object_key: str,
        media_type: str,
        content_hash: str,
        size_bytes: int,
        idempotency_key: str,
        reason: str,
        kind: LifecycleOperationKind,
        stored_object: StoredObject | None,
        batch_id: str | None,
        command_fingerprint: str,
    ) -> SubmittedLifecycle:
        now = self._clock.now()
        operation_id = self._id_generator.new_id()
        job_id = self._job_id(context.tenant_id, idempotency_key)
        async with self._unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id,
                resource_id=document_id,
            )
            if document is None:
                raise KnowledgeNotFoundError("document", document_id)
            self._permission_checker.require(
                context,
                document.authorization,
                PermissionAction.WRITE,
            )
            if document.current_version_id is None:
                raise KnowledgeConflictError(
                    "document has no active version to replace",
                    error_code="document_has_no_active_version",
                )
            version = DocumentVersion(
                id=version_id,
                tenant_id=context.tenant_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                created_by=context.actor_id,
                object_key=object_key,
                media_type=media_type,
                content_hash=content_hash,
                size_bytes=size_bytes,
                created_at=now,
                updated_at=now,
            )
            operation = LifecycleOperation(
                id=operation_id,
                tenant_id=context.tenant_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                version_id=version.id,
                kind=kind,
                idempotency_key=idempotency_key,
                actor_id=context.actor_id,
                reason=reason,
                request_id=context.request_id,
                expected_document_revision=document.revision,
                fencing_token=document.revision + 1,
                previous_version_id=document.current_version_id,
                batch_id=batch_id,
                metadata={"command_fingerprint": command_fingerprint},
                steps=(
                    LifecycleStepState(
                        step=LifecycleStep.REGISTER,
                        status=LifecycleStepStatus.SUCCEEDED,
                        attempts=1,
                        started_at=now,
                        completed_at=now,
                    ),
                    LifecycleStepState(
                        step=LifecycleStep.STORE_OBJECT,
                        status=(
                            LifecycleStepStatus.SUCCEEDED
                            if stored_object is not None
                            else LifecycleStepStatus.SKIPPED
                        ),
                        attempts=1 if stored_object is not None else 0,
                        started_at=now,
                        completed_at=now,
                    ),
                ),
                created_at=now,
                updated_at=now,
            )
            job = IngestionJob(
                id=job_id,
                tenant_id=context.tenant_id,
                knowledge_base_id=document.knowledge_base_id,
                document_id=document.id,
                document_version_id=version.id,
                requested_by=context.actor_id,
                idempotency_key=f"lifecycle:{idempotency_key}",
                trace_id=context.request_id,
                operation_id=operation.id,
                created_at=now,
                updated_at=now,
            )
            tasks = self._tasks(job, idempotency_key, now)
            envelope = IngestionEnvelope.from_task(
                tasks[0],
                message_id=f"lifecycle-ingestion:{operation.id}",
                created_at=now,
            )
            event = LifecycleOutboxEvent(
                id=self._outbox_id(operation.id),
                tenant_id=context.tenant_id,
                operation_id=operation.id,
                aggregate_id=document.id,
                event_type="ingestion.requested",
                idempotency_key=f"outbox:{operation.id}:ingestion",
                payload={"envelope": envelope.model_dump(mode="json")},
                available_at=now,
                created_at=now,
                updated_at=now,
            )
            await unit_of_work.document_versions.add(tenant_id=context.tenant_id, entity=version)
            await unit_of_work.lifecycle_operations.add(
                tenant_id=context.tenant_id,
                entity=operation,
            )
            await unit_of_work.ingestion_jobs.add(tenant_id=context.tenant_id, entity=job)
            for task in tasks:
                await unit_of_work.ingestion_tasks.add(tenant_id=context.tenant_id, entity=task)
            await unit_of_work.lifecycle_outbox.add(tenant_id=context.tenant_id, entity=event)
            await unit_of_work.commit()
        return SubmittedLifecycle(
            operation=operation,
            job=job,
            outbox_event=event,
            stored_object=stored_object,
        )

    async def _existing(
        self,
        context: AuthorizationContext,
        *,
        document_id: str,
        idempotency_key: str,
        kind: LifecycleOperationKind,
        fingerprint: str,
    ) -> SubmittedLifecycle | None:
        async with self._unit_of_work_factory() as unit_of_work:
            operation = await unit_of_work.lifecycle_operations.get_by_idempotency_key(
                tenant_id=context.tenant_id,
                idempotency_key=idempotency_key,
            )
            if operation is None:
                return None
            if (
                operation.document_id != document_id
                or operation.kind is not kind
                or operation.metadata.get("command_fingerprint") != fingerprint
            ):
                raise KnowledgeConflictError(
                    "idempotency key was already used for a different command",
                    error_code="lifecycle_idempotency_conflict",
                )
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id,
                resource_id=operation.document_id,
            )
            job = await unit_of_work.ingestion_jobs.get(
                tenant_id=context.tenant_id,
                resource_id=self._job_id(context.tenant_id, idempotency_key),
            )
            event = await unit_of_work.lifecycle_outbox.get(
                tenant_id=context.tenant_id,
                resource_id=self._outbox_id(operation.id),
            )
        if document is None:
            raise KnowledgeNotFoundError("document", operation.document_id)
        self._permission_checker.require(
            context,
            document.authorization,
            PermissionAction.WRITE,
        )
        if job is None:
            raise KnowledgeConflictError(
                "lifecycle operation has no ingestion job",
                error_code="lifecycle_job_missing",
            )
        if event is None:
            raise KnowledgeConflictError(
                "lifecycle operation has no outbox event",
                error_code="lifecycle_outbox_missing",
            )
        return SubmittedLifecycle(
            operation=operation,
            job=job,
            outbox_event=event,
            duplicate=True,
        )

    async def _require_document_write(
        self,
        context: AuthorizationContext,
        document_id: str,
    ) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.get(
                tenant_id=context.tenant_id,
                resource_id=document_id,
            )
        if document is None:
            raise KnowledgeNotFoundError("document", document_id)
        self._permission_checker.require(
            context,
            document.authorization,
            PermissionAction.WRITE,
        )

    @staticmethod
    def _fingerprint(kind: LifecycleOperationKind, *parts: str) -> str:
        payload = "\x1f".join((kind.value, *parts)).encode()
        return sha256(payload).hexdigest()

    @staticmethod
    def _tasks(job: IngestionJob, key: str, now: datetime) -> tuple[IngestionTask, ...]:
        return tuple(
            IngestionTask(
                id=f"{job.id}:{stage.value}",
                tenant_id=job.tenant_id,
                job_id=job.id,
                document_version_id=job.document_version_id,
                stage=stage,
                idempotency_key=f"{key}:{stage.value}",
                trace_id=job.trace_id,
                created_at=now,
                updated_at=now,
            )
            for stage in (
                IngestionStage.PARSE,
                IngestionStage.CHUNK,
                IngestionStage.EMBED,
                IngestionStage.INDEX,
            )
        )

    @staticmethod
    async def _content(content: bytes) -> AsyncIterator[bytes]:
        yield content

    @staticmethod
    def _job_id(tenant_id: str, idempotency_key: str) -> str:
        digest = sha256(f"{tenant_id}\x1f{idempotency_key}".encode()).hexdigest()
        return f"lifecycle_job_{digest[:24]}"

    @staticmethod
    def _outbox_id(operation_id: str) -> str:
        return f"outbox:{operation_id}"
