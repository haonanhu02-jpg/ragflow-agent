"""Secure source upload, persistent ingestion facts, and post-commit enqueue."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from hashlib import sha256

from pydantic import Field

from ragflow_agent.knowledge.application.knowledge_service import (
    KnowledgeService,
    RegisterDocumentCommand,
)
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionJob,
    IngestionStage,
    IngestionStatus,
    IngestionTask,
)
from ragflow_agent.knowledge.ports.queue import IngestionQueuePort, QueueReceipt
from ragflow_agent.knowledge.ports.storage import (
    ObjectStoragePort,
    StorageWriteRequest,
    StoredObject,
)
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock

ALLOWED_UPLOAD_MEDIA_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "text/html",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "image/png",
        "image/jpeg",
        "image/tiff",
        "image/webp",
        "image/bmp",
    }
)
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class UploadDocumentCommand(KnowledgeModel):
    """One bounded, tenant-authorized immutable source upload."""

    context: AuthorizationContext
    knowledge_base_id: NonEmptyStr
    file_name: NonEmptyStr
    media_type: NonEmptyStr
    content: bytes = Field(min_length=1)
    idempotency_key: NonEmptyStr
    visibility: Visibility | None = None


class SubmittedIngestion(KnowledgeModel):
    """Stable response returned before background ingestion completes."""

    job: IngestionJob
    stored_object: StoredObject | None
    queue_receipt: QueueReceipt | None
    duplicate: bool = False


class UploadService:
    """Persist source and business state before publishing one ARQ command."""

    def __init__(
        self,
        *,
        knowledge_service: KnowledgeService,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        storage: ObjectStoragePort,
        queue: IngestionQueuePort,
        id_generator: IdGenerator,
        clock: Clock,
        max_upload_bytes: int,
    ) -> None:
        self._knowledge_service = knowledge_service
        self._unit_of_work_factory = unit_of_work_factory
        self._storage = storage
        self._queue = queue
        self._id_generator = id_generator
        self._clock = clock
        self._max_upload_bytes = max_upload_bytes

    async def submit(self, command: UploadDocumentCommand) -> SubmittedIngestion:
        self._validate_upload(command)
        job_id = self._job_id(command.context.tenant_id, command.idempotency_key)
        async with self._unit_of_work_factory() as unit_of_work:
            existing = await unit_of_work.ingestion_jobs.get(
                tenant_id=command.context.tenant_id,
                resource_id=job_id,
            )
        if existing is not None:
            if existing.knowledge_base_id != command.knowledge_base_id:
                raise KnowledgeConflictError(
                    "idempotency key is already bound to another knowledge base",
                    error_code="upload_idempotency_scope_conflict",
                )
            receipt = await self._republish_pending(command.context, existing)
            return SubmittedIngestion(
                job=existing,
                stored_object=None,
                queue_receipt=receipt,
                duplicate=True,
            )

        now = self._clock.now()
        digest = sha256(command.content).hexdigest()
        safe_name = _SAFE_NAME.sub("_", command.file_name).strip("._") or "source"
        object_key = f"tenants/{command.context.tenant_id}/uploads/{job_id}/{safe_name}"
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
        registered = await self._knowledge_service.register_document(
            RegisterDocumentCommand(
                context=command.context,
                knowledge_base_id=command.knowledge_base_id,
                name=command.file_name,
                object_key=object_key,
                media_type=command.media_type,
                content_hash=digest,
                size_bytes=len(command.content),
                visibility=command.visibility,
            )
        )
        job = IngestionJob(
            id=job_id,
            tenant_id=command.context.tenant_id,
            knowledge_base_id=command.knowledge_base_id,
            document_id=registered.document.id,
            document_version_id=registered.version.id,
            requested_by=command.context.actor_id,
            idempotency_key=command.idempotency_key,
            trace_id=command.context.request_id,
            created_at=now,
            updated_at=now,
        )
        tasks = tuple(
            IngestionTask(
                id=f"{job_id}:{stage.value}",
                tenant_id=job.tenant_id,
                job_id=job.id,
                document_version_id=job.document_version_id,
                stage=stage,
                idempotency_key=f"{command.idempotency_key}:{stage.value}",
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
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.ingestion_jobs.add(tenant_id=job.tenant_id, entity=job)
            for task in tasks:
                await unit_of_work.ingestion_tasks.add(tenant_id=job.tenant_id, entity=task)
            await unit_of_work.commit()

        first_task = tasks[0]
        envelope = IngestionEnvelope.from_task(
            first_task,
            message_id=f"ingestion:{job.id}",
            created_at=now,
        )
        receipt = await self._queue.publish(command.context, envelope)
        return SubmittedIngestion(
            job=job,
            stored_object=stored,
            queue_receipt=receipt,
        )

    async def get_job(
        self,
        context: AuthorizationContext,
        job_id: str,
    ) -> IngestionJob:
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.ingestion_jobs.get(
                tenant_id=context.tenant_id,
                resource_id=job_id,
            )
        if job is None:
            raise KnowledgeNotFoundError("ingestion_job", job_id, trace_id=context.request_id)
        return job

    async def _republish_pending(
        self,
        context: AuthorizationContext,
        job: IngestionJob,
    ) -> QueueReceipt | None:
        """Recover a post-commit queue failure through the same idempotency key."""
        if job.status is not IngestionStatus.PENDING:
            return None
        async with self._unit_of_work_factory() as unit_of_work:
            tasks = await unit_of_work.ingestion_tasks.list_for_job(
                tenant_id=context.tenant_id,
                job_id=job.id,
            )
        parse_task = next(
            (task for task in tasks if task.stage is IngestionStage.PARSE),
            None,
        )
        if parse_task is None:
            raise KnowledgeConflictError(
                "pending ingestion job has no parse task",
                error_code="ingestion_parse_task_missing",
            )
        envelope = IngestionEnvelope.from_task(
            parse_task,
            message_id=f"ingestion:{job.id}",
            created_at=self._clock.now(),
        )
        return await self._queue.publish(context, envelope)

    def _validate_upload(self, command: UploadDocumentCommand) -> None:
        if command.media_type not in ALLOWED_UPLOAD_MEDIA_TYPES:
            raise KnowledgeConflictError(
                "upload media type is not supported by the Phase 05 parser profile",
                error_code="upload_media_type_unsupported",
                details={"media_type": command.media_type},
            )
        if len(command.content) > self._max_upload_bytes:
            raise KnowledgeConflictError(
                "upload exceeds the configured byte limit",
                error_code="upload_too_large",
            )

    @staticmethod
    async def _content(payload: bytes) -> AsyncIterator[bytes]:
        yield payload

    @staticmethod
    def _job_id(tenant_id: str, idempotency_key: str) -> str:
        digest = sha256(f"{tenant_id}\x1f{idempotency_key}".encode()).hexdigest()
        return f"job_{digest[:32]}"
