import pytest

from ragflow_agent.knowledge.advanced.multimodal.service import (
    MediaInput,
    MediaKind,
    MultimodalService,
)
from tests.fakes.advanced import NOW, FakeSpeechProvider, FakeVisionProvider, make_chunk


@pytest.mark.asyncio
async def test_image_chart_and_audio_have_page_or_time_provenance() -> None:
    service = MultimodalService(vision=FakeVisionProvider(), speech=FakeSpeechProvider())
    chunk = make_chunk("chunk-media", "media source")
    image = await service.derive(
        chunk,
        MediaInput(
            kind=MediaKind.CHART,
            media_type="image/svg+xml",
            content=b"<svg/>",
            page_number=3,
            width=100,
            height=50,
        ),
        build_version="build-1",
        created_at=NOW,
    )
    audio = await service.derive(
        chunk,
        MediaInput(
            kind=MediaKind.AUDIO,
            media_type="audio/wav",
            content=b"synthetic",
            duration_seconds=10,
        ),
        build_version="build-1",
        created_at=NOW,
    )
    assert dict(image[0].attributes)["page_number"] == "3"
    assert dict(audio[0].attributes)["time_start_seconds"] == "0.000"
    assert dict(audio[-1].attributes)["time_end_seconds"] == "10.000"
