"""Production wiring for the Phase 05 multi-format minimum RAG profile."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.config import AppSettings
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.application.fixed_rag import FixedRagService
from ragflow_agent.knowledge.application.ingestion import (
    IngestionPipeline,
    IngestionProfile,
)
from ragflow_agent.knowledge.application.knowledge_service import (
    KnowledgeQueryService,
    KnowledgeService,
)
from ragflow_agent.knowledge.application.parser_registry import ParserRegistry
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadService
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.infrastructure.database import (
    SqlAlchemyKnowledgeUnitOfWorkFactory,
)
from ragflow_agent.knowledge.infrastructure.models import (
    build_chat_provider,
    build_embedding_adapter,
)
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.infrastructure.ocr import TesseractOcrEngine
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.infrastructure.queue import ArqIngestionQueue
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter
from ragflow_agent.knowledge.infrastructure.trace import LoggingKnowledgeTrace
from ragflow_agent.shared.ports.identity import Uuid4Generator
from ragflow_agent.shared.ports.time import SystemClock


@dataclass(slots=True)
class MinimumRagRuntime:
    """Owned resources and application services shared by API or Worker."""

    engine: AsyncEngine
    storage: S3ObjectStorage
    queue: ArqIngestionQueue
    search: ElasticsearchSearchAdapter
    knowledge_service: KnowledgeService
    upload_service: UploadService
    ingestion_pipeline: IngestionPipeline
    fixed_rag_service: FixedRagService

    async def open(self, *, open_queue: bool = True) -> None:
        await self.storage.ensure_bucket()
        await self.search.ensure_index()
        if open_queue:
            await self.queue.open()

    async def close(self) -> None:
        await self.queue.close()
        await self.search.close()
        await self.engine.dispose()


def build_minimum_rag_runtime(settings: AppSettings) -> MinimumRagRuntime:
    """Construct adapters without opening network connections."""
    engine = create_database_engine(settings.database)
    sessions = create_session_factory(engine)
    unit_of_work_factory = SqlAlchemyKnowledgeUnitOfWorkFactory(sessions)
    permission_checker = DefaultPermissionChecker()
    id_generator = Uuid4Generator()
    clock = SystemClock()
    trace = LoggingKnowledgeTrace()
    storage = S3ObjectStorage(settings.object_store)
    queue = ArqIngestionQueue(settings.queue)
    embedding = build_embedding_adapter(settings.models)
    search = ElasticsearchSearchAdapter(
        settings.search,
        embedding=embedding,
        embedding_model_id=settings.models.embedding_model,
        embedding_dimensions=settings.models.embedding_dimensions,
    )
    ocr = TesseractOcrEngine(command=settings.ingestion.tesseract_command)
    parser = ParserRegistry(
        parsers=build_default_binary_parsers(settings.ingestion, ocr=ocr),
        storage=storage,
        unit_of_work_factory=unit_of_work_factory,
        clock=clock,
        max_bytes=settings.ingestion.max_upload_bytes,
        timeout_seconds=settings.ingestion.parser_timeout_seconds,
        ocr_language=settings.ingestion.ocr_languages,
    )
    general_chunker = GeneralChunker(
        max_tokens=settings.ingestion.chunk_max_tokens,
        overlap_tokens=settings.ingestion.chunk_overlap_tokens,
    )
    chunker = ChunkerRegistry(
        chunkers=(
            general_chunker,
            *(
                ScenarioChunker(
                    strategy_id=strategy_id,
                    max_tokens=settings.ingestion.chunk_max_tokens,
                    overlap_tokens=settings.ingestion.chunk_overlap_tokens,
                )
                for strategy_id in (
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
    knowledge_service = KnowledgeService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission_checker,
        id_generator=id_generator,
        clock=clock,
        trace=trace,
    )
    query_service = KnowledgeQueryService(
        unit_of_work_factory=unit_of_work_factory,
        permission_checker=permission_checker,
        retriever=search,
    )
    upload_service = UploadService(
        knowledge_service=knowledge_service,
        unit_of_work_factory=unit_of_work_factory,
        storage=storage,
        queue=queue,
        id_generator=id_generator,
        clock=clock,
        max_upload_bytes=settings.ingestion.max_upload_bytes,
    )
    ingestion_pipeline = IngestionPipeline(
        unit_of_work_factory=unit_of_work_factory,
        parser=parser,
        chunker=chunker,
        embedding=embedding,
        search=search,
        clock=clock,
        profile=IngestionProfile(
            chunk_strategy_id="auto",
            chunk_strategy_version="auto",
            chunk_max_tokens=settings.ingestion.chunk_max_tokens,
            embedding_model_id=settings.models.embedding_model,
        ),
        max_attempts=settings.worker.max_tries,
    )
    fixed_rag_service = FixedRagService(
        query_service=query_service,
        chat_provider=build_chat_provider(settings.models),
        chat_model_id=settings.models.chat_model,
    )
    return MinimumRagRuntime(
        engine=engine,
        storage=storage,
        queue=queue,
        search=search,
        knowledge_service=knowledge_service,
        upload_service=upload_service,
        ingestion_pipeline=ingestion_pipeline,
        fixed_rag_service=fixed_rag_service,
    )
