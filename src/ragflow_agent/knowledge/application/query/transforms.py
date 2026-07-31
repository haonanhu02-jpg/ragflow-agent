"""Bounded rewrite, translation, and keyword variants with safe fallback."""

from __future__ import annotations

from dataclasses import dataclass

from ragflow_agent.knowledge.application.query.preprocess import PreprocessedQuery
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import QueryVariant, QueryVariantKind
from ragflow_agent.knowledge.ports.generation import (
    QueryTransformKind,
    QueryTransformProviderPort,
    QueryTransformRequest,
)


@dataclass(frozen=True, slots=True)
class QueryTransformOutcome:
    variants: tuple[QueryVariant, ...]
    failures: tuple[str, ...]


class QueryVariantBuilder:
    """Produce variants without ever carrying or mutating filters."""

    def __init__(
        self,
        provider: QueryTransformProviderPort,
        *,
        model_id: str,
        rewrite_enabled: bool,
        translation_enabled: bool,
        keyword_expansion_enabled: bool,
        max_variants: int,
    ) -> None:
        self._provider = provider
        self._model_id = model_id
        self._rewrite_enabled = rewrite_enabled
        self._translation_enabled = translation_enabled
        self._keyword_expansion_enabled = keyword_expansion_enabled
        self._max_variants = max_variants

    async def build(
        self,
        context: AuthorizationContext,
        *,
        processed: PreprocessedQuery,
        history: tuple[str, ...],
        target_languages: tuple[str, ...],
        trace_id: str,
    ) -> QueryTransformOutcome:
        variants = [
            QueryVariant(
                text=processed.canonical_text,
                kind=QueryVariantKind.CANONICAL,
                language=processed.language,
            )
        ]
        failures: list[str] = []
        if self._rewrite_enabled and history:
            await self._append_provider_variants(
                variants,
                failures,
                context=context,
                request=QueryTransformRequest(
                    model_id=self._model_id,
                    kind=QueryTransformKind.REWRITE,
                    query=processed.canonical_text,
                    history=history[-8:],
                    max_items=1,
                    trace_id=trace_id,
                ),
                kind=QueryVariantKind.REWRITE,
            )
        if self._translation_enabled and target_languages:
            await self._append_provider_variants(
                variants,
                failures,
                context=context,
                request=QueryTransformRequest(
                    model_id=self._model_id,
                    kind=QueryTransformKind.TRANSLATE,
                    query=processed.canonical_text,
                    target_languages=target_languages,
                    max_items=min(len(target_languages), 4),
                    trace_id=trace_id,
                ),
                kind=QueryVariantKind.TRANSLATION,
            )
        if self._keyword_expansion_enabled and processed.lexical_keywords:
            lexical = " ".join(processed.lexical_keywords)
            if lexical != processed.canonical_text.casefold():
                variants.append(QueryVariant(text=lexical, kind=QueryVariantKind.KEYWORD))
            await self._append_provider_variants(
                variants,
                failures,
                context=context,
                request=QueryTransformRequest(
                    model_id=self._model_id,
                    kind=QueryTransformKind.KEYWORDS,
                    query=processed.canonical_text,
                    max_items=4,
                    trace_id=trace_id,
                ),
                kind=QueryVariantKind.KEYWORD,
            )
        deduplicated: list[QueryVariant] = []
        seen: set[str] = set()
        for variant in variants:
            key = variant.text.casefold()
            if key not in seen:
                seen.add(key)
                deduplicated.append(variant)
        return QueryTransformOutcome(
            variants=tuple(deduplicated[: self._max_variants]),
            failures=tuple(failures),
        )

    async def _append_provider_variants(
        self,
        variants: list[QueryVariant],
        failures: list[str],
        *,
        context: AuthorizationContext,
        request: QueryTransformRequest,
        kind: QueryVariantKind,
    ) -> None:
        try:
            result = await self._provider.transform(context, request)
        except Exception as error:  # provider failure is a documented canonical-query fallback
            failures.append(f"{request.kind.value}:{type(error).__name__}")
            return
        variants.extend(
            QueryVariant(text=item, kind=kind, provider=result.model_id) for item in result.items
        )
