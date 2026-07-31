"""Tesseract CLI OCR adapter; the engine and language data are external."""

from __future__ import annotations

from threading import Lock

import pytesseract  # type: ignore[import-untyped]
from PIL import Image
from pytesseract import Output

from ragflow_agent.knowledge.domain.chunk import BoundingBox, CoordinateSpace
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.ports.ocr import OcrResult, OcrWord

_COMMAND_LOCK = Lock()


class TesseractOcrEngine:
    """Map Tesseract TSV data to a small versioned OCR contract."""

    def __init__(
        self,
        *,
        command: str | None = None,
        minimum_confidence: float = 0,
    ) -> None:
        if minimum_confidence < 0 or minimum_confidence > 1:
            raise ValueError("minimum OCR confidence must be in [0, 1]")
        self._command = command
        self._minimum_confidence = minimum_confidence

    def recognize(
        self,
        image: object,
        *,
        language: str,
    ) -> OcrResult:
        if not isinstance(image, Image.Image):
            raise TypeError("Tesseract OCR requires a Pillow image")
        self._configure_command()
        try:
            version = str(pytesseract.get_tesseract_version())
        except pytesseract.TesseractNotFoundError as error:
            raise KnowledgeConflictError(
                "Tesseract OCR executable is not available",
                error_code="ocr_engine_unavailable",
            ) from error
        except pytesseract.TesseractError as error:
            raise KnowledgeConflictError(
                "Tesseract OCR runtime inspection failed",
                error_code="ocr_engine_failed",
                details={"status": error.status},
            ) from error
        available = self.available_languages()
        requested = frozenset(part for part in language.split("+") if part)
        missing = sorted(requested - available)
        if missing:
            raise KnowledgeConflictError(
                "configured OCR languages are not installed",
                error_code="ocr_language_unavailable",
                details={"missing_languages": missing},
            )
        try:
            data = pytesseract.image_to_data(
                image,
                lang=language,
                output_type=Output.DICT,
                config="--psm 6",
            )
        except pytesseract.TesseractError as error:
            raise KnowledgeConflictError(
                "Tesseract OCR execution failed",
                error_code="ocr_engine_failed",
                details={"status": error.status},
            ) from error
        words: list[OcrWord] = []
        texts = data["text"]
        for index, raw_text in enumerate(texts):
            text = str(raw_text).strip()
            if not text:
                continue
            raw_confidence = float(data["conf"][index])
            confidence = max(0.0, min(1.0, raw_confidence / 100))
            if confidence < self._minimum_confidence:
                continue
            left = int(data["left"][index])
            top = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])
            if width < 1 or height < 1:
                continue
            words.append(
                OcrWord(
                    text=text,
                    confidence=confidence,
                    bounding_box=BoundingBox(
                        x0=float(left),
                        y0=float(top),
                        x1=float(left + width),
                        y1=float(top + height),
                        coordinate_space=CoordinateSpace.PIXELS,
                    ),
                    order=len(words),
                )
            )
        return OcrResult(
            engine_name="tesseract",
            engine_version=version,
            language=language,
            words=tuple(words),
        )

    def available_languages(self) -> frozenset[str]:
        self._configure_command()
        try:
            return frozenset(pytesseract.get_languages(config=""))
        except (pytesseract.TesseractNotFoundError, pytesseract.TesseractError):
            return frozenset()

    def _configure_command(self) -> None:
        if self._command is None:
            return
        with _COMMAND_LOCK:
            pytesseract.pytesseract.tesseract_cmd = self._command
