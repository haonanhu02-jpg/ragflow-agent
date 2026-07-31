"""Independent TXT parser with bounded encoding detection."""

from __future__ import annotations

from charset_normalizer import from_bytes

from ragflow_agent.knowledge.domain.chunk import BlockKind, ParsedBlock, ParseWarning
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class TextBinaryParser:
    """Decode plain text and retain paragraph order."""

    capability = ParserCapability(
        parser_id="independent-text",
        parser_version="2",
        media_types=frozenset({"text/plain"}),
        extensions=frozenset({".txt"}),
        default_chunk_strategy="general",
    )

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        del request, ocr_language
        match = from_bytes(payload).best()
        if match is None:
            raise KnowledgeConflictError(
                "text encoding could not be detected",
                error_code="parser_encoding_invalid",
            )
        text = str(match).replace("\r\n", "\n").replace("\r", "\n")
        sections = [section.strip() for section in text.split("\n\n") if section.strip()]
        blocks = tuple(
            ParsedBlock(
                id=f"text_{index}",
                kind=BlockKind.TEXT,
                order=index,
                text=section,
            )
            for index, section in enumerate(sections)
        )
        warnings: tuple[ParseWarning, ...] = ()
        if match.encoding and match.encoding.casefold() not in {"utf_8", "utf_8_sig", "ascii"}:
            warnings = (
                ParseWarning(
                    code="text_encoding_detected",
                    message=f"decoded source as {match.encoding}",
                ),
            )
        return ParsedPayload(blocks=blocks, warnings=warnings)
