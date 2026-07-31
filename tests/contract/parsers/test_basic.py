"""Minimum parser source, format, and failure contracts."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DictionaryObject,
    NameObject,
    NumberObject,
    StreamObject,
)

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.document import DocumentVersion
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.parsers import BasicObjectParser
from ragflow_agent.knowledge.ports.parsing import ParseRequest
from ragflow_agent.knowledge.ports.storage import StorageWriteRequest
from tests.fakes.knowledge import (
    FixedClock,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
)

NOW = datetime(2026, 7, 30, tzinfo=UTC)


async def _parser_for(payload: bytes, media_type: str) -> tuple[BasicObjectParser, ParseRequest]:
    store = MemoryKnowledgeStore()
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    storage = MemoryObjectStorage()
    context = AuthorizationContext(tenant_id="tenant-a", actor_id="owner-a", request_id="trace")
    version = DocumentVersion(
        id="version-a",
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        created_by="owner-a",
        object_key="tenants/tenant-a/source",
        media_type=media_type,
        content_hash=sha256(payload).hexdigest(),
        size_bytes=len(payload),
        created_at=NOW,
        updated_at=NOW,
    )
    async with factory() as unit_of_work:
        await unit_of_work.document_versions.add(tenant_id="tenant-a", entity=version)
        await unit_of_work.commit()

    async def parts() -> AsyncIterator[bytes]:
        yield payload

    await storage.put(
        context,
        StorageWriteRequest(
            tenant_id="tenant-a",
            object_key=version.object_key,
            media_type=media_type,
            size_bytes=len(payload),
            checksum_sha256=version.content_hash,
            trace_id="trace",
        ),
        parts(),
    )
    parser = BasicObjectParser(
        storage=storage,
        unit_of_work_factory=factory,
        clock=FixedClock(NOW),
        max_bytes=1024,
    )
    request = ParseRequest(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        object_key=version.object_key,
        media_type=media_type,
        trace_id="trace",
    )
    return parser, request


@pytest.mark.asyncio
async def test_text_and_markdown_preserve_order_and_heading_source() -> None:
    parser, request = await _parser_for(
        b"# Reset Procedure\n\nInspect relay cabinet.\n\n## Recovery\n\nReset controller.",
        "text/markdown",
    )

    parsed = await parser.parse(request)

    assert [block.order for block in parsed.blocks] == list(range(len(parsed.blocks)))
    assert parsed.blocks[0].text == "Reset Procedure"
    assert parsed.blocks[-1].heading_path == ("Reset Procedure", "Recovery")
    assert parsed.document_version_id == "version-a"


@pytest.mark.asyncio
async def test_unsupported_and_invalid_encoding_return_stable_errors() -> None:
    parser, request = await _parser_for(b"content", "application/octet-stream")
    with pytest.raises(KnowledgeConflictError) as unsupported:
        await parser.parse(request)
    assert unsupported.value.error_code == "parser_media_type_unsupported"

    parser, request = await _parser_for(b"\xff\xfe\xfd", "text/plain")
    with pytest.raises(KnowledgeConflictError) as invalid:
        await parser.parse(request)
    assert invalid.value.error_code == "parser_encoding_invalid"


def _single_page_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = StreamObject()
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode())
    stream_ref = writer._add_object(stream)
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = stream_ref
    page[NameObject("/Rotate")] = NumberObject(0)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_pdf_extracts_page_number_and_text() -> None:
    parser, request = await _parser_for(
        _single_page_pdf("Reset controller before inspection."),
        "application/pdf",
    )

    parsed = await parser.parse(request)

    assert len(parsed.blocks) == 1
    assert parsed.blocks[0].page_number == 1
    assert "Reset controller" in parsed.blocks[0].text
