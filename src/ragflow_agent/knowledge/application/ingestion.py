"""Minimum parse → chunk → embed → index Worker pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.document import (
    Document,
    DocumentVersion,
    DocumentVersionStatus,
    activate_document_version,
    transition_document_version,
)
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionError,
    IngestionJob,
    IngestionStage,
    IngestionStatus,
    IngestionTask,
    retry_ingestion_task,
    transition_ingestion,
)
from ragflow_agent.knowledge.domain.retrieval import (
    EmbeddingMetadata,
    IndexRecord,
    IndexVersion,
    IndexVersionStatus,
)
from ragflow_agent.knowledge.ports.chunking import ChunkerPort, ChunkingRequest
from ragflow_agent.knowledge.ports.embedding import EmbeddingInput, EmbeddingPort, EmbeddingRequest
from ragflow_agent.knowledge.ports.parsing import ParseRequest, ParserPort
from ragflow_agent.knowledge.ports.search import SearchIndexPort
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock


class RetryableIngestionError(RuntimeError):
    """Tell the transport that persisted stage state allows another delivery."""


@dataclass(frozen=True, slots=True)
class IngestionProfile:
    """Frozen minimum parser/chunker/embedding profile."""

    chunk_strategy_id: str
    chunk_strategy_version: str
    chunk_max_tokens: int
    embedding_model_id: str


class IngestionPipeline:
    """Execute one persisted tenant-scoped ingestion job."""

    def __init__(
        self,
        *,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        parser: ParserPort,
        chunker: ChunkerPort,
        embedding: EmbeddingPort,
        search: SearchIndexPort,
        clock: Clock,
        profile: IngestionProfile,
        max_attempts: int,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._parser = parser
        self._chunker = chunker
        self._embedding = embedding
        self._search = search
        self._clock = clock
        self._profile = profile
        self._max_attempts = max_attempts

    async def handle(
        self,
        envelope: IngestionEnvelope,
        *,
        delivery_attempt: int = 1,
    ) -> IngestionJob:
        context = AuthorizationContext(
            tenant_id=envelope.tenant_id,
            actor_id="ingestion-worker",
            request_id=envelope.trace_id,
        )
        job, tasks, document, version = await self._load(envelope)
        if job.status is IngestionStatus.SUCCEEDED:
            return job
        try:
            if job.status is IngestionStatus.PENDING:
                job = transition_ingestion(
                    job,
                    IngestionStatus.RUNNING,
                    progress=job.progress,
                    changed_at=self._clock.now(),
                )
                await self._save_job(job)
            if version.status is DocumentVersionStatus.REGISTERED:
                version = transition_document_version(
                    version,
                    DocumentVersionStatus.INGESTING,
                    changed_at=self._clock.now(),
                )
                await self._save_version(version)

            parse_task = self._task(tasks, IngestionStage.PARSE)
            parse_task = await self._start_task(parse_task)
            parsed = await self._parser.parse(
                ParseRequest(
                    tenant_id=job.tenant_id,
                    knowledge_base_id=job.knowledge_base_id,
                    document_id=job.document_id,
                    document_version_id=job.document_version_id,
                    object_key=version.object_key,
                    media_type=version.media_type,
                    trace_id=job.trace_id,
                )
            )
            await self._succeed_task(parse_task)
            job = await self._progress(job, 0.25)

            chunk_task = await self._start_task(self._task(tasks, IngestionStage.CHUNK))
            chunks = await self._chunker.chunk(
                context,
                ChunkingRequest(
                    parsed_document=parsed,
                    strategy_id=self._profile.chunk_strategy_id,
                    strategy_version=self._profile.chunk_strategy_version,
                    max_tokens=self._profile.chunk_max_tokens,
                    trace_id=job.trace_id,
                ),
            )
            if not chunks:
                raise KnowledgeConflictError(
                    "chunker produced no searchable content",
                    error_code="chunk_empty_result",
                )
            await self._succeed_task(chunk_task)
            job = await self._progress(job, 0.5)

            embed_task = await self._start_task(self._task(tasks, IngestionStage.EMBED))
            embedded = await self._embedding.embed(
                context,
                EmbeddingRequest(
                    tenant_id=job.tenant_id,
                    model_id=self._profile.embedding_model_id,
                    inputs=tuple(
                        EmbeddingInput(id=chunk.id, text=chunk.content) for chunk in chunks
                    ),
                    trace_id=job.trace_id,
                ),
            )
            vector_by_id = {vector.input_id: vector.values for vector in embedded.vectors}
            if set(vector_by_id) != {chunk.id for chunk in chunks}:
                raise KnowledgeConflictError(
                    "embedding result does not cover every chunk",
                    error_code="embedding_partial_result",
                )
            await self._succeed_task(embed_task)
            job = await self._progress(job, 0.75)

            index_task = await self._start_task(self._task(tasks, IngestionStage.INDEX))
            index_version = IndexVersion(
                id=f"idx_{job.document_version_id}",
                tenant_id=job.tenant_id,
                knowledge_base_id=job.knowledge_base_id,
                embedding=EmbeddingMetadata(
                    model_id=embedded.model_id,
                    dimensions=embedded.dimensions,
                    normalized=embedded.normalized,
                ),
                status=IndexVersionStatus.BUILDING,
                created_at=self._clock.now(),
            )
            records = tuple(
                IndexRecord(
                    index_version_id=index_version.id,
                    tenant_id=chunk.tenant_id,
                    knowledge_base_id=chunk.knowledge_base_id,
                    owner_id=document.owner_id,
                    visibility=document.visibility,
                    document_id=chunk.document_id,
                    document_version_id=chunk.document_version_id,
                    chunk_id=chunk.id,
                    content=chunk.content,
                    media_type=version.media_type,
                    created_at=self._clock.now(),
                    embedding=vector_by_id[chunk.id],
                    metadata=chunk.metadata,
                )
                for chunk in chunks
            )
            await self._search.upsert(context, index_version, records)
            await self._search.activate(context, index_version)
            await self._succeed_task(index_task)

            version = transition_document_version(
                version,
                DocumentVersionStatus.READY,
                changed_at=self._clock.now(),
            )
            document = activate_document_version(
                document,
                version,
                changed_at=self._clock.now(),
            )
            job = transition_ingestion(
                job,
                IngestionStatus.SUCCEEDED,
                progress=1,
                changed_at=self._clock.now(),
            )
            async with self._unit_of_work_factory() as unit_of_work:
                await unit_of_work.document_versions.save(
                    tenant_id=job.tenant_id,
                    entity=version,
                )
                await unit_of_work.documents.save(
                    tenant_id=job.tenant_id,
                    entity=document,
                )
                await unit_of_work.ingestion_jobs.save(
                    tenant_id=job.tenant_id,
                    entity=job,
                )
                await unit_of_work.commit()
            return job
        except Exception as error:
            await self._record_failure(
                envelope,
                job,
                delivery_attempt=delivery_attempt,
                error=error,
            )
            if delivery_attempt < self._max_attempts:
                raise RetryableIngestionError(str(error)) from error
            raise

    async def _load(
        self,
        envelope: IngestionEnvelope,
    ) -> tuple[IngestionJob, tuple[IngestionTask, ...], Document, DocumentVersion]:
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.ingestion_jobs.get(
                tenant_id=envelope.tenant_id,
                resource_id=envelope.job_id,
            )
            tasks = await unit_of_work.ingestion_tasks.list_for_job(
                tenant_id=envelope.tenant_id,
                job_id=envelope.job_id,
            )
            version = await unit_of_work.document_versions.get(
                tenant_id=envelope.tenant_id,
                resource_id=envelope.document_version_id,
            )
            document = (
                await unit_of_work.documents.get(
                    tenant_id=envelope.tenant_id,
                    resource_id=job.document_id,
                )
                if job is not None
                else None
            )
        if job is None:
            raise KnowledgeNotFoundError("ingestion_job", envelope.job_id)
        if version is None or document is None:
            raise KnowledgeNotFoundError("document_version", envelope.document_version_id)
        if (
            job.tenant_id,
            job.document_version_id,
            envelope.task_id,
        ) != (
            envelope.tenant_id,
            envelope.document_version_id,
            f"{job.id}:{IngestionStage.PARSE.value}",
        ):
            raise KnowledgeConflictError(
                "queue envelope does not match persisted ingestion facts",
                error_code="ingestion_envelope_scope_mismatch",
            )
        return job, tasks, document, version

    @staticmethod
    def _task(
        tasks: tuple[IngestionTask, ...],
        stage: IngestionStage,
    ) -> IngestionTask:
        for task in tasks:
            if task.stage is stage:
                return task
        raise KnowledgeNotFoundError("ingestion_task", stage.value)

    async def _start_task(self, task: IngestionTask) -> IngestionTask:
        if task.status is IngestionStatus.SUCCEEDED:
            return task
        if task.status is IngestionStatus.FAILED:
            task = retry_ingestion_task(task, changed_at=self._clock.now())
        elif task.status is IngestionStatus.PENDING:
            task = transition_ingestion(
                task,
                IngestionStatus.RUNNING,
                progress=task.progress,
                changed_at=self._clock.now(),
            )
        await self._save_task(task)
        return task

    async def _succeed_task(self, task: IngestionTask) -> None:
        if task.status is IngestionStatus.SUCCEEDED:
            return
        succeeded = transition_ingestion(
            task,
            IngestionStatus.SUCCEEDED,
            progress=1,
            changed_at=self._clock.now(),
        )
        await self._save_task(succeeded)

    async def _progress(self, job: IngestionJob, progress: float) -> IngestionJob:
        updated = job.model_copy(update={"progress": progress, "updated_at": self._clock.now()})
        await self._save_job(updated)
        return updated

    async def _record_failure(
        self,
        envelope: IngestionEnvelope,
        job: IngestionJob,
        *,
        delivery_attempt: int,
        error: Exception,
    ) -> None:
        tasks = await self._tasks(envelope.tenant_id, envelope.job_id)
        running = next(
            (task for task in tasks if task.status is IngestionStatus.RUNNING),
            None,
        )
        retryable = delivery_attempt < self._max_attempts
        failure = IngestionError(
            code=getattr(error, "error_code", "ingestion_stage_failed"),
            message=str(error) or type(error).__name__,
            retryable=retryable,
        )
        if running is not None:
            failed_task = transition_ingestion(
                running,
                IngestionStatus.FAILED,
                progress=running.progress,
                changed_at=self._clock.now(),
                error=failure,
            )
            await self._save_task(failed_task)
        if not retryable and job.status is IngestionStatus.RUNNING:
            failed_job = transition_ingestion(
                job,
                IngestionStatus.FAILED,
                progress=job.progress,
                changed_at=self._clock.now(),
                error=failure,
            )
            await self._save_job(failed_job)
            async with self._unit_of_work_factory() as unit_of_work:
                version = await unit_of_work.document_versions.get(
                    tenant_id=envelope.tenant_id,
                    resource_id=envelope.document_version_id,
                )
                if version is not None and version.status is DocumentVersionStatus.INGESTING:
                    failed_version = transition_document_version(
                        version,
                        DocumentVersionStatus.FAILED,
                        changed_at=self._clock.now(),
                    )
                    await unit_of_work.document_versions.save(
                        tenant_id=envelope.tenant_id,
                        entity=failed_version,
                    )
                    await unit_of_work.commit()

    async def _tasks(self, tenant_id: str, job_id: str) -> tuple[IngestionTask, ...]:
        async with self._unit_of_work_factory() as unit_of_work:
            return await unit_of_work.ingestion_tasks.list_for_job(
                tenant_id=tenant_id,
                job_id=job_id,
            )

    async def _save_job(self, job: IngestionJob) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.ingestion_jobs.save(tenant_id=job.tenant_id, entity=job)
            await unit_of_work.commit()

    async def _save_task(self, task: IngestionTask) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.ingestion_tasks.save(tenant_id=task.tenant_id, entity=task)
            await unit_of_work.commit()

    async def _save_version(self, version: DocumentVersion) -> None:
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.document_versions.save(
                tenant_id=version.tenant_id,
                entity=version,
            )
            await unit_of_work.commit()
