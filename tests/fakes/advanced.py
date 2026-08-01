"""Deterministic advanced providers and source builders."""

from datetime import UTC, datetime

from ragflow_agent.knowledge.domain.chunk import ChunkMetadata, ChunkRecord

NOW = datetime(2026, 8, 1, 0, 0, tzinfo=UTC)


def make_chunk(
    chunk_id: str,
    content: str,
    *,
    tenant_id: str = "tenant-a",
    knowledge_base_id: str = "kb-a",
    document_id: str = "doc-a",
    document_version_id: str = "ver-a",
    sequence: int = 0,
    parent_chunk_id: str | None = None,
) -> ChunkRecord:
    return ChunkRecord(
        id=chunk_id,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        document_version_id=document_version_id,
        parsed_document_id="parsed-a",
        sequence=sequence,
        content=content,
        source_block_ids=(f"block-{sequence}",),
        parent_chunk_id=parent_chunk_id,
        token_count=len(content.split()),
        metadata=ChunkMetadata(),
    )


class FakeVisionProvider:
    async def describe(self, *, media_type: str, content: bytes) -> str:
        return f"synthetic {media_type} figure with {len(content)} bytes"


class FakeSpeechProvider:
    async def transcribe(self, *, media_type: str, content: bytes) -> tuple[str, ...]:
        del media_type, content
        return ("alarm started", "maintenance completed")
