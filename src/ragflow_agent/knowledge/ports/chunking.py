"""Chunk strategy boundary over normalized ParsedDocument input."""

from typing import Protocol, runtime_checkable

from pydantic import Field

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import ChunkRecord, ParsedDocument


class ChunkingRequest(KnowledgeModel):
    """Versioned strategy selection without Phase 05 implementation details."""

    parsed_document: ParsedDocument
    strategy_id: NonEmptyStr
    strategy_version: NonEmptyStr
    max_tokens: int | None = Field(default=None, ge=1)
    trace_id: NonEmptyStr


@runtime_checkable
class ChunkerPort(Protocol):
    """Produce stable chunks for one parsed document."""

    async def chunk(
        self,
        context: AuthorizationContext,
        request: ChunkingRequest,
    ) -> tuple[ChunkRecord, ...]: ...
