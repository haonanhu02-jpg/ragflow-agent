"""CommonMark parser retaining headings, lists, code, tables, and order."""

from __future__ import annotations

from markdown_it import MarkdownIt
from markdown_it.token import Token

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ParsedBlock,
    TableMetadata,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class MarkdownBinaryParser:
    """Convert Markdown tokens to parser-neutral blocks."""

    capability = ParserCapability(
        parser_id="independent-markdown",
        parser_version="2",
        media_types=frozenset({"text/markdown"}),
        extensions=frozenset({".md", ".markdown"}),
        default_chunk_strategy="manual",
    )

    def __init__(self) -> None:
        self._markdown = MarkdownIt("commonmark").enable("table")

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        del request, ocr_language
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise KnowledgeConflictError(
                "Markdown source must be valid UTF-8",
                error_code="parser_encoding_invalid",
            ) from error
        tokens = self._markdown.parse(text)
        blocks: list[ParsedBlock] = []
        heading_path: tuple[str, ...] = ()
        index = 0
        while index < len(tokens):
            current = tokens[index]
            if current.type == "heading_open" and index + 1 < len(tokens):
                heading_token = tokens[index + 1]
                level = int(current.tag[1])
                value = heading_token.content.strip()
                if value:
                    heading_path = (*heading_path[: level - 1], value)
                    blocks.append(
                        ParsedBlock(
                            id=f"md_{len(blocks)}",
                            kind=BlockKind.HEADING,
                            order=len(blocks),
                            text=value,
                            heading_path=heading_path,
                        )
                    )
                index += 3
                continue
            if current.type in {"paragraph_open", "list_item_open"}:
                inline_token = next(
                    (
                        candidate
                        for candidate in tokens[index + 1 : index + 4]
                        if candidate.type == "inline"
                    ),
                    None,
                )
                if inline_token is not None and inline_token.content.strip():
                    kind = BlockKind.LIST if current.type == "list_item_open" else BlockKind.TEXT
                    blocks.append(
                        ParsedBlock(
                            id=f"md_{len(blocks)}",
                            kind=kind,
                            order=len(blocks),
                            text=inline_token.content.strip(),
                            heading_path=heading_path,
                        )
                    )
            elif current.type in {"fence", "code_block"} and current.content.strip():
                blocks.append(
                    ParsedBlock(
                        id=f"md_{len(blocks)}",
                        kind=BlockKind.CODE,
                        order=len(blocks),
                        text=current.content.rstrip(),
                        heading_path=heading_path,
                    )
                )
            elif current.type == "table_open":
                rows, consumed = self._table(tokens, index)
                if rows:
                    blocks.append(
                        ParsedBlock(
                            id=f"md_{len(blocks)}",
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
                index = consumed
                continue
            index += 1
        return ParsedPayload(blocks=tuple(blocks))

    @staticmethod
    def _table(tokens: list[Token], start: int) -> tuple[list[list[str]], int]:
        rows: list[list[str]] = []
        row: list[str] | None = None
        index = start + 1
        while index < len(tokens):
            current = tokens[index]
            current_type = current.type
            if current_type == "tr_open":
                row = []
            elif current_type == "inline" and row is not None:
                row.append(current.content.strip())
            elif current_type == "tr_close" and row is not None:
                rows.append(row)
                row = None
            elif current_type == "table_close":
                return rows, index + 1
            index += 1
        return rows, index
