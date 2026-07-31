"""Versioned metadata, stable IDs, and all Phase 05 Chunk Methods."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.chunker_registry import ChunkerRegistry
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    BoundingBox,
    CoordinateSpace,
    ImageReference,
    ParsedBlock,
    ParsedDocument,
    TableMetadata,
)
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker, ScenarioChunker
from ragflow_agent.knowledge.ports.chunking import ChunkerPort, ChunkingRequest

STRATEGIES = (
    "general",
    "paper",
    "book",
    "manual",
    "laws",
    "qa",
    "table",
    "resume",
    "picture",
)


def _document(strategy: str) -> ParsedDocument:
    blocks = (
        ParsedBlock(
            id="heading",
            kind=BlockKind.HEADING,
            order=0,
            text="Alarm Recovery",
            page_number=1,
            bounding_box=BoundingBox(
                x0=10,
                y0=10,
                x1=200,
                y1=30,
                coordinate_space=CoordinateSpace.PAGE_POINTS,
            ),
            heading_path=("Alarm Recovery",),
        ),
        ParsedBlock(
            id="text",
            kind=BlockKind.TEXT,
            order=1,
            text=(
                "Article 1 Safety isolation.\n"
                "Q: How is the alarm reset?\nA: Isolate power and inspect the relay."
            ),
            page_number=1,
            bounding_box=BoundingBox(
                x0=10,
                y0=40,
                x1=400,
                y1=100,
                coordinate_space=CoordinateSpace.PAGE_POINTS,
            ),
            heading_path=("Alarm Recovery",),
        ),
        ParsedBlock(
            id="table",
            kind=BlockKind.TABLE,
            order=2,
            text="Step\tAction\n1\tReset controller\n2\tInspect relay",
            page_number=1,
            bounding_box=BoundingBox(
                x0=10,
                y0=110,
                x1=400,
                y1=180,
                coordinate_space=CoordinateSpace.PAGE_POINTS,
            ),
            heading_path=("Alarm Recovery",),
            table=TableMetadata(rows=3, columns=2, has_header=True),
        ),
        ParsedBlock(
            id="image",
            kind=BlockKind.IMAGE,
            order=3,
            text="Relay diagram",
            page_number=1,
            bounding_box=BoundingBox(
                x0=10,
                y0=190,
                x1=200,
                y1=300,
                coordinate_space=CoordinateSpace.PAGE_POINTS,
            ),
            image=ImageReference(
                object_key="fixtures/manual.pdf",
                media_type="image/png",
            ),
        ),
    )
    return ParsedDocument(
        id=f"parsed-{strategy}",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        parser_name="contract-parser",
        parser_version="2",
        parsed_at=datetime(2026, 7, 31, tzinfo=UTC),
        blocks=blocks,
        recommended_chunk_strategy=strategy,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("strategy", STRATEGIES)
async def test_all_chunk_methods_are_deterministic_and_traceable(strategy: str) -> None:
    chunkers: tuple[ChunkerPort, ...] = tuple(
        [
            GeneralChunker(max_tokens=64, overlap_tokens=8),
            *(
                ScenarioChunker(
                    strategy_id=item,
                    max_tokens=64,
                    overlap_tokens=8,
                )
                for item in STRATEGIES
                if item != "general"
            ),
        ]
    )
    registry = ChunkerRegistry(chunkers=chunkers)
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="worker",
        request_id="trace-a",
    )
    request = ChunkingRequest(
        parsed_document=_document(strategy),
        strategy_id="auto",
        strategy_version="auto",
        max_tokens=64,
        trace_id="trace-a",
    )
    first = await registry.chunk(context, request)
    second = await registry.chunk(context, request)
    assert first
    assert [chunk.id for chunk in first] == [chunk.id for chunk in second]
    assert [chunk.sequence for chunk in first] == list(range(len(first)))
    assert all(chunk.metadata.chunk_strategy_id == strategy for chunk in first)
    assert all(chunk.metadata.parser_name == "contract-parser" for chunk in first)
    assert all(chunk.metadata.source_order_start is not None for chunk in first)
    assert all(chunk.source_block_ids for chunk in first)


@pytest.mark.asyncio
async def test_table_strategy_repeats_header_and_qa_strategy_pairs_rows() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="worker",
        request_id="trace-a",
    )
    table = ScenarioChunker(strategy_id="table", max_tokens=64, overlap_tokens=8)
    qa = ScenarioChunker(strategy_id="qa", max_tokens=64, overlap_tokens=8)
    table_chunks = await table.chunk(
        context,
        ChunkingRequest(
            parsed_document=_document("table"),
            strategy_id="table",
            strategy_version="1",
            trace_id="trace-a",
        ),
    )
    qa_chunks = await qa.chunk(
        context,
        ChunkingRequest(
            parsed_document=_document("qa"),
            strategy_id="qa",
            strategy_version="1",
            trace_id="trace-a",
        ),
    )
    table_rows = [chunk for chunk in table_chunks if "Step" in chunk.content]
    assert len(table_rows) == 2
    assert all(chunk.content.startswith("Step") for chunk in table_rows)
    assert any("Question:" in chunk.content and "Answer:" in chunk.content for chunk in qa_chunks)
