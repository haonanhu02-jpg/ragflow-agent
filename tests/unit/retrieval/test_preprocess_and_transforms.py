"""Phase 06 query normalization and Provider-isolated variant tests."""

from datetime import UTC, datetime

import pytest
from tests.fakes.retrieval import StubQueryTransformProvider

from ragflow_agent.knowledge.application.query.preprocess import QueryPreprocessor
from ragflow_agent.knowledge.application.query.transforms import QueryVariantBuilder
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import QueryVariantKind

NOW = datetime(2026, 7, 31, tzinfo=UTC)


def test_preprocessor_normalizes_unicode_controls_and_detects_language() -> None:
    processed = QueryPreprocessor(max_characters=100).process(
        "  \uff21\uff2c\uff21\uff32\uff2d\x00   复位\n检查  "
    )

    assert processed.canonical_text == "ALARM 复位 检查"
    assert processed.language in {"en", "zh"}
    assert "alarm" in processed.lexical_keywords


def test_preprocessor_rejects_empty_and_over_limit_queries() -> None:
    preprocessor = QueryPreprocessor(max_characters=4)
    with pytest.raises(ValueError, match="empty"):
        preprocessor.process("\x00   ")
    with pytest.raises(ValueError, match="limit"):
        preprocessor.process("12345")


@pytest.mark.asyncio
async def test_rewrite_translation_and_keywords_are_bounded_and_keep_original() -> None:
    provider = StubQueryTransformProvider(
        {
            "rewrite": ("How should controller A be reset?",),
            "translate": ("控制器 A 如何复位\uff1f",),
            "keywords": ("controller A", "reset procedure"),
        }
    )
    builder = QueryVariantBuilder(
        provider,
        model_id="deepseek-chat",
        rewrite_enabled=True,
        translation_enabled=True,
        keyword_expansion_enabled=True,
        max_variants=6,
    )
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="request-a",
    )

    result = await builder.build(
        context,
        processed=QueryPreprocessor(max_characters=200).process("How to reset controller A?"),
        history=("Alarm A occurred", "What about it?"),
        target_languages=("zh",),
        trace_id="trace-a",
    )

    assert result.variants[0].kind is QueryVariantKind.CANONICAL
    assert {variant.kind for variant in result.variants} >= {
        QueryVariantKind.REWRITE,
        QueryVariantKind.TRANSLATION,
        QueryVariantKind.KEYWORD,
    }
    assert len(result.variants) <= 6
    assert result.failures == ()
