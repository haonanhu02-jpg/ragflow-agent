"""Parser contract isolated from file-format libraries and RAGFlow internals."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import ParsedDocument


class ParseRequest(KnowledgeModel):
    """Tenant-scoped source identity supplied to a parser adapter."""

    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    document_id: NonEmptyStr
    document_version_id: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    trace_id: NonEmptyStr


@runtime_checkable
class ParserPort(Protocol):
    """Produce normalized parser output for one immutable document version."""

    async def parse(self, request: ParseRequest) -> ParsedDocument: ...
