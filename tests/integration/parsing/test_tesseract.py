"""Real Tesseract adapter verification; required in CI and skippable locally."""

from __future__ import annotations

import os

import pytest
from PIL import Image, ImageDraw, ImageFont

from ragflow_agent.knowledge.infrastructure.ocr import TesseractOcrEngine


def test_real_tesseract_english_and_language_pack_boundary() -> None:
    engine = TesseractOcrEngine()
    languages = engine.available_languages()
    required = os.environ.get("RAGFLOW_AGENT_TEST_REQUIRE_TESSERACT") == "1"
    if not languages:
        if required:
            pytest.fail("Tesseract is required but not installed")
        pytest.skip("Tesseract is not installed in this local environment")
    assert "eng" in languages
    if required:
        assert "chi_sim" in languages
    image = Image.new("RGB", (900, 180), "white")
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 52)
    except OSError:
        font = ImageFont.load_default(size=52)
    ImageDraw.Draw(image).text(
        (30, 50),
        "ALARM RESET CONTROLLER INSPECTION",
        fill="black",
        font=font,
        stroke_width=1,
    )
    result = engine.recognize(image, language="eng")
    normalized = " ".join(word.text.casefold() for word in result.words)
    assert "alarm" in normalized
    assert "reset" in normalized
    assert all(word.bounding_box.x1 > word.bounding_box.x0 for word in result.words)
    if required:
        cjk_font = ImageFont.truetype(
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            72,
        )
        chinese = Image.new("RGB", (720, 220), "white")
        ImageDraw.Draw(chinese).text(
            (40, 50),
            "故障 检修",
            fill="black",
            font=cjk_font,
        )
        chinese_result = engine.recognize(chinese, language="chi_sim")
        recognized = "".join(word.text for word in chinese_result.words)
        expected = set("故障检修")
        assert len(expected & set(recognized)) >= 2
