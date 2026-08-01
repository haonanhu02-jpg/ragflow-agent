"""Provider-isolated multimodal derivation with page/box/time provenance."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedCapability
from ragflow_agent.knowledge.advanced.enrichment.common import artifact_from_chunk
from ragflow_agent.knowledge.advanced.ports import SpeechRecognitionPort, VisionDescriptionPort
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.chunk import BoundingBox, ChunkRecord


class MediaKind(StrEnum):
    IMAGE = "image"
    CHART = "chart"
    AUDIO = "audio"


class MediaInput(KnowledgeModel):
    kind: MediaKind
    media_type: NonEmptyStr
    content: bytes
    page_number: int | None = Field(default=None, ge=1)
    bounding_box: BoundingBox | None = None
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    duration_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def coordinates_match_kind(self) -> MediaInput:
        if self.kind in {MediaKind.IMAGE, MediaKind.CHART} and self.page_number is None:
            raise ValueError("image and chart inputs require page_number")
        if self.bounding_box is not None and self.page_number is None:
            raise ValueError("bounding_box requires page_number")
        if self.kind is MediaKind.AUDIO and self.duration_seconds is None:
            raise ValueError("audio inputs require duration_seconds")
        return self


class MultimodalService:
    def __init__(
        self,
        *,
        vision: VisionDescriptionPort,
        speech: SpeechRecognitionPort,
        max_image_bytes: int = 20 * 1024 * 1024,
        max_image_pixels: int = 25_000_000,
        max_audio_seconds: int = 1_800,
    ) -> None:
        self._vision = vision
        self._speech = speech
        self._max_image_bytes = max_image_bytes
        self._max_image_pixels = max_image_pixels
        self._max_audio_seconds = max_audio_seconds

    async def derive(
        self,
        chunk: ChunkRecord,
        media: MediaInput,
        *,
        build_version: str,
        created_at: datetime,
    ) -> tuple[AdvancedArtifact, ...]:
        if media.kind in {MediaKind.IMAGE, MediaKind.CHART}:
            pixels = (media.width or 0) * (media.height or 0)
            if len(media.content) > self._max_image_bytes or pixels > self._max_image_pixels:
                raise ValueError("image resource budget exceeded")
            text = await self._vision.describe(media_type=media.media_type, content=media.content)
            attributes = (
                ("media_kind", media.kind.value),
                ("page_number", str(media.page_number)),
                (
                    "bounding_box",
                    "none" if media.bounding_box is None else media.bounding_box.model_dump_json(),
                ),
            )
            return (
                artifact_from_chunk(
                    chunk,
                    capability=AdvancedCapability.MULTIMODAL,
                    build_version=build_version,
                    text=text,
                    created_at=created_at,
                    attributes=attributes,
                ),
            )
        if (media.duration_seconds or 0) > self._max_audio_seconds:
            raise ValueError("audio resource budget exceeded")
        segments = await self._speech.transcribe(media_type=media.media_type, content=media.content)
        if not segments:
            raise ValueError("speech provider returned no transcript")
        segment_seconds = (media.duration_seconds or 0) / len(segments)
        return tuple(
            artifact_from_chunk(
                chunk,
                capability=AdvancedCapability.MULTIMODAL,
                build_version=build_version,
                text=text,
                created_at=created_at,
                attributes=(
                    ("media_kind", MediaKind.AUDIO.value),
                    ("time_start_seconds", f"{index * segment_seconds:.3f}"),
                    ("time_end_seconds", f"{(index + 1) * segment_seconds:.3f}"),
                ),
            ).model_copy(update={"id": f"adv_audio_{chunk.id}_{index}"})
            for index, text in enumerate(segments)
        )
