"""Deterministic Phase 04 providers and hybrid search for CI/E2E."""

from __future__ import annotations

import math
import re
from hashlib import sha256

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    IndexRecord,
    IndexVersion,
    RetrievalCandidate,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    ScoreBreakdown,
)
from ragflow_agent.knowledge.ports.embedding import (
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingVector,
)
from ragflow_agent.knowledge.ports.generation import (
    ChatGenerationRequest,
    ChatGenerationResult,
)

_WORDS = re.compile(r"\w+", re.UNICODE)


class KeywordEmbedding:
    """Small normalized hash embedding that preserves token overlap."""

    def __init__(self, *, model_id: str = "BAAI/bge-m3", dimensions: int = 16) -> None:
        self.model_id = model_id
        self.dimensions = dimensions

    async def embed(
        self,
        context: AuthorizationContext,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        if context.tenant_id != request.tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        vectors = tuple(
            EmbeddingVector(input_id=item.id, values=self.vector(item.text))
            for item in request.inputs
        )
        return EmbeddingResult(
            model_id=request.model_id,
            dimensions=self.dimensions,
            normalized=True,
            vectors=vectors,
        )

    def vector(self, text: str) -> tuple[float, ...]:
        values = [0.0] * self.dimensions
        for word in _WORDS.findall(text.casefold()):
            index = int.from_bytes(sha256(word.encode()).digest()[:4], "big") % self.dimensions
            values[index] += 1
        norm = math.sqrt(sum(value * value for value in values)) or 1
        return tuple(value / norm for value in values)


class StubChatProvider:
    """Return a stable cited answer without network access."""

    def __init__(self, *, model_id: str = "deepseek-chat") -> None:
        self.model_id = model_id
        self.requests: list[ChatGenerationRequest] = []

    async def generate(
        self,
        context: AuthorizationContext,
        request: ChatGenerationRequest,
    ) -> ChatGenerationResult:
        del context
        self.requests.append(request)
        return ChatGenerationResult(
            model_id=self.model_id,
            content="根据已授权证据, 设备需要执行复位检查。[1]",
        )


class MemoryHybridSearch:
    """In-memory BM25-like/vector hybrid implementation for deterministic E2E."""

    def __init__(self, embedding: KeywordEmbedding) -> None:
        self._embedding = embedding
        self.records: dict[tuple[str, str, str], IndexRecord] = {}
        self.active_versions: dict[tuple[str, str], str] = {}

    async def upsert(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
        records: tuple[IndexRecord, ...],
    ) -> None:
        self._require_tenant(context, version.tenant_id)
        for record in records:
            self.records[(record.tenant_id, record.index_version_id, record.chunk_id)] = record

    async def delete(
        self,
        context: AuthorizationContext,
        *,
        index_version_id: str,
        chunk_ids: tuple[str, ...],
    ) -> None:
        keys = [
            key
            for key in self.records
            if key[0] == context.tenant_id
            and key[1] == index_version_id
            and key[2] in chunk_ids
        ]
        for key in keys:
            del self.records[key]

    async def activate(
        self,
        context: AuthorizationContext,
        version: IndexVersion,
    ) -> None:
        self._require_tenant(context, version.tenant_id)
        self.active_versions[(version.tenant_id, version.knowledge_base_id)] = version.id

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        self._require_tenant(context, query.tenant_id)
        query_words = set(_WORDS.findall(query.text.casefold()))
        query_vector = self._embedding.vector(query.text)
        ranked: list[RetrievalCandidate] = []
        for record in self.records.values():
            if not self._allowed(context, query, record):
                continue
            words = set(_WORDS.findall(record.content.casefold()))
            text_score = float(len(query_words & words))
            vector_score = sum(
                left * right for left, right in zip(query_vector, record.embedding, strict=True)
            )
            final_score = text_score + vector_score
            if final_score <= 0:
                continue
            citation = Citation(
                tenant_id=record.tenant_id,
                knowledge_base_id=record.knowledge_base_id,
                document_id=record.document_id,
                document_version_id=record.document_version_id,
                chunk_id=record.chunk_id,
                quote=record.content,
                page_number=record.metadata.page_start,
                bounding_box=record.metadata.bounding_box,
                source_uri=(
                    f"documents/{record.document_id}/versions/{record.document_version_id}"
                ),
            )
            ranked.append(
                RetrievalCandidate(
                    tenant_id=record.tenant_id,
                    knowledge_base_id=record.knowledge_base_id,
                    document_id=record.document_id,
                    document_version_id=record.document_version_id,
                    chunk_id=record.chunk_id,
                    content=record.content,
                    score=ScoreBreakdown(
                        final_score=final_score,
                        full_text_score=text_score,
                        vector_score=vector_score,
                        fusion_score=final_score,
                    ),
                    citation=citation,
                )
            )
        ranked.sort(key=lambda item: item.score.final_score, reverse=True)
        selected = tuple(ranked[: query.top_n])
        trace = RetrievalTrace(
            trace_id=query.trace_id,
            tenant_id=query.tenant_id,
            original_query=query.text,
            authorization_applied=True,
            events=(
                RetrievalTraceEvent(
                    sequence=0,
                    stage=RetrievalStage.AUTHORIZATION,
                    elapsed_ms=0,
                    candidate_count=len(selected),
                ),
                RetrievalTraceEvent(
                    sequence=1,
                    stage=RetrievalStage.FUSION,
                    elapsed_ms=0,
                    candidate_count=len(selected),
                ),
            ),
        )
        return RetrievalResult(
            query=query,
            candidates=selected,
            trace=trace,
            empty_reason=None if selected else RetrievalEmptyReason.NO_MATCH,
        )

    def _allowed(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
        record: IndexRecord,
    ) -> bool:
        active = self.active_versions.get((record.tenant_id, record.knowledge_base_id))
        return (
            record.tenant_id == context.tenant_id
            and record.knowledge_base_id in query.knowledge_base_ids
            and record.index_version_id == active
            and (
                record.owner_id == context.actor_id
                or record.visibility is Visibility.TENANT
            )
        )

    @staticmethod
    def _require_tenant(context: AuthorizationContext, tenant_id: str) -> None:
        if context.tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
