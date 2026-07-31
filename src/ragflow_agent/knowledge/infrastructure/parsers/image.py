"""Image validation and real OCR parser."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    BoundingBox,
    CoordinateSpace,
    ImageReference,
    ParsedBlock,
    ParseWarning,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers.ocr_layout import (
    ocr_words_to_blocks,
)
from ragflow_agent.knowledge.infrastructure.parsers.security import validate_image
from ragflow_agent.knowledge.ports.ocr import OcrEnginePort
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class ImageBinaryParser:
    """Decode one bounded image and OCR it through an isolated engine."""

    capability = ParserCapability(
        parser_id="independent-image-ocr",
        parser_version="2",
        media_types=frozenset(
            {
                "image/png",
                "image/jpeg",
                "image/tiff",
                "image/webp",
                "image/bmp",
            }
        ),
        extensions=frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}),
        default_chunk_strategy="picture",
    )

    def __init__(
        self,
        *,
        ocr: OcrEnginePort,
        max_pixels: int,
    ) -> None:
        self._ocr = ocr
        self._max_pixels = max_pixels

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        try:
            with Image.open(BytesIO(payload)) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
        except (UnidentifiedImageError, OSError) as error:
            raise KnowledgeConflictError(
                "image source is invalid",
                error_code="parser_image_invalid",
            ) from error
        validate_image(image, max_pixels=self._max_pixels)
        result = self._ocr.recognize(image, language=ocr_language)
        if not result.words:
            raise KnowledgeConflictError(
                "OCR produced no text",
                error_code="ocr_no_text",
            )
        width, height = image.size
        image_block = ParsedBlock(
            id="image_0",
            kind=BlockKind.IMAGE,
            order=0,
            text="source image",
            page_number=1,
            bounding_box=BoundingBox(
                x0=0,
                y0=0,
                x1=float(width),
                y1=float(height),
                coordinate_space=CoordinateSpace.PIXELS,
            ),
            image=ImageReference(
                object_key=request.object_key,
                media_type=request.media_type,
                width=width,
                height=height,
            ),
        )
        text_blocks = ocr_words_to_blocks(
            result.words,
            page_number=1,
            id_prefix="ocr",
            start_order=1,
        )
        warnings: tuple[ParseWarning, ...] = ()
        low_confidence = [
            block
            for block in text_blocks
            if block.confidence is not None and block.confidence < 0.5
        ]
        if low_confidence:
            warnings = (
                ParseWarning(
                    code="ocr_low_confidence",
                    message=f"{len(low_confidence)} OCR lines are below confidence 0.5",
                    page_number=1,
                ),
            )
        return ParsedPayload(
            blocks=(image_block, *text_blocks),
            warnings=warnings,
        )
