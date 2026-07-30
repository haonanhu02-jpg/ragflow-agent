"""General Chunk stability and token-bound tests."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import BlockKind, ParsedBlock, ParsedDocument
from ragflow_agent.knowledge.infrastructure.chunking import GeneralChunker
from ragflow_agent.knowledge.ports.chunking import ChunkingRequest


@pytest.mark.asyncio
async def test_general_chunk_is_bounded_overlapped_and_stable() -> None:
    parsed = ParsedDocument(
        id="parsed-1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        parser_name="test",
        parser_version="1",
        parsed_at=datetime(2026, 7, 30, tzinfo=UTC),
        blocks=(
            ParsedBlock(
                id="block-1",
                kind=BlockKind.TEXT,
                order=0,
                text="one two three four five six seven eight nine ten",
                page_number=2,
            ),
        ),
    )
    request = ChunkingRequest(
        parsed_document=parsed,
        strategy_id="general",
        strategy_version="1",
        max_tokens=4,
        trace_id="trace",
    )
    chunker = GeneralChunker(max_tokens=4, overlap_tokens=1)
    context = AuthorizationContext(tenant_id="tenant-a", actor_id="owner", request_id="trace")

    first = await chunker.chunk(context, request)
    second = await chunker.chunk(context, request)

    assert first == second
    assert len(first) == 3
    assert all(chunk.token_count is not None and chunk.token_count <= 4 for chunk in first)
    assert all(chunk.metadata.page_start == 2 for chunk in first)
    assert first[0].id == second[0].id
