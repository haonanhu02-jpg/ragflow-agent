"""Parser and Chunk Method registry behavior."""

from datetime import UTC, datetime

import pytest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
)
from tests.fakes.parsing import StaticOcrEngine, generated_format_samples, parse_request

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.application.parser_registry import ParserRegistry
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import BlockKind, ParsedBlock, ParsedDocument
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.ports.chunking import ChunkingRequest


def test_parser_profile_routes_every_declared_format_deterministically() -> None:
    parsers = build_default_binary_parsers(IngestionSettings(), ocr=StaticOcrEngine())
    by_media_and_extension = {
        (media_type, extension): parser.capability.parser_id
        for parser in parsers
        for media_type in parser.capability.media_types
        for extension in parser.capability.extensions
    }
    for sample in generated_format_samples():
        extension = f".{sample.name.rsplit('.', maxsplit=1)[1]}"
        assert (sample.media_type, extension) in by_media_and_extension


@pytest.mark.asyncio
async def test_chunk_registry_uses_parser_recommendation_and_rejects_unknown() -> None:
    registry = ChunkerRegistry(
        chunkers=(
            GeneralChunker(max_tokens=32, overlap_tokens=4),
            ScenarioChunker(
                strategy_id="manual",
                max_tokens=32,
                overlap_tokens=4,
            ),
        )
    )
    document = ParsedDocument(
        id="parsed-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        parser_name="independent-markdown",
        parser_version="2",
        parsed_at=datetime(2026, 7, 31, tzinfo=UTC),
        blocks=(
            ParsedBlock(
                id="heading",
                kind=BlockKind.HEADING,
                order=0,
                text="Reset procedure",
            ),
            ParsedBlock(
                id="step",
                kind=BlockKind.TEXT,
                order=1,
                text="Isolate power and inspect the relay.",
            ),
        ),
        recommended_chunk_strategy="manual",
    )
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="worker",
        request_id="trace-a",
    )
    chunks = await registry.chunk(
        context,
        ChunkingRequest(
            parsed_document=document,
            strategy_id="auto",
            strategy_version="auto",
            max_tokens=32,
            trace_id="trace-a",
        ),
    )
    assert chunks[0].metadata.chunk_strategy_id == "manual"

    with pytest.raises(KnowledgeConflictError) as unknown:
        await registry.chunk(
            context,
            ChunkingRequest(
                parsed_document=document,
                strategy_id="not-registered",
                strategy_version="1",
                trace_id="trace-a",
            ),
        )
    assert unknown.value.error_code == "chunk_strategy_unknown"


def test_explicit_parser_contract_rejects_mismatched_media_type() -> None:
    settings = IngestionSettings()
    registry = ParserRegistry(
        parsers=build_default_binary_parsers(settings, ocr=StaticOcrEngine()),
        storage=MemoryObjectStorage(),
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(MemoryKnowledgeStore()),
        clock=FixedClock(datetime(2026, 7, 31, tzinfo=UTC)),
        max_bytes=settings.max_upload_bytes,
        timeout_seconds=settings.parser_timeout_seconds,
        ocr_language="eng",
    )
    sample = generated_format_samples()[0]
    assert sample.media_type == "text/plain"
    assert registry.resolve(parse_request(sample)).capability.parser_id == "independent-text"
    with pytest.raises(KnowledgeConflictError) as incompatible:
        registry.resolve(
            parse_request(sample).model_copy(update={"parser_id": "independent-markdown"})
        )
    assert incompatible.value.error_code == "parser_override_incompatible"
