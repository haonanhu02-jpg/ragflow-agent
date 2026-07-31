"""Deterministic Unicode-aware general chunking."""

from __future__ import annotations

import re

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ChunkMetadata,
    ChunkRecord,
    ParsedBlock,
    ParsedDocument,
    derive_chunk_id,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.ports.chunking import ChunkingRequest

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class GeneralChunker:
    """Split ordered blocks by a stable token approximation with overlap."""

    strategy_id = "general"
    strategy_version = "1"

    def __init__(self, *, max_tokens: int, overlap_tokens: int) -> None:
        if max_tokens < 1 or overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("chunk token bounds are invalid")
        self._max_tokens = max_tokens
        self._overlap_tokens = overlap_tokens

    async def chunk(
        self,
        context: AuthorizationContext,
        request: ChunkingRequest,
    ) -> tuple[ChunkRecord, ...]:
        document = request.parsed_document
        if context.tenant_id != document.tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        limit = request.max_tokens or self._max_tokens
        overlap = min(self._overlap_tokens, limit - 1)
        chunks: list[ChunkRecord] = []
        for block in document.blocks:
            for content, token_count in self._split(block.text, limit=limit, overlap=overlap):
                sequence = len(chunks)
                source_ids = (block.id,)
                chunks.append(
                    ChunkRecord(
                        id=derive_chunk_id(
                            tenant_id=document.tenant_id,
                            document_version_id=document.document_version_id,
                            sequence=sequence,
                            source_block_ids=source_ids,
                            content=content,
                        ),
                        tenant_id=document.tenant_id,
                        knowledge_base_id=document.knowledge_base_id,
                        document_id=document.document_id,
                        document_version_id=document.document_version_id,
                        parsed_document_id=document.id,
                        sequence=sequence,
                        content=content,
                        source_block_ids=source_ids,
                        token_count=token_count,
                        metadata=self._metadata(document, block),
                    )
                )
        return tuple(chunks)

    @staticmethod
    def _split(text: str, *, limit: int, overlap: int) -> list[tuple[str, int]]:
        matches = list(_TOKEN_PATTERN.finditer(text))
        if not matches:
            return []
        output: list[tuple[str, int]] = []
        start = 0
        while start < len(matches):
            end = min(start + limit, len(matches))
            char_start = matches[start].start()
            char_end = matches[end - 1].end()
            content = text[char_start:char_end].strip()
            if content:
                output.append((content, end - start))
            if end == len(matches):
                break
            start = end - overlap
        return output

    def _metadata(
        self,
        document: ParsedDocument,
        block: ParsedBlock,
    ) -> ChunkMetadata:
        return ChunkMetadata(
            heading_path=block.heading_path,
            page_start=block.page_number,
            page_end=block.page_number,
            source_order_start=block.order,
            source_order_end=block.order,
            block_kinds=(block.kind,),
            bounding_box=block.bounding_box,
            contains_table=block.kind is BlockKind.TABLE,
            contains_image=block.kind is BlockKind.IMAGE,
            parser_name=document.parser_name,
            parser_version=document.parser_version,
            chunk_strategy_id=self.strategy_id,
            chunk_strategy_version=self.strategy_version,
        )
