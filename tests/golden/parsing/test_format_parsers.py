"""Golden parser behavior over generated, repository-safe samples."""

from tests.fakes.parsing import StaticOcrEngine, generated_format_samples, parse_request

from ragflow_agent.config import IngestionSettings
from ragflow_agent.knowledge.domain.chunk import BlockKind
from ragflow_agent.knowledge.infrastructure.parsers import build_default_binary_parsers


def test_all_phase05_formats_preserve_expected_structure_and_source_order() -> None:
    ocr = StaticOcrEngine()
    parsers = build_default_binary_parsers(IngestionSettings(), ocr=ocr)
    for sample in generated_format_samples():
        request = parse_request(sample)
        extension = f".{sample.name.rsplit('.', maxsplit=1)[1]}"
        parser = next(
            item
            for item in parsers
            if sample.media_type in item.capability.media_types
            and extension in item.capability.extensions
        )
        result = parser.parse_bytes(
            sample.payload,
            request,
            ocr_language="eng",
        )
        kinds = frozenset(block.kind.value for block in result.blocks)
        assert sample.expected_kinds <= kinds, sample.name
        assert [block.order for block in result.blocks] == list(range(len(result.blocks)))
        assert len({block.id for block in result.blocks}) == len(result.blocks)
        for block in result.blocks:
            if block.kind is BlockKind.TABLE:
                assert block.table is not None
                assert block.table.rows >= 1
                assert block.table.columns >= 1


def test_html_removes_active_content_and_keeps_image_provenance() -> None:
    sample = next(item for item in generated_format_samples() if item.name.endswith(".html"))
    parser = build_default_binary_parsers(
        IngestionSettings(),
        ocr=StaticOcrEngine(),
    )[2]
    result = parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert "secret" not in "\n".join(block.text for block in result.blocks)
    image = next(block for block in result.blocks if block.kind is BlockKind.IMAGE)
    assert image.image is not None
    assert image.image.embedded_path == "relay.png"


def test_xlsx_preserves_formula_as_text_and_reports_degradation() -> None:
    sample = next(item for item in generated_format_samples() if item.name.endswith(".xlsx"))
    parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-xlsx"
    )
    result = parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert "CONCAT" in result.blocks[0].text
    warning_codes = {warning.code for warning in result.warnings}
    assert warning_codes == {
        "xlsx_formula_preserved_not_evaluated",
        "xlsx_merged_cells_present",
    }


def test_pdf_retains_page_geometry_and_table_shape() -> None:
    sample = next(item for item in generated_format_samples() if item.name.endswith(".pdf"))
    parser = next(
        item
        for item in build_default_binary_parsers(
            IngestionSettings(),
            ocr=StaticOcrEngine(),
        )
        if item.capability.parser_id == "independent-pdf-layout"
    )
    result = parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert not result.warnings
    assert all(block.page_number == 1 for block in result.blocks)
    assert all(block.bounding_box is not None for block in result.blocks)
    table = next(block for block in result.blocks if block.kind is BlockKind.TABLE)
    assert table.table is not None
    assert (table.table.rows, table.table.columns) == (2, 2)
    ordered_text = [block.text for block in result.blocks if block.kind is BlockKind.TEXT]
    left_index = next(index for index, value in enumerate(ordered_text) if "LEFT COLUMN" in value)
    right_index = next(index for index, value in enumerate(ordered_text) if "RIGHT COLUMN" in value)
    assert left_index < right_index


def test_image_uses_ocr_port_and_keeps_pixel_geometry() -> None:
    sample = next(item for item in generated_format_samples() if item.name.endswith(".png"))
    ocr = StaticOcrEngine()
    parser = next(
        item
        for item in build_default_binary_parsers(IngestionSettings(), ocr=ocr)
        if item.capability.parser_id == "independent-image-ocr"
    )
    result = parser.parse_bytes(sample.payload, parse_request(sample), ocr_language="eng")
    assert ocr.calls == ["eng"]
    assert result.blocks[0].kind is BlockKind.IMAGE
    assert result.blocks[0].image is not None
    assert result.blocks[0].image.width == 480
    assert "alarm reset inspection" in result.blocks[1].text
