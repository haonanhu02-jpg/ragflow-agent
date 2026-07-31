"""Parser resource guards for untrusted images and OOXML packages."""

from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile

from PIL import Image

from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError


def validate_zip_package(
    payload: bytes,
    *,
    max_entries: int,
    max_uncompressed_bytes: int,
    max_compression_ratio: float,
) -> None:
    """Reject malformed or decompression-bomb-like OOXML containers."""
    try:
        with ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
    except BadZipFile as error:
        raise KnowledgeConflictError(
            "Office Open XML package is invalid",
            error_code="parser_ooxml_invalid",
        ) from error
    if len(entries) > max_entries:
        raise KnowledgeConflictError(
            "Office Open XML package has too many entries",
            error_code="parser_resource_limit",
            details={"resource": "ooxml_entries", "actual": len(entries)},
        )
    total = sum(entry.file_size for entry in entries)
    if total > max_uncompressed_bytes:
        raise KnowledgeConflictError(
            "Office Open XML package exceeds the uncompressed-size limit",
            error_code="parser_resource_limit",
            details={"resource": "ooxml_uncompressed_bytes", "actual": total},
        )
    for entry in entries:
        if entry.file_size == 0:
            continue
        ratio = entry.file_size / max(entry.compress_size, 1)
        if ratio > max_compression_ratio:
            raise KnowledgeConflictError(
                "Office Open XML package has an unsafe compression ratio",
                error_code="parser_resource_limit",
                details={"resource": "ooxml_compression_ratio", "entry": entry.filename},
            )


def validate_image(
    image: Image.Image,
    *,
    max_pixels: int,
) -> None:
    """Reject images whose decoded dimensions exceed the configured budget."""
    width, height = image.size
    if width < 1 or height < 1 or width * height > max_pixels:
        raise KnowledgeConflictError(
            "image exceeds the configured pixel limit",
            error_code="parser_resource_limit",
            details={
                "resource": "image_pixels",
                "width": width,
                "height": height,
            },
        )
