"""Independent Phase 05 parser adapters and their bounded default profile."""

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.infrastructure.parsers.basic import BasicObjectParser
from ragflow_agent.knowledge.infrastructure.parsers.docx import DocxBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.html import HtmlBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.image import ImageBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.markdown import MarkdownBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.pdf import PdfBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.pptx import PptxBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.text import TextBinaryParser
from ragflow_agent.knowledge.infrastructure.parsers.xlsx import XlsxBinaryParser
from ragflow_agent.knowledge.ports.ocr import OcrEnginePort
from ragflow_agent.knowledge.ports.parsing import BinaryParserPort


def build_default_binary_parsers(
    settings: IngestionSettings,
    *,
    ocr: OcrEnginePort,
) -> tuple[BinaryParserPort, ...]:
    """Build the explicit, bounded Phase 05 format profile."""
    return (
        TextBinaryParser(),
        MarkdownBinaryParser(),
        HtmlBinaryParser(),
        DocxBinaryParser(
            max_entries=settings.ooxml_max_entries,
            max_uncompressed_bytes=settings.ooxml_max_uncompressed_bytes,
            max_compression_ratio=settings.ooxml_max_compression_ratio,
        ),
        PptxBinaryParser(
            max_entries=settings.ooxml_max_entries,
            max_uncompressed_bytes=settings.ooxml_max_uncompressed_bytes,
            max_compression_ratio=settings.ooxml_max_compression_ratio,
        ),
        XlsxBinaryParser(
            max_entries=settings.ooxml_max_entries,
            max_uncompressed_bytes=settings.ooxml_max_uncompressed_bytes,
            max_compression_ratio=settings.ooxml_max_compression_ratio,
            max_sheets=settings.xlsx_max_sheets,
            max_rows_per_sheet=settings.xlsx_max_rows_per_sheet,
            max_nonempty_cells=settings.xlsx_max_nonempty_cells,
        ),
        PdfBinaryParser(
            ocr=ocr,
            max_pages=settings.pdf_max_pages,
            max_image_pixels=settings.image_max_pixels,
        ),
        ImageBinaryParser(ocr=ocr, max_pixels=settings.image_max_pixels),
    )


__all__ = [
    "BasicObjectParser",
    "DocxBinaryParser",
    "HtmlBinaryParser",
    "ImageBinaryParser",
    "MarkdownBinaryParser",
    "PdfBinaryParser",
    "PptxBinaryParser",
    "TextBinaryParser",
    "XlsxBinaryParser",
    "build_default_binary_parsers",
]
