"""Stable parser failures and visible degradation behavior."""

from io import BytesIO

import pytest
from PIL import Image
from tests.fakes.parsing import (
    FormatSample,
    StaticOcrEngine,
    blank_pdf_bytes,
    parse_request,
)

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.ports.ocr import OcrResult


class EmptyOcrEngine:
    """Return a valid empty result to exercise the no-text protocol."""

    def recognize(self, image: object, *, language: str) -> OcrResult:
        del image
        return OcrResult(
            engine_name="empty-test-ocr",
            engine_version="1",
            language=language,
            words=(),
        )

    def available_languages(self) -> frozenset[str]:
        return frozenset({"eng"})


def test_scanned_pdf_fallback_is_explicit_and_traceable() -> None:
    sample = FormatSample(
        name="scanned.pdf",
        media_type="application/pdf",
        payload=blank_pdf_bytes(),
        expected_kinds=frozenset({"text"}),
    )
    parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-pdf-layout"
    )
    result = parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert result.blocks
    assert [warning.code for warning in result.warnings] == ["pdf_scanned_page_ocr"]
    assert result.warnings[0].page_number == 1


def test_image_no_text_and_invalid_payload_use_stable_error_codes() -> None:
    parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(),
            ocr=EmptyOcrEngine(),
        )
        if item.capability.parser_id == "independent-image-ocr"
    )
    image_stream = BytesIO()
    Image.new("RGB", (100, 50), "white").save(image_stream, format="PNG")
    sample = FormatSample(
        name="blank.png",
        media_type="image/png",
        payload=image_stream.getvalue(),
        expected_kinds=frozenset(),
    )
    with pytest.raises(KnowledgeConflictError) as no_text:
        parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert no_text.value.error_code == "ocr_no_text"
    with pytest.raises(KnowledgeConflictError) as invalid:
        parser.parse_bytes(b"not an image", parse_request(sample), ocr_language="eng")
    assert invalid.value.error_code == "parser_image_invalid"
