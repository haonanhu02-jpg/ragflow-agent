"""Deterministic, versioned query normalization and language hints."""

from __future__ import annotations

import re
import unicodedata

from pydantic import Field

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr

_WHITESPACE = re.compile(r"\s+")
_TOKENS = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]*|[\u3400-\u9fff]{2,}")


class PreprocessedQuery(KnowledgeModel):
    """Normalized query without authorization or backend state."""

    canonical_text: NonEmptyStr
    language: NonEmptyStr
    lexical_keywords: tuple[NonEmptyStr, ...] = Field(max_length=16)
    transform_version: NonEmptyStr = "query-normalize-v1"


class QueryPreprocessor:
    """Normalize Unicode/control characters and derive bounded lexical terms."""

    def __init__(self, *, max_characters: int) -> None:
        self._max_characters = max_characters

    def process(self, text: str) -> PreprocessedQuery:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = "".join(
            char
            for char in normalized
            if unicodedata.category(char) not in {"Cc", "Cf"} or char in "\t\n\r"
        )
        normalized = _WHITESPACE.sub(" ", normalized).strip()
        if not normalized:
            raise ValueError("query is empty after normalization")
        if len(normalized) > self._max_characters:
            raise ValueError("query exceeds configured character limit")
        cjk_count = sum("\u3400" <= char <= "\u9fff" for char in normalized)
        latin_count = sum(char.isascii() and char.isalpha() for char in normalized)
        language = "zh" if cjk_count > latin_count else "en" if latin_count else "und"
        keywords = tuple(dict.fromkeys(token.casefold() for token in _TOKENS.findall(normalized)))[
            :16
        ]
        return PreprocessedQuery(
            canonical_text=normalized,
            language=language,
            lexical_keywords=keywords,
        )
