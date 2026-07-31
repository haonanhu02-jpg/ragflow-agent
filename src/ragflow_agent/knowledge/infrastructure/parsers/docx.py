"""Independent DOCX parser using the public python-docx object model."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ImageReference,
    ParsedBlock,
    ParseWarning,
    TableMetadata,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers.security import validate_zip_package
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class DocxBinaryParser:
    """Retain paragraph/table order, heading styles, and image anchors."""

    capability = ParserCapability(
        parser_id="independent-docx",
        parser_version="2",
        media_types=frozenset(
            {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        ),
        extensions=frozenset({".docx"}),
        default_chunk_strategy="manual",
    )

    def __init__(
        self,
        *,
        max_entries: int,
        max_uncompressed_bytes: int,
        max_compression_ratio: float,
    ) -> None:
        self._max_entries = max_entries
        self._max_uncompressed_bytes = max_uncompressed_bytes
        self._max_compression_ratio = max_compression_ratio

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        del ocr_language
        validate_zip_package(
            payload,
            max_entries=self._max_entries,
            max_uncompressed_bytes=self._max_uncompressed_bytes,
            max_compression_ratio=self._max_compression_ratio,
        )
        try:
            document = Document(BytesIO(payload))
        except Exception as error:
            raise KnowledgeConflictError(
                "DOCX document is invalid",
                error_code="parser_docx_invalid",
            ) from error
        blocks: list[ParsedBlock] = []
        warnings: list[ParseWarning] = []
        heading_path: tuple[str, ...] = ()
        for item in document.iter_inner_content():
            if isinstance(item, Paragraph):
                value = item.text.strip()
                style_name = str(item.style.name or "") if item.style is not None else ""
                heading_level = self._heading_level(style_name)
                if value:
                    kind = BlockKind.HEADING if heading_level is not None else BlockKind.TEXT
                    if heading_level is not None:
                        heading_path = (*heading_path[: heading_level - 1], value)
                    blocks.append(
                        ParsedBlock(
                            id=f"docx_{len(blocks)}",
                            kind=kind,
                            order=len(blocks),
                            text=value,
                            heading_path=heading_path,
                        )
                    )
                for blip in item._p.xpath(".//a:blip"):
                    relation_id = blip.get(qn("r:embed"))
                    if not relation_id:
                        continue
                    part = document.part.related_parts.get(relation_id)
                    if part is None:
                        warnings.append(
                            ParseWarning(
                                code="docx_image_relation_missing",
                                message=f"image relation {relation_id} is missing",
                            )
                        )
                        continue
                    blocks.append(
                        ParsedBlock(
                            id=f"docx_{len(blocks)}",
                            kind=BlockKind.IMAGE,
                            order=len(blocks),
                            text="embedded DOCX image",
                            heading_path=heading_path,
                            image=ImageReference(
                                object_key=request.object_key,
                                embedded_path=str(part.partname),
                                media_type=str(part.content_type),
                            ),
                        )
                    )
            elif isinstance(item, Table):
                rows = [
                    [cell.text.strip() for cell in row.cells]
                    for row in item.rows
                ]
                rows = [row for row in rows if any(row)]
                if rows:
                    blocks.append(
                        ParsedBlock(
                            id=f"docx_{len(blocks)}",
                            kind=BlockKind.TABLE,
                            order=len(blocks),
                            text="\n".join("\t".join(row) for row in rows),
                            heading_path=heading_path,
                            table=TableMetadata(
                                rows=len(rows),
                                columns=max(len(row) for row in rows),
                                has_header=True,
                            ),
                        )
                    )
        return ParsedPayload(blocks=tuple(blocks), warnings=tuple(warnings))

    @staticmethod
    def _heading_level(style_name: str) -> int | None:
        normalized = style_name.casefold().strip()
        for prefix in ("heading ", "title "):
            if normalized.startswith(prefix):
                suffix = normalized.removeprefix(prefix)
                if suffix.isdigit():
                    return min(max(int(suffix), 1), 6)
        if normalized == "title":
            return 1
        return None
