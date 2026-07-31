"""Fast resource-limit checks for hostile parser inputs."""

from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter
from tests.fakes.parsing import StaticOcrEngine, generated_format_samples, parse_request

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers
from ragflow_agent.knowledge.infrastructure.parsers.security import (
    validate_image,
    validate_zip_package,
)


def test_ooxml_entry_and_compression_ratio_limits_fail_closed() -> None:
    stream = BytesIO()
    with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", "A" * 20_000)
    with pytest.raises(KnowledgeConflictError) as compression:
        validate_zip_package(
            stream.getvalue(),
            max_entries=10,
            max_uncompressed_bytes=100_000,
            max_compression_ratio=2,
        )
    assert compression.value.error_code == "parser_resource_limit"
    assert compression.value.details["resource"] == "ooxml_compression_ratio"


def test_image_pixel_limit_fails_before_ocr() -> None:
    with pytest.raises(KnowledgeConflictError) as pixels:
        validate_image(Image.new("RGB", (101, 100)), max_pixels=10_000)
    assert pixels.value.error_code == "parser_resource_limit"
    assert pixels.value.details["resource"] == "image_pixels"


def test_pdf_page_and_xlsx_sheet_limits_fail_closed() -> None:
    pdf_sample = next(
        item for item in generated_format_samples() if item.name.endswith(".pdf")
    )
    reader = PdfReader(BytesIO(pdf_sample.payload))
    writer = PdfWriter()
    writer.add_page(reader.pages[0])
    writer.add_page(reader.pages[0])
    repeated_pdf = BytesIO()
    writer.write(repeated_pdf)
    pdf_parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(pdf_max_pages=1),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-pdf-layout"
    )
    with pytest.raises(KnowledgeConflictError) as pages:
        pdf_parser.parse_bytes(
            repeated_pdf.getvalue(),
            parse_request(pdf_sample),
            ocr_language="eng",
        )
    assert pages.value.details["resource"] == "pdf_pages"

    xlsx_sample = next(
        item for item in generated_format_samples() if item.name.endswith(".xlsx")
    )
    xlsx_parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(xlsx_max_sheets=1),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-xlsx"
    )
    with pytest.raises(KnowledgeConflictError) as sheets:
        xlsx_parser.parse_bytes(
            xlsx_sample.payload,
            parse_request(xlsx_sample),
            ocr_language="eng",
        )
    assert sheets.value.details["resource"] == "xlsx_sheets"


def test_parser_adapters_are_repeatable_under_bounded_concurrency() -> None:
    sample = next(
        item for item in generated_format_samples() if item.name.endswith(".docx")
    )
    parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-docx"
    )

    def parse_once() -> tuple[tuple[str, str], ...]:
        result = parser.parse_bytes(
            sample.payload,
            parse_request(sample),
            ocr_language="eng",
        )
        return tuple((block.kind.value, block.text) for block in result.blocks)

    with ThreadPoolExecutor(max_workers=4) as pool:
        outputs = list(pool.map(lambda _: parse_once(), range(8)))
    assert outputs
    assert all(output == outputs[0] for output in outputs)
