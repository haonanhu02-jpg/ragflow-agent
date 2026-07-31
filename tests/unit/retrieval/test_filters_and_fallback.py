"""Filter AST and immutable hard-scope fallback tests."""

import pytest
from pydantic import SecretStr, ValidationError
from tests.fakes.minimum_rag import KeywordEmbedding

from ragflow_agent.config import SearchSettings
from ragflow_agent.knowledge.application.query.fallback import fallback_attempts
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import (
    FilterGroupOperator,
    FilterOperator,
    MetadataField,
    MetadataFilter,
    MetadataFilterGroup,
    RetrievalQuery,
)
from ragflow_agent.knowledge.infrastructure.search import ElasticsearchSearchAdapter


def _filters() -> tuple[MetadataFilterGroup, MetadataFilterGroup]:
    user = MetadataFilterGroup(
        operator=FilterGroupOperator.AND,
        items=(
            MetadataFilter(
                field=MetadataField.LANGUAGE,
                operator=FilterOperator.EQUALS,
                value="zh",
            ),
        ),
    )
    inferred = MetadataFilterGroup(
        operator=FilterGroupOperator.OR,
        items=(
            MetadataFilter(
                field=MetadataField.CONTAINS_TABLE,
                operator=FilterOperator.EQUALS,
                value=True,
            ),
            MetadataFilter(
                field=MetadataField.CONTAINS_IMAGE,
                operator=FilterOperator.EQUALS,
                value=True,
            ),
        ),
    )
    return user, inferred


def test_filter_ast_validates_not_arity() -> None:
    leaf = MetadataFilter(
        field=MetadataField.LANGUAGE,
        operator=FilterOperator.EQUALS,
        value="zh",
    )
    with pytest.raises(ValidationError):
        MetadataFilterGroup(operator=FilterGroupOperator.NOT, items=(leaf, leaf))


def test_fallback_only_removes_inferred_filters_and_preserves_hard_scope() -> None:
    user, inferred = _filters()
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="reset",
        knowledge_base_ids=("kb-a",),
        index_version_ids=("index-a",),
        filter_expression=user,
        inferred_filter_expression=inferred,
        top_k=10,
        top_n=3,
        trace_id="trace-a",
    )

    attempts = fallback_attempts(
        query,
        normal_threshold=0.02,
        threshold_floor=0.005,
        candidate_multiplier=2,
        maximum_attempts=4,
    )

    assert len(attempts) == 4
    for attempt in attempts:
        assert attempt.query.tenant_id == query.tenant_id
        assert attempt.query.knowledge_base_ids == query.knowledge_base_ids
        assert attempt.query.index_version_ids == query.index_version_ids
        assert attempt.query.filter_expression == user
    assert attempts[0].query.inferred_filter_expression == inferred
    assert all(item.query.inferred_filter_expression is None for item in attempts[1:])


def test_elasticsearch_filters_always_include_tenant_acl_scope_and_state() -> None:
    embedding = KeywordEmbedding(dimensions=4)
    adapter = ElasticsearchSearchAdapter(
        SearchSettings(url=SecretStr("http://localhost:9200"), index_name="test"),
        embedding=embedding,
        embedding_model_id=embedding.model_id,
        embedding_dimensions=embedding.dimensions,
    )
    user, inferred = _filters()
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="reset",
        knowledge_base_ids=("kb-a",),
        index_version_ids=("index-a",),
        filter_expression=user,
        inferred_filter_expression=inferred,
        trace_id="trace-a",
    )
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="actor-a",
        request_id="request-a",
        roles=("maintenance",),
    )

    compiled = adapter._filters(context, query)
    rendered = repr(compiled)

    assert "tenant_id" in rendered
    assert "knowledge_base_id" in rendered
    assert "index_version_id" in rendered
    assert "owner_id" in rendered
    assert "allowed_actor_ids" in rendered
    assert "allowed_roles" in rendered
    assert "document_enabled" in rendered
    assert "document_deleted" in rendered
    assert "language" in rendered
    assert "contains_table" in rendered
