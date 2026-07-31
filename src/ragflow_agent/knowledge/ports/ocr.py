"""OCR contract isolated from Tesseract, model runtimes, and image libraries."""

from typing import Protocol, runtime_checkable

from pydantic import Field

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import BoundingBox


class OcrWord(KnowledgeModel):
    """One OCR word and its exact source geometry."""

    text: NonEmptyStr
    confidence: float = Field(ge=0, le=1)
    bounding_box: BoundingBox
    order: int = Field(ge=0)


class OcrResult(KnowledgeModel):
    """OCR output for one image or rendered PDF page."""

    engine_name: NonEmptyStr
    engine_version: NonEmptyStr
    language: NonEmptyStr
    words: tuple[OcrWord, ...]


@runtime_checkable
class OcrEnginePort(Protocol):
    """Recognize an encoded image without exposing a vendor result object."""

    def recognize(
        self,
        image: object,
        *,
        language: str,
    ) -> OcrResult: ...

    def available_languages(self) -> frozenset[str]: ...
