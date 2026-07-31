"""Deterministic MIME/extension parser routing and bounded source loading."""

from __future__ import annotations

import asyncio
from pathlib import PurePosixPath

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import ParsedDocument
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.ports.parsing import (
    BinaryParserPort,
    ParseRequest,
)
from ragflow_agent.knowledge.ports.storage import ObjectStoragePort, StoredObject
from ragflow_agent.knowledge.ports.uow import KnowledgeUnitOfWorkFactory
from ragflow_agent.shared.ports.time import Clock


class ParserRegistry:
    """Select one registered binary parser and attach immutable source facts."""

    def __init__(
        self,
        *,
        parsers: tuple[BinaryParserPort, ...],
        storage: ObjectStoragePort,
        unit_of_work_factory: KnowledgeUnitOfWorkFactory,
        clock: Clock,
        max_bytes: int,
        timeout_seconds: float,
        ocr_language: str,
    ) -> None:
        if not parsers:
            raise ValueError("at least one parser must be registered")
        identifiers = [parser.capability.parser_id for parser in parsers]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("parser identifiers must be unique")
        self._parsers = tuple(
            sorted(parsers, key=lambda item: item.capability.priority, reverse=True)
        )
        self._storage = storage
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._max_bytes = max_bytes
        self._timeout_seconds = timeout_seconds
        self._ocr_language = ocr_language

    async def parse(self, request: ParseRequest) -> ParsedDocument:
        parser = self.resolve(request)
        payload = await self._load(request)
        if not payload:
            raise KnowledgeConflictError(
                "document is empty",
                error_code="parser_empty_document",
            )
        try:
            parsed = await asyncio.wait_for(
                asyncio.to_thread(
                    parser.parse_bytes,
                    payload,
                    request,
                    ocr_language=self._ocr_language,
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as error:
            raise KnowledgeConflictError(
                "document parsing exceeded the configured timeout",
                error_code="parser_timeout",
                details={"parser_id": parser.capability.parser_id},
            ) from error
        if not parsed.blocks:
            raise KnowledgeConflictError(
                "document contains no extractable content",
                error_code="parser_no_content",
                details={"parser_id": parser.capability.parser_id},
            )
        return ParsedDocument(
            id=f"parsed_{request.document_version_id}",
            tenant_id=request.tenant_id,
            knowledge_base_id=request.knowledge_base_id,
            document_id=request.document_id,
            document_version_id=request.document_version_id,
            parser_name=parser.capability.parser_id,
            parser_version=parser.capability.parser_version,
            parsed_at=self._clock.now(),
            blocks=parsed.blocks,
            source_media_type=request.media_type,
            source_name=PurePosixPath(request.object_key).name,
            recommended_chunk_strategy=parser.capability.default_chunk_strategy,
            warnings=parsed.warnings,
        )

    def resolve(self, request: ParseRequest) -> BinaryParserPort:
        extension = PurePosixPath(request.object_key).suffix.casefold()
        if request.parser_id is not None:
            explicit = next(
                (
                    parser
                    for parser in self._parsers
                    if parser.capability.parser_id == request.parser_id
                ),
                None,
            )
            if explicit is None:
                raise KnowledgeConflictError(
                    "explicit parser is not registered",
                    error_code="parser_override_unknown",
                    details={"parser_id": request.parser_id},
                )
            self._require_compatible(explicit, request.media_type, extension)
            return explicit
        candidates = [
            parser
            for parser in self._parsers
            if request.media_type in parser.capability.media_types
            and extension in parser.capability.extensions
        ]
        if not candidates:
            media_candidates = [
                parser
                for parser in self._parsers
                if request.media_type in parser.capability.media_types
            ]
            error_code = (
                "parser_extension_media_type_mismatch"
                if media_candidates
                else "parser_media_type_unsupported"
            )
            raise KnowledgeConflictError(
                "no parser matches the source MIME type and extension",
                error_code=error_code,
                details={"media_type": request.media_type, "extension": extension},
            )
        if (
            len(candidates) > 1
            and candidates[0].capability.priority == candidates[1].capability.priority
        ):
            raise KnowledgeConflictError(
                "parser routing is ambiguous",
                error_code="parser_route_ambiguous",
                details={"media_type": request.media_type, "extension": extension},
            )
        return candidates[0]

    @staticmethod
    def _require_compatible(
        parser: BinaryParserPort,
        media_type: str,
        extension: str,
    ) -> None:
        if (
            media_type not in parser.capability.media_types
            or extension not in parser.capability.extensions
        ):
            raise KnowledgeConflictError(
                "explicit parser is incompatible with the source",
                error_code="parser_override_incompatible",
                details={
                    "parser_id": parser.capability.parser_id,
                    "media_type": media_type,
                    "extension": extension,
                },
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
