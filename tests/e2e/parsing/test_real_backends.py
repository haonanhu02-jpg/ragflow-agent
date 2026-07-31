"""Phase 05 parsers through real PostgreSQL, MinIO, Redis, and Elasticsearch."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from pydantic import SecretStr
from sqlalchemy import text
from tests.fakes.minimum_rag import KeywordEmbedding
from tests.fakes.parsing import StaticOcrEngine, generated_format_samples

from ragflow_agent.config import (
    DatabaseSettings,
    IngestionSettings,
    ObjectStoreSettings,
    QueueSettings,
    SearchSettings,
)
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.application.ingestion import IngestionPipeline, IngestionProfile
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.parser_registry import ParserRegistry
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionStage,
    IngestionStatus,
)
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.infrastructure.database import (
    SqlAlchemyKnowledgeUnitOfWorkFactory,
)
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.infrastructure.queue import ArqIngestionQueue
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace
from ragflow_agent.knowledge.ports.storage import StoredObject
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock


def _required_environment() -> dict[str, str]:
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
        pytest.skip("complete Phase 05 real-backend environment is not configured")
    return values


@pytest.mark.asyncio
async def test_all_formats_reach_real_storage_database_queue_and_index() -> None:
    environment = _required_environment()
    suffix = uuid4().hex
    tenant_id = f"tenant-phase05-{suffix}"
    index_name = f"ragflow-agent-phase05-{suffix}"
    engine = create_database_engine(
        DatabaseSettings(url=SecretStr(environment["RAGFLOW_AGENT_TEST_DATABASE_URL"]))
    )
    factory = SqlAlchemyKnowledgeUnitOfWorkFactory(create_session_factory(engine))
    storage = S3ObjectStorage(
        ObjectStoreSettings(
            endpoint_url=environment["RAGFLOW_AGENT_TEST_S3_ENDPOINT_URL"],
            bucket="ragflow-agent-phase05-tests",
            access_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_ACCESS_KEY"]),
            secret_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_SECRET_KEY"]),
        )
    )
    queue = ArqIngestionQueue(
        QueueSettings(
            url=SecretStr(environment["RAGFLOW_AGENT_TEST_REDIS_URL"]),
            queue_name=f"arq:ragflow-agent:phase05:{suffix}",
        )
    )
    embedding = KeywordEmbedding(dimensions=32)
    elasticsearch_client = AsyncElasticsearch(
        environment["RAGFLOW_AGENT_TEST_ELASTICSEARCH_URL"],
        verify_certs=False,
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
        client=elasticsearch_client,
    )
    settings = IngestionSettings(
        max_upload_bytes=10 * 1024 * 1024,
        chunk_max_tokens=64,
        chunk_overlap_tokens=8,
    )
    permission = DefaultPermissionChecker()
    clock = SystemClock()
    context = AuthorizationContext(
        tenant_id=tenant_id,
        actor_id="owner-a",
        request_id=f"trace-{suffix}",
    )
    knowledge = KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=permission,
        id_generator=Uuid4Generator(),
        clock=clock,
        trace=LoggingKnowledgeTrace(),
    )
    upload = UploadService(
        knowledge_service=knowledge,
        unit_of_work_factory=factory,
        storage=storage,
        queue=queue,
        id_generator=Uuid4Generator(),
        clock=clock,
        max_upload_bytes=settings.max_upload_bytes,
    )
    parser = ParserRegistry(
        parsers=build_default_binary_parsers(settings, ocr=StaticOcrEngine()),
        storage=storage,
        unit_of_work_factory=factory,
        clock=clock,
        max_bytes=settings.max_upload_bytes,
        timeout_seconds=settings.parser_timeout_seconds,
        ocr_language="eng",
    )
    chunker = ChunkerRegistry(
        chunkers=(
            GeneralChunker(max_tokens=64, overlap_tokens=8),
            *(
                ScenarioChunker(
                    strategy_id=strategy,
                    max_tokens=64,
                    overlap_tokens=8,
                )
                for strategy in (
                    "paper",
                    "book",
                    "manual",
                    "laws",
                    "qa",
                    "table",
                    "resume",
                    "picture",
                )
            ),
        )
    )
    pipeline = IngestionPipeline(
        unit_of_work_factory=factory,
        parser=parser,
        chunker=chunker,
        embedding=embedding,
        search=search,
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="auto",
            chunk_strategy_version="auto",
            chunk_max_tokens=64,
            embedding_model_id=embedding.model_id,
        ),
        max_attempts=3,
    )
    stored_objects: list[StoredObject] = []
    try:
        await storage.ensure_bucket()
        await queue.open()
        await search.ensure_index()
        knowledge_base = await knowledge.create_knowledge_base(
            CreateKnowledgeBaseCommand(
                context=context,
                name="Phase 05 formats",
                visibility=Visibility.TENANT,
            )
        )
        for index, sample in enumerate(generated_format_samples()):
            submitted = await upload.submit(
                UploadDocumentCommand(
                    context=context.model_copy(
                        update={"request_id": f"trace-{suffix}-{index}"}
                    ),
                    knowledge_base_id=knowledge_base.id,
                    file_name=sample.name,
                    media_type=sample.media_type,
                    content=sample.payload,
                    idempotency_key=f"phase05-{suffix}-{index}",
                )
            )
            assert submitted.stored_object is not None
            stored_objects.append(submitted.stored_object)
            assert submitted.queue_receipt is not None
            async with factory() as unit_of_work:
                tasks = await unit_of_work.ingestion_tasks.list_for_job(
                    tenant_id=tenant_id,
                    job_id=submitted.job.id,
                )
            parse_task = next(
                task for task in tasks if task.stage is IngestionStage.PARSE
            )
            completed = await pipeline.handle(
                IngestionEnvelope.from_task(
                    parse_task,
                    message_id=f"ingestion:{submitted.job.id}",
                    created_at=datetime.now(UTC),
                )
            )
            assert completed.status is IngestionStatus.SUCCEEDED
            count = await elasticsearch_client.count(
                index=index_name,
                query={
                    "bool": {
                        "filter": [
                            {"term": {"tenant_id": tenant_id}},
                            {
                                "term": {
                                    "document_version_id": (
                                        submitted.job.document_version_id
                                    )
                                }
                            },
                        ]
                    }
                },
            )
            assert count["count"] > 0
    finally:
        for stored_object in stored_objects:
            await storage.delete(context, stored_object)
        await elasticsearch_client.indices.delete(
            index=index_name,
            ignore_unavailable=True,
        )
        await queue.close()
        async with engine.begin() as connection:
            for table_name in (
                "knowledge_ingestion_tasks",
                "knowledge_ingestion_jobs",
                "knowledge_document_versions",
                "knowledge_documents",
                "knowledge_bases",
            ):
                await connection.execute(
                    text(f"delete from {table_name} where tenant_id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )
        await search.close()
        await engine.dispose()
