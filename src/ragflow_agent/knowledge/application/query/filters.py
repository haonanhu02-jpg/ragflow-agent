"""Filter AST inspection helpers; backend compilation remains in adapters."""

from __future__ import annotations

from hashlib import sha256

from ragflow_agent.knowledge.domain.retrieval import (
    MetadataFilter,
    MetadataFilterGroup,
    RetrievalQuery,
)


def filter_summary(query: RetrievalQuery) -> tuple[str, ...]:
    """Return content-free stable hashes for user and inferred filters."""

    summaries = [
        "hard:tenant",
        f"hard:knowledge_bases:{len(query.knowledge_base_ids)}",
        f"hard:index_versions:{len(query.index_version_ids)}",
        f"user_filters:{len(query.filters)}",
        f"user_ast:{_digest(query.filter_expression)}",
        f"inferred_ast:{_digest(query.inferred_filter_expression)}",
    ]
    return tuple(summaries)


def _digest(value: MetadataFilter | MetadataFilterGroup | None) -> str:
    if value is None:
        return "none"
    payload = value.model_dump_json().encode("utf-8")
    return sha256(payload).hexdigest()[:16]
