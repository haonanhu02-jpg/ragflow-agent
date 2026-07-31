"""PDF text/layout/table parser with OCR fallback for scanned pages."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pdfplumber
import pypdfium2 as pdfium  # type: ignore[import-untyped]

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    BoundingBox,
    CoordinateSpace,
    ParsedBlock,
    ParseWarning,
    TableMetadata,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers.ocr_layout import (
    ocr_words_to_blocks,
)
from ragflow_agent.knowledge.infrastructure.parsers.security import validate_image
from ragflow_agent.knowledge.ports.ocr import OcrEnginePort, OcrWord
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class PdfBinaryParser:
    """Extract text words, source geometry, native tables, and scanned-page OCR."""

    capability = ParserCapability(
        parser_id="independent-pdf-layout",
        parser_version="2",
        media_types=frozenset({"application/pdf"}),
        extensions=frozenset({".pdf"}),
        default_chunk_strategy="paper",
    )

    def __init__(
        self,
        *,
        ocr: OcrEnginePort,
        max_pages: int,
        max_image_pixels: int,
        render_scale: float = 2,
    ) -> None:
        self._ocr = ocr
        self._max_pages = max_pages
        self._max_image_pixels = max_image_pixels
        self._render_scale = render_scale

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        del request
        try:
            document = pdfplumber.open(BytesIO(payload))
        except Exception as error:
            raise KnowledgeConflictError(
                "PDF document is invalid or encrypted",
                error_code="parser_pdf_invalid",
            ) from error
        try:
            renderer = pdfium.PdfDocument(payload)
        except Exception as error:
            document.close()
            raise KnowledgeConflictError(
                "PDF document is invalid or encrypted",
                error_code="parser_pdf_invalid",
            ) from error
        if len(document.pages) > self._max_pages:
            document.close()
            renderer.close()
            raise KnowledgeConflictError(
                "PDF exceeds the configured page limit",
                error_code="parser_resource_limit",
                details={"resource": "pdf_pages", "actual": len(document.pages)},
            )
        blocks: list[ParsedBlock] = []
        warnings: list[ParseWarning] = []
        try:
            for page_index, page in enumerate(document.pages):
                page_number = page_index + 1
                page_items: list[ParsedBlock] = []
                words = page.extract_words(
                    use_text_flow=True,
                    keep_blank_chars=False,
                    x_tolerance=2,
                    y_tolerance=3,
                )
                page_items.extend(
                    self._pdf_words_to_blocks(
                        words,
                        page_number=page_number,
                        start_order=0,
                        page_width=float(page.width),
                    )
                )
                page_items.extend(
                    self._table_blocks(
                        page,
                        page_number=page_number,
                        start_order=len(page_items),
                    )
                )
                if not page_items:
                    rendered = renderer[page_index].render(scale=self._render_scale).to_pil()
                    validate_image(rendered, max_pixels=self._max_image_pixels)
                    result = self._ocr.recognize(rendered, language=ocr_language)
                    page_items = ocr_words_to_blocks(
                        result.words,
                        page_number=page_number,
                        id_prefix=f"pdf_ocr_{page_number}",
                        start_order=0,
                    )
                    warnings.append(
                        ParseWarning(
                            code="pdf_scanned_page_ocr",
                            message="page had no native text and used OCR",
                            page_number=page_number,
                        )
                    )
                page_items.sort(
                    key=lambda item: (
                        item.bounding_box.y0 if item.bounding_box is not None else 0,
                        item.bounding_box.x0 if item.bounding_box is not None else 0,
                        item.order,
                    )
                )
                for item in page_items:
                    blocks.append(
                        item.model_copy(
                            update={
                                "id": f"pdf_{len(blocks)}",
                                "order": len(blocks),
                            }
                        )
                    )
        except KnowledgeConflictError:
            raise
        except Exception as error:
            raise KnowledgeConflictError(
                "PDF extraction failed",
                error_code="parser_pdf_extract_failed",
            ) from error
        finally:
            document.close()
            renderer.close()
        return ParsedPayload(blocks=tuple(blocks), warnings=tuple(warnings))

    @staticmethod
    def _pdf_words_to_blocks(
        words: list[dict[str, Any]],
        *,
        page_number: int,
        start_order: int,
        page_width: float,
    ) -> list[ParsedBlock]:
        ocr_words = tuple(
            OcrWord(
                text=str(word["text"]).strip(),
                confidence=1,
                order=index,
                bounding_box=BoundingBox(
                    x0=float(word["x0"]),
                    y0=float(word["top"]),
                    x1=float(word["x1"]),
                    y1=float(word["bottom"]),
                    coordinate_space=CoordinateSpace.PAGE_POINTS,
                ),
            )
            for index, word in enumerate(words)
            if str(word.get("text", "")).strip()
            and float(word["x1"]) > float(word["x0"])
            and float(word["bottom"]) > float(word["top"])
        )
        groups = PdfBinaryParser._column_groups(ocr_words, page_width=page_width)
        blocks: list[ParsedBlock] = []
        for column_index, group in enumerate(groups):
            column_blocks = ocr_words_to_blocks(
                group,
                page_number=page_number,
                id_prefix=f"pdf_text_{page_number}_{column_index}",
                start_order=start_order + len(blocks),
            )
            blocks.extend(column_blocks)
        return blocks

    @staticmethod
    def _column_groups(
        words: tuple[OcrWord, ...],
        *,
        page_width: float,
    ) -> tuple[tuple[OcrWord, ...], ...]:
        """Split clearly separated columns, otherwise preserve one visual flow."""
        if len(words) < 2 or page_width <= 0:
            return (words,)
        intervals = sorted(
            (
                word.bounding_box.x0,
                word.bounding_box.x1,
            )
            for word in words
        )
        gaps: list[tuple[float, float]] = []
        occupied_end = intervals[0][1]
        for left, right in intervals[1:]:
            if left > occupied_end:
                gaps.append((left - occupied_end, (left + occupied_end) / 2))
            occupied_end = max(occupied_end, right)
        if not gaps:
            return (words,)
        gap, divider = max(gaps)
        if gap < max(48.0, page_width * 0.08):
            return (words,)
        left_words = tuple(
            word
            for word in words
            if (word.bounding_box.x0 + word.bounding_box.x1) / 2 < divider
        )
        right_words = tuple(word for word in words if word not in left_words)
        if not left_words or not right_words:
            return (words,)
        return (left_words, right_words)

    @staticmethod
    def _table_blocks(
        page: Any,
        *,
        page_number: int,
        start_order: int,
    ) -> list[ParsedBlock]:
        blocks: list[ParsedBlock] = []
        for table in page.find_tables():
            rows = [
                [str(cell or "").strip() for cell in row]
                for row in table.extract()
            ]
            rows = [row for row in rows if any(row)]
            if not rows:
                continue
            x0, top, x1, bottom = (float(value) for value in table.bbox)
            if x1 <= x0 or bottom <= top:
                continue
            blocks.append(
                ParsedBlock(
                    id=f"pdf_table_{page_number}_{len(blocks)}",
                    kind=BlockKind.TABLE,
                    order=start_order + len(blocks),
                    text="\n".join("\t".join(row) for row in rows),
                    page_number=page_number,
                    bounding_box=BoundingBox(
                        x0=x0,
                        y0=top,
                        x1=x1,
                        y1=bottom,
                        coordinate_space=CoordinateSpace.PAGE_POINTS,
                    ),
                    table=TableMetadata(
                        rows=len(rows),
                        columns=max(len(row) for row in rows),
                        has_header=True,
                    ),
                )
            )
        return blocks
