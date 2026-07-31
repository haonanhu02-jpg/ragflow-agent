"""Independent, explicit scenario Chunk Methods over normalized blocks."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.chunk import (
    CHUNK_ID_ALGORITHM_V2,
    BlockKind,
    BoundingBox,
    ChunkMetadata,
    ChunkRecord,
    ParsedBlock,
    ParsedDocument,
    derive_chunk_id_v2,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.ports.chunking import ChunkingRequest

_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_LAW_ARTICLE = re.compile(
    r"^(?:第[一二三四五六七八九十百千万零〇\d]+条|Article\s+\d+)",
    re.IGNORECASE,
)
_CHAPTER = re.compile(
    r"^(?:第[一二三四五六七八九十百千万零〇\d]+章|Chapter\s+\d+)",
    re.IGNORECASE,
)
_QA = re.compile(
    r"(?:^|\n)(?:Q(?:uestion)?|问(?:题)?)[\uFF1A:]\s*(.+?)"
    r"(?:\n+)(?:A(?:nswer)?|答(?:案)?)[\uFF1A:]\s*(.+?)(?=\n(?:Q|问)|$)",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class _Group:
    blocks: tuple[ParsedBlock, ...]
    content: str


class ScenarioChunker:
    """One explicit strategy implementation selected by ``strategy_id``."""

    strategy_version = "1"

    def __init__(
        self,
        *,
        strategy_id: str,
        max_tokens: int,
        overlap_tokens: int,
    ) -> None:
        if strategy_id not in {
            "paper",
            "book",
            "manual",
            "laws",
            "qa",
            "table",
            "resume",
            "picture",
        }:
            raise ValueError("unsupported scenario chunk strategy")
        if max_tokens < 1 or overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("chunk token bounds are invalid")
        self.strategy_id = strategy_id
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
        records: list[ChunkRecord] = []
        for group in self._groups(document):
            for content, token_count in self._split(
                group.content,
                limit=limit,
                overlap=overlap,
            ):
                sequence = len(records)
                source_ids = tuple(dict.fromkeys(block.id for block in group.blocks))
                records.append(
                    ChunkRecord(
                        id=derive_chunk_id_v2(
                            tenant_id=document.tenant_id,
                            document_version_id=document.document_version_id,
                            strategy_id=self.strategy_id,
                            strategy_version=self.strategy_version,
                            sequence=sequence,
                            source_block_ids=source_ids,
                            content=content,
                        ),
                        id_algorithm=CHUNK_ID_ALGORITHM_V2,
                        tenant_id=document.tenant_id,
                        knowledge_base_id=document.knowledge_base_id,
                        document_id=document.document_id,
                        document_version_id=document.document_version_id,
                        parsed_document_id=document.id,
                        sequence=sequence,
                        content=content,
                        source_block_ids=source_ids,
                        token_count=token_count,
                        metadata=self._metadata(document, group.blocks),
                    )
                )
        return tuple(records)

    def _groups(self, document: ParsedDocument) -> tuple[_Group, ...]:
        method: Callable[[tuple[ParsedBlock, ...]], list[_Group]] = {
            "paper": self._paper,
            "book": self._book,
            "manual": self._manual,
            "laws": self._laws,
            "qa": self._qa,
            "table": self._table,
            "resume": self._resume,
            "picture": self._picture,
        }[self.strategy_id]
        return tuple(group for group in method(document.blocks) if group.content.strip())

    def _paper(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Keep abstract/section/reference boundaries and isolate tables."""
        return self._heading_sections(
            blocks,
            isolate=lambda block: block.kind in {BlockKind.TABLE, BlockKind.IMAGE},
        )

    def _book(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Start chapters at chapter-like or explicit heading blocks."""
        groups: list[list[ParsedBlock]] = []
        current: list[ParsedBlock] = []
        for block in blocks:
            if block.kind is BlockKind.HEADING and (_CHAPTER.match(block.text) or current):
                if current:
                    groups.append(current)
                current = [block]
            else:
                current.append(block)
        if current:
            groups.append(current)
        return [self._group(group) for group in groups]

    def _manual(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Keep a heading with its procedure steps and isolate tables/images."""
        return self._heading_sections(
            blocks,
            isolate=lambda block: block.kind in {BlockKind.TABLE, BlockKind.IMAGE},
        )

    def _laws(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Start a new legal chunk for each explicit article marker."""
        groups: list[_Group] = []
        for block in blocks:
            lines = [line.strip() for line in block.text.splitlines() if line.strip()]
            current: list[str] = []
            for line in lines:
                if _LAW_ARTICLE.match(line) and current:
                    groups.append(_Group(blocks=(block,), content="\n".join(current)))
                    current = [line]
                else:
                    current.append(line)
            if current:
                groups.append(_Group(blocks=(block,), content="\n".join(current)))
        return groups

    def _qa(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Pair explicit Q/A text or the first two columns of table rows."""
        groups: list[_Group] = []
        for block in blocks:
            if block.kind is BlockKind.TABLE:
                rows = [row.split("\t") for row in block.text.splitlines()]
                for row in rows[1:] if len(rows) > 1 else rows:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        groups.append(
                            _Group(
                                blocks=(block,),
                                content=f"Question: {row[0].strip()}\nAnswer: {row[1].strip()}",
                            )
                        )
                continue
            matches = list(_QA.finditer(block.text))
            if matches:
                groups.extend(
                    _Group(
                        blocks=(block,),
                        content=(
                            f"Question: {match.group(1).strip()}\nAnswer: {match.group(2).strip()}"
                        ),
                    )
                    for match in matches
                )
            elif block.text.strip():
                groups.append(_Group(blocks=(block,), content=block.text.strip()))
        return groups

    def _table(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Repeat the header with every table row to keep row-level context."""
        groups: list[_Group] = []
        for block in blocks:
            if block.kind is not BlockKind.TABLE:
                if block.text.strip():
                    groups.append(_Group(blocks=(block,), content=block.text.strip()))
                continue
            rows = [row for row in block.text.splitlines() if row.strip()]
            if not rows:
                continue
            header = rows[0]
            data_rows = rows[1:]
            if not data_rows:
                groups.append(_Group(blocks=(block,), content=header))
            else:
                groups.extend(
                    _Group(blocks=(block,), content=f"{header}\n{row}") for row in data_rows
                )
        return groups

    def _resume(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Keep common résumé sections independent and source ordered."""
        return self._heading_sections(blocks, isolate=lambda block: False)

    def _picture(self, blocks: tuple[ParsedBlock, ...]) -> list[_Group]:
        """Bind each image to OCR/text blocks on the same source page."""
        groups: list[_Group] = []
        by_page: dict[int | None, list[ParsedBlock]] = {}
        for block in blocks:
            by_page.setdefault(block.page_number, []).append(block)
        for page_blocks in by_page.values():
            images = [block for block in page_blocks if block.kind is BlockKind.IMAGE]
            text = [block for block in page_blocks if block.kind is not BlockKind.IMAGE]
            if images:
                content = "\n".join(block.text for block in (*images, *text) if block.text)
                groups.append(_Group(blocks=tuple((*images, *text)), content=content))
            else:
                groups.extend(self._group([block]) for block in text)
        return groups

    def _heading_sections(
        self,
        blocks: tuple[ParsedBlock, ...],
        *,
        isolate: Callable[[ParsedBlock], bool],
    ) -> list[_Group]:
        groups: list[_Group] = []
        current: list[ParsedBlock] = []
        for block in blocks:
            if isolate(block):
                if current:
                    groups.append(self._group(current))
                    current = []
                groups.append(self._group([block]))
            elif block.kind is BlockKind.HEADING and current:
                groups.append(self._group(current))
                current = [block]
            else:
                current.append(block)
        if current:
            groups.append(self._group(current))
        return groups

    @staticmethod
    def _group(blocks: list[ParsedBlock]) -> _Group:
        return _Group(
            blocks=tuple(blocks),
            content="\n\n".join(block.text.strip() for block in blocks if block.text.strip()),
        )

    @staticmethod
    def _split(
        text: str,
        *,
        limit: int,
        overlap: int,
    ) -> list[tuple[str, int]]:
        matches = list(_TOKEN_PATTERN.finditer(text))
        if not matches:
            return []
        output: list[tuple[str, int]] = []
        start = 0
        while start < len(matches):
            end = min(start + limit, len(matches))
            content = text[matches[start].start() : matches[end - 1].end()].strip()
            if content:
                output.append((content, end - start))
            if end == len(matches):
                break
            start = end - overlap
        return output

    def _metadata(
        self,
        document: ParsedDocument,
        blocks: tuple[ParsedBlock, ...],
    ) -> ChunkMetadata:
        pages = [block.page_number for block in blocks if block.page_number is not None]
        heading_path = next(
            (block.heading_path for block in blocks if block.heading_path),
            (),
        )
        kinds = tuple(dict.fromkeys(block.kind for block in blocks))
        boxes = [block.bounding_box for block in blocks if block.bounding_box is not None]
        bounding_box = self._combined_box(boxes) if len(set(pages)) == 1 else None
        return ChunkMetadata(
            heading_path=heading_path,
            page_start=min(pages) if pages else None,
            page_end=max(pages) if pages else None,
            source_order_start=min(block.order for block in blocks),
            source_order_end=max(block.order for block in blocks),
            block_kinds=kinds,
            bounding_box=bounding_box,
            contains_table=BlockKind.TABLE in kinds,
            contains_image=BlockKind.IMAGE in kinds,
            parser_name=document.parser_name,
            parser_version=document.parser_version,
            chunk_strategy_id=self.strategy_id,
            chunk_strategy_version=self.strategy_version,
        )

    @staticmethod
    def _combined_box(boxes: list[BoundingBox]) -> BoundingBox | None:
        if not boxes:
            return None
        coordinate_spaces = {box.coordinate_space for box in boxes}
        if len(coordinate_spaces) != 1:
            return None
        return BoundingBox(
            x0=min(box.x0 for box in boxes),
            y0=min(box.y0 for box in boxes),
            x1=max(box.x1 for box in boxes),
            y1=max(box.y1 for box in boxes),
            coordinate_space=boxes[0].coordinate_space,
        )
