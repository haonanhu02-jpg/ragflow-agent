"""Stable OCR adapter failure semantics without a system dependency."""

import pytesseract  # type: ignore[import-untyped]
import pytest
from PIL import Image

from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.ocr import TesseractOcrEngine


def test_missing_tesseract_is_engine_unavailable_not_language_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_version() -> object:
        raise pytesseract.TesseractNotFoundError

    monkeypatch.setattr(pytesseract, "get_tesseract_version", missing_version)
    with pytest.raises(KnowledgeConflictError) as unavailable:
        TesseractOcrEngine().recognize(
            Image.new("RGB", (100, 40), "white"),
            language="eng",
        )
    assert unavailable.value.error_code == "ocr_engine_unavailable"
