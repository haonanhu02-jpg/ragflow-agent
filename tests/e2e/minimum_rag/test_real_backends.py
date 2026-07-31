"""Real PostgreSQL/MinIO/Redis/Elasticsearch vertical-slice verification."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from elasticsearch import AsyncElasticsearch
from pydantic import SecretStr
from sqlalchemy import text

from ragflow_agent.config import (
    DatabaseSettings,
    ObjectStoreSettings,
    QueueSettings,
    SearchSettings,
)
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest, FixedRagService
from ragflow_agent.knowledge.application.ingestion import IngestionPipeline, IngestionProfile
from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeQueryService,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadDocumentCommand, UploadService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionStage,
    IngestionStatus,
)
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker
from ragflow_agent.knowledge.infrastructure.database import (
    SqlAlchemyKnowledgeUnitOfWorkFactory,
)
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.infrastructure.parsers import BasicObjectParser
from ragflow_agent.knowledge.infrastructure.queue import ArqIngestionQueue
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock
from tests.fakes.minimum_rag import KeywordEmbedding, StubChatProvider


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
        pytest.skip("complete Phase 04 real-backend environment is not configured")
    return values


@pytest.mark.asyncio
async def test_real_backends_complete_minimum_rag_vertical_slice() -> None:
    environment = _required_environment()
    suffix = uuid4().hex
    tenant_id = f"tenant-e2e-{suffix}"
    index_name = f"ragflow-agent-e2e-{suffix}"
    engine = create_database_engine(
        DatabaseSettings(url=SecretStr(environment["RAGFLOW_AGENT_TEST_DATABASE_URL"]))
    )
    unit_of_work_factory = SqlAlchemyKnowledgeUnitOfWorkFactory(create_session_factory(engine))
    storage = S3ObjectStorage(
        ObjectStoreSettings(
            endpoint_url=environment["RAGFLOW_AGENT_TEST_S3_ENDPOINT_URL"],
            bucket="ragflow-agent-phase04-tests",
            access_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_ACCESS_KEY"]),
            secret_key=SecretStr(environment["RAGFLOW_AGENT_TEST_S3_SECRET_KEY"]),
        )
    )
    queue_settings = QueueSettings(
        url=SecretStr(environment["RAGFLOW_AGENT_TEST_REDIS_URL"]),
        queue_name=f"arq:ragflow-agent:e2e:{suffix}",
    )
    queue = ArqIngestionQueue(queue_settings)
    embedding = KeywordEmbedding(dimensions=16)
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
    permission = DefaultPermissionChecker()
    clock = SystemClock()
    context = AuthorizationContext(
        tenant_id=tenant_id,
        actor_id="owner-a",
        request_id=f"trace-{suffix}",
    )
    knowledge = KnowledgeService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission,
        id_generator=Uuid4Generator(),
        clock=clock,
        trace=LoggingKnowledgeTrace(),
    )
    upload = UploadService(
        knowledge_service=knowledge,
        unit_of_work_factory=unit_of_work_factory,
        storage=storage,
        queue=queue,
        id_generator=Uuid4Generator(),
        clock=clock,
        max_upload_bytes=4096,
    )
    stored_object = None
    try:
        await storage.ensure_bucket()
        await search.ensure_index()
        await queue.open()
        knowledge_base = await knowledge.create_knowledge_base(
            CreateKnowledgeBaseCommand(
                context=context,
                name="Real backend maintenance",
                visibility=Visibility.TENANT,
            )
        )
        submitted = await upload.submit(
            UploadDocumentCommand(
                context=context,
                knowledge_base_id=knowledge_base.id,
                file_name="manual.md",
                media_type="text/markdown",
                content=(
                    b"# Alarm Recovery\n\ncontroller reset relay inspection recovery procedure"
                ),
                idempotency_key=f"upload-{suffix}",
            )
        )
        stored_object = submitted.stored_object
        assert submitted.queue_receipt is not None

        async with unit_of_work_factory() as unit_of_work:
            tasks = await unit_of_work.ingestion_tasks.list_for_job(
                tenant_id=tenant_id,
                job_id=submitted.job.id,
            )
        parse_task = next(task for task in tasks if task.stage is IngestionStage.PARSE)
        envelope = IngestionEnvelope.from_task(
            parse_task,
            message_id=f"ingestion:{submitted.job.id}",
            created_at=datetime.now(UTC),
        )
        pipeline = IngestionPipeline(
            unit_of_work_factory=unit_of_work_factory,
            parser=BasicObjectParser(
                storage=storage,
                unit_of_work_factory=unit_of_work_factory,
                clock=clock,
                max_bytes=4096,
            ),
            chunker=GeneralChunker(max_tokens=16, overlap_tokens=2),
            embedding=embedding,
            search=search,
            clock=clock,
            profile=IngestionProfile(
                chunk_strategy_id="general",
                chunk_strategy_version="1",
                chunk_max_tokens=16,
                embedding_model_id=embedding.model_id,
            ),
            max_attempts=3,
        )

        completed = await pipeline.handle(envelope)
        assert completed.status is IngestionStatus.SUCCEEDED

        chat = StubChatProvider()
        fixed_rag = FixedRagService(
            query_service=KnowledgeQueryService(
                unit_of_work_factory=unit_of_work_factory,
                permission_checker=permission,
                retriever=search,
            ),
            chat_provider=chat,
            chat_model_id=chat.model_id,
        )
        answer = await fixed_rag.answer(
            FixedRagRequest(
                context=context.model_copy(update={"request_id": f"query-{suffix}"}),
                question="controller reset inspection",
                knowledge_base_ids=(knowledge_base.id,),
            )
        )

        assert answer.citations
        assert answer.citations[0].document_version_id == submitted.job.document_version_id
        assert answer.retrieval_trace.authorization_applied
        assert answer.model_id == "deepseek-chat"
    finally:
        if stored_object is not None:
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
