"""Safe HTML structure parser that removes executable and hidden content."""

from __future__ import annotations

from bs4 import BeautifulSoup

from ragflow_agent.knowledge.domain.chunk import (
    BlockKind,
    ImageReference,
    ParsedBlock,
    TableMetadata,
)
from ragflow_agent.knowledge.ports.parsing import (
    ParsedPayload,
    ParserCapability,
    ParseRequest,
)


class HtmlBinaryParser:
    """Retain document order without executing active HTML content."""

    capability = ParserCapability(
        parser_id="independent-html",
        parser_version="2",
        media_types=frozenset({"text/html"}),
        extensions=frozenset({".html", ".htm"}),
        default_chunk_strategy="manual",
    )

    def parse_bytes(
        self,
        payload: bytes,
        request: ParseRequest,
        *,
        ocr_language: str,
    ) -> ParsedPayload:
        del ocr_language
        soup = BeautifulSoup(payload, "html.parser")
        for node in soup(["script", "style", "noscript", "template"]):
            node.decompose()
        blocks: list[ParsedBlock] = []
        heading_path: tuple[str, ...] = ()
        for node in soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "table", "img"]
        ):
            if node.name and node.name.startswith("h") and len(node.name) == 2:
                value = node.get_text(" ", strip=True)
                if not value:
                    continue
                level = int(node.name[1])
                heading_path = (*heading_path[: level - 1], value)
                blocks.append(
                    ParsedBlock(
                        id=f"html_{len(blocks)}",
                        kind=BlockKind.HEADING,
                        order=len(blocks),
                        text=value,
                        heading_path=heading_path,
                    )
                )
            elif node.name == "table":
                rows = [
                    [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
                    for row in node.find_all("tr")
                ]
                rows = [row for row in rows if any(row)]
                if rows:
                    blocks.append(
                        ParsedBlock(
                            id=f"html_{len(blocks)}",
                            kind=BlockKind.TABLE,
                            order=len(blocks),
                            text="\n".join("\t".join(row) for row in rows),
                            heading_path=heading_path,
                            table=TableMetadata(
                                rows=len(rows),
                                columns=max(len(row) for row in rows),
                                has_header=node.find("th") is not None,
                            ),
                        )
                    )
            elif node.name == "img":
                alt = str(node.get("alt") or "embedded image").strip()
                source = str(node.get("src") or f"image-{len(blocks)}")
                blocks.append(
                    ParsedBlock(
                        id=f"html_{len(blocks)}",
                        kind=BlockKind.IMAGE,
                        order=len(blocks),
                        text=alt,
                        heading_path=heading_path,
                        image=ImageReference(
                            object_key=request.object_key,
                            embedded_path=source,
                            media_type="image/unknown",
                        ),
                    )
                )
            else:
                value = node.get_text(" ", strip=True)
                if not value or node.find_parent(["li", "table"]) is not None:
                    continue
                kind = {
                    "li": BlockKind.LIST,
                    "pre": BlockKind.CODE,
                }.get(node.name, BlockKind.TEXT)
                blocks.append(
                    ParsedBlock(
                        id=f"html_{len(blocks)}",
                        kind=kind,
                        order=len(blocks),
                        text=value,
                        heading_path=heading_path,
                    )
                )
        return ParsedPayload(blocks=tuple(blocks))
