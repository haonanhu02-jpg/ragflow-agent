"""Independent minimum parser; no RAGFlow source is copied."""

from __future__ import annotations

import asyncio
from io import BytesIO

from pypdf import PdfReader

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ParsedBlock,
    ParsedDocument,
)
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.ports.parsing import ParseRequest
from ragflow_agent.knowledge.ports.storage import ObjectStoragePort, StoredObject
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock

SUPPORTED_MEDIA_TYPES = frozenset(
    {
        "text/plain",
        "text/markdown",
        "application/pdf",
    }
)


class BasicObjectParser:
    """Read an immutable source object and normalize its minimum structure."""

    name = "independent-basic-parser"
    version = "1"

    def __init__(
        self,
        *,
        storage: ObjectStoragePort,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        clock: Clock,
        max_bytes: int,
        timeout_seconds: float = 30,
    ) -> None:
        self._storage = storage
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds

    async def parse(self, request: ParseRequest) -> ParsedDocument:
        if request.media_type not in SUPPORTED_MEDIA_TYPES:
            raise KnowledgeConflictError(
                "document media type is not supported by the minimum parser",
                error_code="parser_media_type_unsupported",
                details={"media_type": request.media_type},
            )
        payload = await self._load(request)
        if not payload:
            raise KnowledgeConflictError(
                "document is empty",
                error_code="parser_empty_document",
            )
        if request.media_type == "application/pdf":
            try:
                blocks = await asyncio.wait_for(
                    asyncio.to_thread(self._parse_pdf, payload),
                    timeout=self._timeout_seconds,
                )
            except TimeoutError as error:
                raise KnowledgeConflictError(
                    "PDF parsing exceeded the configured timeout",
                    error_code="parser_timeout",
                ) from error
        else:
            blocks = self._parse_text(payload, markdown=request.media_type == "text/markdown")
        if not blocks:
            raise KnowledgeConflictError(
                "document contains no extractable text",
                error_code="parser_no_text",
            )
        return ParsedDocument(
            id=f"parsed_{request.document_version_id}",
            tenant_id=request.tenant_id,
            knowledge_base_id=request.knowledge_base_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            parser_name=self.name,
            parser_version=self.version,
            parsed_at=self._clock.now(),
            blocks=tuple(blocks),
        )

    async def _load(self, request: ParseRequest) -> bytes:
        async with self._unit_of_work_factory() as unit_of_work:
            version = await unit_of_work.document_versions.get(
                tenant_id=request.tenant_id,
                resource_id=request.document_version_id,
            )
        if version is None:
            raise KnowledgeNotFoundError("document_version", request.document_version_id)
        if (
            version.knowledge_base_id,
            version.document_id,
            version.object_key,
            version.media_type,
        ) != (
            request.knowledge_base_id,
            request.document_id,
            request.object_key,
            request.media_type,
        ):
            raise KnowledgeConflictError(
                "parse request does not match the persisted document version",
                error_code="parser_source_scope_mismatch",
            )
        stored = StoredObject(
            tenant_id=version.tenant_id,
            object_key=version.object_key,
            media_type=version.media_type,
            size_bytes=version.size_bytes,
            checksum_sha256=version.content_hash,
        )
        context = AuthorizationContext(
            tenant_id=request.tenant_id,
            actor_id="ingestion-worker",
            request_id=request.trace_id,
        )
        parts: list[bytes] = []
        size = 0
        async for part in self._storage.read(context, stored):
            size += len(part)
            if size > self._max_bytes:
                raise KnowledgeConflictError(
                    "document exceeds parser byte limit",
                    error_code="parser_resource_limit",
                )
            parts.append(part)
        return b"".join(parts)

    @staticmethod
    def _decode_text(payload: bytes) -> str:
        try:
            return payload.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise KnowledgeConflictError(
                "text document must be valid UTF-8",
                error_code="parser_encoding_invalid",
            ) from error

    def _parse_text(self, payload: bytes, *, markdown: bool) -> list[ParsedBlock]:
        text = self._decode_text(payload).replace("\r\n", "\n").replace("\r", "\n")
        sections = [section.strip() for section in text.split("\n\n") if section.strip()]
        blocks: list[ParsedBlock] = []
        heading_path: tuple[str, ...] = ()
        for section in sections:
            first_line = section.splitlines()[0].strip()
            if markdown and first_line.startswith("#"):
                level = len(first_line) - len(first_line.lstrip("#"))
                heading = first_line[level:].strip()
                if heading and level <= 6 and section == first_line:
                    heading_path = (*heading_path[: level - 1], heading)
                    blocks.append(
                        ParsedBlock(
                            id=f"block_{len(blocks)}",
                            kind=BlockKind.HEADING,
                            order=len(blocks),
                            text=heading,
                            heading_path=heading_path,
                        )
                    )
                    continue
            blocks.append(
                ParsedBlock(
                    id=f"block_{len(blocks)}",
                    kind=BlockKind.TEXT,
                    order=len(blocks),
                    text=section,
                    heading_path=heading_path,
                )
            )
        return blocks

    @staticmethod
    def _parse_pdf(payload: bytes) -> list[ParsedBlock]:
        try:
            reader = PdfReader(BytesIO(payload))
        except Exception as error:
            raise KnowledgeConflictError(
                "PDF document is invalid or encrypted",
                error_code="parser_pdf_invalid",
            ) from error
        blocks: list[ParsedBlock] = []
        for page_number, page in enumerate(reader.pages, start=1):
            try:
                text = (page.extract_text() or "").strip()
            except Exception as error:
                raise KnowledgeConflictError(
                    "PDF page text extraction failed",
                    error_code="parser_pdf_extract_failed",
                    details={"page_number": page_number},
                ) from error
            if text:
                blocks.append(
                    ParsedBlock(
                        id=f"page_{page_number}",
                        kind=BlockKind.TEXT,
                        order=len(blocks),
                        text=text,
                        page_number=page_number,
                    )
                )
        return blocks
