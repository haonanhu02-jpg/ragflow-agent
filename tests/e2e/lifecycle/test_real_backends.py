"""Real PostgreSQL, Redis, MinIO, and Elasticsearch lifecycle vertical slice."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from pydantic import SecretStr
from redis.asyncio import Redis
from sqlalchemy import text

from ragflow_agent.config import (
    DatabaseSettings,
    ObjectStoreSettings,
    QueueSettings,
    SearchSettings,
)
from ragflow_agent.infrastructure.database import create_database_engine, create_session_factory
from ragflow_agent.knowledge.application.ingestion import IngestionPipeline, IngestionProfile
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeQueryService,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.lifecycle.delete import DocumentDeletionService
from ragflow_agent.knowledge.application.lifecycle.publish import DocumentVersionPublisher
from ragflow_agent.knowledge.application.lifecycle.rebuild import IndexRebuildService
from ragflow_agent.knowledge.application.lifecycle.update import (
    DocumentUpdateService,
    UpdateDocumentCommand,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.chunk import ChunkMetadata
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope, IngestionStage
from ragflow_agent.knowledge.domain.lifecycle import IndexGeneration
from ragflow_agent.knowledge.domain.retrieval import (
    IndexRecord,
    RetrievalEmptyReason,
    RetrievalQuery,
)
from ragflow_agent.knowledge.domain.retry import RetryPolicy
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker
from ragflow_agent.knowledge.infrastructure.database import SqlAlchemyKnowledgeUnitOfWorkFactory
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.infrastructure.parsers import BasicObjectParser
from ragflow_agent.knowledge.infrastructure.queue import ArqIngestionQueue
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace
from ragflow_agent.knowledge.ports.storage import StoredObject
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock
from ragflow_agent.worker.outbox import LifecycleOutboxDispatcher
from tests.fakes.minimum_rag import KeywordEmbedding


def _environment() -> dict[str, str]:
    names = (
        "RAGFLOW_AGENT_TEST_DATABASE_URL",
        "RAGFLOW_AGENT_TEST_REDIS_URL",
        "RAGFLOW_AGENT_TEST_S3_ENDPOINT_URL",
        "RAGFLOW_AGENT_TEST_S3_ACCESS_KEY",
        "RAGFLOW_AGENT_TEST_S3_SECRET_KEY",
        "RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL",
    )
    values = {name: os.environ.get(name, "") for name in names}
    if any(not value for value in values.values()):
        pytest.skip("complete Phase 07 real-backend environment is not configured")
    return values


@pytest.mark.asyncio
async def test_real_lifecycle_update_publish_delete_and_purge() -> None:
    environment = _environment()
    suffix = uuid4().hex
    tenant_id = f"tenant-p07-{suffix}"
    queue_name = f"arq:ragflow-agent:p07:{suffix}"
    index_name = f"ragflow-agent-p07-{suffix}"
    engine = create_database_engine(
        DatabaseSettings(url=SecretStr(environment["RAGFLOW_AGENT_TEST_DATABASE_URL"]))
    )
    factory = SqlAlchemyKnowledgeUnitOfWorkFactory(create_session_factory(engine))
    storage = S3ObjectStorage(
        ObjectStoreSettings(
            endpoint_url=environment["RAGFLOW_AGENT_TEST_S3_ENDPOINT_URL"],
            bucket="ragflow-agent-phase07-tests",
            access_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_ACCESS_KEY"]),
            secret_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_SECRET_KEY"]),
        )
    )
    queue = ArqIngestionQueue(
        QueueSettings(
            url=SecretStr(environment["RAGFLOW_AGENT_TEST_REDIS_URL"]),
            queue_name=queue_name,
        )
    )
    embedding = KeywordEmbedding(dimensions=16)
    client = AsyncElasticsearch(
        environment["RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL"], verify_certs=False
    )
    search = ElasticsearchSearchAdapter(
        SearchSettings(
            url=SecretStr(environment["RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL"]),
            index_name=index_name,
            verify_certs=False,
        ),
        embedding=embedding,
        embedding_model_id=embedding.model_id,
        embedding_dimensions=embedding.dimensions,
        client=client,
    )
    clock = SystemClock()
    permission = DefaultPermissionChecker()
    context = AuthorizationContext(
        tenant_id=tenant_id,
        actor_id="owner-a",
        request_id=f"request-{suffix}",
    )
    ids = Uuid4Generator()
    try:
        await storage.ensure_bucket()
        await search.ensure_index()
        await queue.open()
        knowledge = KnowledgeService(
            unit_of_work_factory=factory,
            permission_checker=permission,
            id_generator=ids,
            clock=clock,
            trace=LoggingKnowledgeTrace(),
        )
        knowledge_base = await knowledge.create_knowledge_base(
            CreateKnowledgeBaseCommand(
                context=context,
                name="Phase 07 isolated lifecycle",
                visibility=Visibility.TENANT,
            )
        )
        submitted = await UploadService(
            knowledge_service=knowledge,
            unit_of_work_factory=factory,
            storage=storage,
            queue=queue,
            id_generator=ids,
            clock=clock,
            max_upload_bytes=4096,
        ).submit(
            UploadDocumentCommand(
                context=context,
                knowledge_base_id=knowledge_base.id,
                file_name="manual.md",
                media_type="text/markdown",
                content=b"old controller procedure",
                idempotency_key=f"initial-{suffix}",
            )
        )
        async with factory() as unit_of_work:
            tasks = await unit_of_work.ingestion_tasks.list_for_job(
                tenant_id=tenant_id, job_id=submitted.job.id
            )
        parse_task = next(item for item in tasks if item.stage is IngestionStage.PARSE)
        profile = IngestionProfile(
            chunk_strategy_id="general",
            chunk_strategy_version="1",
            chunk_max_tokens=16,
            embedding_model_id=embedding.model_id,
        )
        parser = BasicObjectParser(
            storage=storage,
            unit_of_work_factory=factory,
            clock=clock,
            max_bytes=4096,
        )
        chunker = GeneralChunker(max_tokens=16, overlap_tokens=2)
        await IngestionPipeline(
            unit_of_work_factory=factory,
            parser=parser,
            chunker=chunker,
            embedding=embedding,
            search=search,
            clock=clock,
            profile=profile,
            max_attempts=6,
        ).handle(
            IngestionEnvelope.from_task(
                parse_task,
                message_id=f"initial:{suffix}",
                created_at=datetime.now(UTC),
            )
        )
        publisher = DocumentVersionPublisher(
            unit_of_work_factory=factory,
            search=search,
            clock=clock,
            id_generator=ids,
            permission_checker=permission,
        )
        update = await DocumentUpdateService(
            unit_of_work_factory=factory,
            storage=storage,
            permission_checker=permission,
            id_generator=ids,
            clock=clock,
            max_upload_bytes=4096,
        ).update(
            UpdateDocumentCommand(
                context=context,
                document_id=submitted.job.document_id,
                file_name="manual-v2.md",
                media_type="text/markdown",
                content=b"new controller reset evidence",
                idempotency_key=f"update-{suffix}",
                reason="source revision",
            )
        )
        await LifecycleOutboxDispatcher(
            unit_of_work_factory=factory,
            queue=queue,
            clock=clock,
            retry_policy=RetryPolicy(),
        ).dispatch_due(context)
        envelope = IngestionEnvelope.model_validate(update.outbox_event.payload["envelope"])
        await IngestionPipeline(
            unit_of_work_factory=factory,
            parser=parser,
            chunker=chunker,
            embedding=embedding,
            search=search,
            clock=clock,
            profile=profile,
            max_attempts=6,
            lifecycle_activation=publisher,
        ).handle(envelope)
        query_service = KnowledgeQueryService(
            unit_of_work_factory=factory,
            permission_checker=permission,
            retriever=search,
        )
        result = await query_service.retrieve(
            context,
            RetrievalQuery(
                tenant_id=tenant_id,
                text="new controller reset",
                knowledge_base_ids=(knowledge_base.id,),
                trace_id=f"query-{suffix}",
            ),
        )
        assert result.candidates
        assert {item.document_version_id for item in result.candidates} == {
            update.operation.version_id
        }
        generation = IndexGeneration(
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base.id,
            generation=2,
            physical_index=f"{index_name}-generation-2",
            read_alias=f"{index_name}-read",
            write_alias=f"{index_name}-write",
            fencing_token=2,
            expected_chunks=1,
            mapping_version="2",
            created_at=datetime.now(UTC),
        )
        generation_record = IndexRecord(
            index_version_id="generation-2",
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base.id,
            owner_id=context.actor_id,
            visibility=Visibility.PRIVATE,
            document_id=submitted.job.document_id,
            document_version_id=update.operation.version_id,
            chunk_id=f"generation-chunk-{suffix}",
            content="generation validation evidence",
            media_type="text/plain",
            created_at=datetime.now(UTC),
            embedding=embedding.vector("generation validation evidence"),
            metadata=ChunkMetadata(),
        )
        validation = await IndexRebuildService(search).build_and_publish(
            context,
            generation,
            (generation_record,),
            expected_current=None,
        )
        assert validation.healthy
        assert (
            await search.resolve_alias(context, alias=generation.read_alias)
            == generation.physical_index
        )
        deletion = DocumentDeletionService(
            unit_of_work_factory=factory,
            search=search,
            storage=storage,
            permission_checker=permission,
            id_generator=ids,
            clock=clock,
            retention_days=0,
        )
        await deletion.request_delete(
            context,
            document_id=submitted.job.document_id,
            idempotency_key=f"delete-{suffix}",
            reason="test cleanup",
        )
        empty = await query_service.retrieve(
            context,
            RetrievalQuery(
                tenant_id=tenant_id,
                text="controller",
                knowledge_base_ids=(knowledge_base.id,),
                trace_id=f"deleted-query-{suffix}",
            ),
        )
        assert empty.empty_reason in {
            RetrievalEmptyReason.NO_MATCH,
            RetrievalEmptyReason.NO_EVIDENCE,
        }
        await deletion.purge(
            context, document_id=submitted.job.document_id, reason="retention elapsed"
        )
    finally:
        for key in await storage.list_prefix(
            context,
            tenant_id=tenant_id,
            prefix=f"tenants/{tenant_id}/",
        ):
            await storage.delete(
                context,
                StoredObject(
                    tenant_id=tenant_id,
                    object_key=key,
                    media_type="application/octet-stream",
                    size_bytes=0,
                    checksum_sha256="cleanup",
                ),
            )
        await client.indices.delete(index=index_name, ignore_unavailable=True)
        if "generation" in locals():
            await client.indices.delete(
                index=generation.physical_index, ignore_unavailable=True
            )
        await queue.close()
        redis = Redis.from_url(environment["RAGFLOW_AGENT_TEST_REDIS_URL"])
        await redis.delete(
            queue_name,
            f"arq:job:ingestion:{submitted.job.id}" if "submitted" in locals() else "unused",
            (
                f"arq:job:lifecycle-ingestion:{update.operation.id}"
                if "update" in locals()
                else "unused-2"
            ),
        )
        await redis.aclose()
        async with engine.begin() as connection:
            for table in (
                "knowledge_lifecycle_outbox",
                "knowledge_lifecycle_operations",
                "knowledge_lifecycle_batches",
                "knowledge_ingestion_tasks",
                "knowledge_ingestion_jobs",
                "knowledge_document_versions",
                "knowledge_documents",
                "knowledge_bases",
            ):
                await connection.execute(
                    text(f"delete from {table} where tenant_id=:tenant_id"),
                    {"tenant_id": tenant_id},
                )
        await search.close()
        await engine.dispose()
