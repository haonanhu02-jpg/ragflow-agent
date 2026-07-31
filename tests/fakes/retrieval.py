"""Deterministic Phase 06 retrieval, reranker, transform, and trace fakes."""

from __future__ import annotations

import asyncio
from datetime import datetime

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalTrace,
    ScoreBreakdown,
)
from ragflow_agent.knowledge.ports.generation import (
    QueryTransformRequest,
    QueryTransformResult,
)
from ragflow_agent.knowledge.ports.search import RerankRequest


def retrieval_candidate(
    chunk_id: str,
    *,
    document_id: str | None = None,
    full_text_score: float | None = None,
    vector_score: float | None = None,
) -> RetrievalCandidate:
    """Build one stable tenant-scoped candidate."""
    document = document_id or f"doc-{chunk_id}"
    citation = Citation(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id=document,
        document_version_id=f"version-{document}",
        chunk_id=chunk_id,
        quote=f"evidence {chunk_id}",
        page_number=1,
    )
    score = full_text_score if full_text_score is not None else vector_score or 0
    return RetrievalCandidate(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id=document,
        document_version_id=f"version-{document}",
        chunk_id=chunk_id,
        content=f"evidence {chunk_id}",
        score=ScoreBreakdown(
            final_score=score,
            full_text_score=full_text_score,
            vector_score=vector_score,
        ),
        citation=citation,
    )


class FakeSearchChannels:
    """Return configured channels and retain every immutable query snapshot."""

    def __init__(
        self,
        *,
        full_text: tuple[RetrievalCandidate, ...] = (),
        vector: tuple[RetrievalCandidate, ...] = (),
        fail_full_text: bool = False,
        fail_vector: bool = False,
        minimum_top_k: int = 0,
    ) -> None:
        self.full_text = full_text
        self.vector = vector
        self.fail_full_text = fail_full_text
        self.fail_vector = fail_vector
        self.minimum_top_k = minimum_top_k
        self.full_text_queries: list[RetrievalQuery] = []
        self.vector_queries: list[RetrievalQuery] = []

    async def retrieve_full_text(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]:
        del context
        self.full_text_queries.append(query)
        if self.fail_full_text:
            raise RuntimeError("full text unavailable")
        return self.full_text if query.top_k >= self.minimum_top_k else ()

    async def retrieve_vector(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]:
        del context
        self.vector_queries.append(query)
        if self.fail_vector:
            raise RuntimeError("vector unavailable")
        return self.vector if query.top_k >= self.minimum_top_k else ()


class FakeReranker:
    """Assign configured scores, raise, or sleep for timeout tests."""

    def __init__(
        self,
        scores: dict[str, float] | None = None,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0,
    ) -> None:
        self.scores = scores or {}
        self.error = error
        self.delay_seconds = delay_seconds
        self.requests: list[RerankRequest] = []

    async def rerank(
        self,
        context: AuthorizationContext,
        request: RerankRequest,
    ) -> tuple[RetrievalCandidate, ...]:
        del context
        self.requests.append(request)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        ranked = sorted(
            request.candidates,
            key=lambda item: (-self.scores.get(item.chunk_id, 0), item.chunk_id),
        )
        return tuple(
            candidate.model_copy(
                update={
                    "score": candidate.score.model_copy(
                        update={
                            "rerank_score": self.scores.get(candidate.chunk_id, 0),
                            "rerank_rank": rank,
                        }
                    )
                }
            )
            for rank, candidate in enumerate(ranked, start=1)
        )


class StubQueryTransformProvider:
    """Return configured items without an external model."""

    def __init__(self, items: dict[str, tuple[str, ...]] | None = None) -> None:
        self.items = items or {}
        self.requests: list[QueryTransformRequest] = []

    async def transform(
        self,
        context: AuthorizationContext,
        request: QueryTransformRequest,
    ) -> QueryTransformResult:
        del context
        self.requests.append(request)
        return QueryTransformResult(
            model_id=request.model_id,
            items=self.items.get(request.kind.value, ()),
        )


class MemoryRetrievalTraceStore:
    """Tenant-scoped in-memory trace store with executable TTL cleanup."""

    def __init__(self) -> None:
        self.traces: dict[tuple[str, str], RetrievalTrace] = {}
        self.error: Exception | None = None

    async def save(self, trace: RetrievalTrace) -> None:
        if self.error is not None:
            raise self.error
        payload = trace.model_dump(mode="json")
        self.traces[(trace.tenant_id, trace.trace_id)] = RetrievalTrace.model_validate(payload)

    async def get(
        self,
        context: AuthorizationContext,
        trace_id: str,
    ) -> RetrievalTrace | None:
        return self.traces.get((context.tenant_id, trace_id))

    async def delete_expired(self, *, before: datetime) -> int:
        keys = [
            key
            for key, trace in self.traces.items()
            if trace.expires_at is not None and trace.expires_at <= before
        ]
        for key in keys:
            del self.traces[key]
        return len(keys)
