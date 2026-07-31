"""Parser contract isolated from file-format libraries and RAGFlow internals."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import (
    ParsedBlock,
    ParsedDocument,
    ParseWarning,
)


class ParseRequest(KnowledgeModel):
    """Tenant-scoped source identity supplied to a parser adapter."""

    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    trace_id: NonEmptyStr
    parser_id: str | None = None


class ParserCapability(KnowledgeModel):
    """Declarative parser registration used by the application registry."""

    parser_id: NonEmptyStr
    parser_version: NonEmptyStr
    media_types: frozenset[NonEmptyStr]
    extensions: frozenset[NonEmptyStr]
    default_chunk_strategy: NonEmptyStr
    priority: int = 0


class ParsedPayload(KnowledgeModel):
    """Format-parser result before immutable source identity is attached."""

    blocks: tuple[ParsedBlock, ...]
    warnings: tuple[ParseWarning, ...] = ()


@runtime_checkable
class BinaryParserPort(Protocol):
    """Parse trusted bytes without storage, database, or index side effects."""

    capability: ParserCapability

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload: ...


@runtime_checkable
class ParserPort(Protocol):
    """Produce normalized parser output for one immutable document version."""

    async def parse(self, request: ParseRequest) -> ParsedDocument: ...
