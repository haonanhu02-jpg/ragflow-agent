"""Deterministic line grouping for OCR and PDF word coordinates."""

from __future__ import annotations

from collections.abc import Sequence
from statistics import median

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    BoundingBox,
    ParsedBlock,
)
from ragflow_agent.knowledge.ports.ocr import OcrWord


def ocr_words_to_blocks(
    words: Sequence[OcrWord],
    *,
    page_number: int,
    id_prefix: str,
    start_order: int,
    heading_path: tuple[str, ...] = (),
) -> list[ParsedBlock]:
    """Group ordered OCR words into stable visual lines."""
    if not words:
        return []
    heights = [
        word.bounding_box.y1 - word.bounding_box.y0
        for word in words
    ]
    tolerance = max(4.0, median(heights) * 0.65)
    sorted_words = sorted(
        words,
        key=lambda item: (
            round((item.bounding_box.y0 + item.bounding_box.y1) / 2 / tolerance),
            item.bounding_box.x0,
            item.order,
        ),
    )
    lines: list[list[OcrWord]] = []
    centers: list[float] = []
    for word in sorted_words:
        center = (word.bounding_box.y0 + word.bounding_box.y1) / 2
        if not lines or abs(center - centers[-1]) > tolerance:
            lines.append([word])
            centers.append(center)
        else:
            lines[-1].append(word)
            centers[-1] = sum(
                (item.bounding_box.y0 + item.bounding_box.y1) / 2
                for item in lines[-1]
            ) / len(lines[-1])
    blocks: list[ParsedBlock] = []
    for line in lines:
        line.sort(key=lambda item: (item.bounding_box.x0, item.order))
        coordinate_space = line[0].bounding_box.coordinate_space
        blocks.append(
            ParsedBlock(
                id=f"{id_prefix}_{len(blocks)}",
                kind=BlockKind.TEXT,
                order=start_order + len(blocks),
                text=" ".join(word.text for word in line),
                page_number=page_number,
                bounding_box=BoundingBox(
                    x0=min(word.bounding_box.x0 for word in line),
                    y0=min(word.bounding_box.y0 for word in line),
                    x1=max(word.bounding_box.x1 for word in line),
                    y1=max(word.bounding_box.y1 for word in line),
                    coordinate_space=coordinate_space,
                ),
                heading_path=heading_path,
                confidence=sum(word.confidence for word in line) / len(line),
            )
        )
    return blocks
