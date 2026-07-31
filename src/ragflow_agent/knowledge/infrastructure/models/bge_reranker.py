"""Provider-isolated HTTP adapter for a BGE-compatible rerank endpoint."""

from __future__ import annotations

from typing import Any, cast

import httpx

from ragflow_agent.config import ModelSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.retrieval import RetrievalCandidate
from ragflow_agent.knowledge.ports.search import RerankRequest
from ragflow_agent.shared import AppError


class BgeRerankerAdapter:
    """Call a `/rerank`-style endpoint without leaking its wire format upstream."""

    def __init__(
        self,
        *,
        endpoint: str,
        model_id: str,
        api_key: str | None,
        timeout_seconds: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model_id = model_id
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def rerank(
        self,
        context: AuthorizationContext,
        request: RerankRequest,
    ) -> tuple[RetrievalCandidate, ...]:
        if context.tenant_id != request.query.tenant_id:
            raise KnowledgeConflictError(
                "rerank tenant does not match request context",
                error_code="reranker_tenant_mismatch",
            )
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        response = await self._client.post(
            self._endpoint,
            headers=headers,
            json={
                "model": self.model_id,
                "query": request.query.text,
                "documents": [candidate.content for candidate in request.candidates],
                "top_n": len(request.candidates),
            },
        )
        response.raise_for_status()
        payload = cast(dict[str, Any], response.json())
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise KnowledgeConflictError(
                "reranker returned no result list",
                error_code="reranker_invalid_result",
            )
        ranked: list[RetrievalCandidate] = []
        used: set[int] = set()
        for rank, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                raise KnowledgeConflictError(
                    "reranker result item is invalid",
                    error_code="reranker_invalid_result",
                )
            index = item.get("index")
            score = item.get("relevance_score", item.get("score"))
            if (
                not isinstance(index, int)
                or index in used
                or not 0 <= index < len(request.candidates)
            ):
                raise KnowledgeConflictError(
                    "reranker returned an invalid candidate index",
                    error_code="reranker_invalid_result",
                )
            if not isinstance(score, int | float):
                raise KnowledgeConflictError(
                    "reranker returned an invalid score",
                    error_code="reranker_invalid_result",
                )
            used.add(index)
            candidate = request.candidates[index]
            ranked.append(
                candidate.model_copy(
                    update={
                        "score": candidate.score.model_copy(
                            update={
                                "final_score": float(score),
                                "rerank_score": float(score),
                                "rerank_rank": rank,
                            }
                        )
                    }
                )
            )
        if len(ranked) != len(request.candidates):
            raise KnowledgeConflictError(
                "reranker returned a partial result",
                error_code="reranker_partial_result",
            )
        return tuple(ranked)


class UnconfiguredReranker:
    """Explicitly unavailable default used when no BGE endpoint is configured."""

    def __init__(self, *, model_id: str) -> None:
        self.model_id = model_id

    async def rerank(
        self,
        context: AuthorizationContext,
        request: RerankRequest,
    ) -> tuple[RetrievalCandidate, ...]:
        del context, request
        raise AppError(
            "reranker endpoint is not configured",
            error_code="reranker_unconfigured",
            status_code=503,
        )


def build_reranker(
    settings: ModelSettings,
) -> BgeRerankerAdapter | UnconfiguredReranker:
    """Build a BGE-compatible adapter only when its endpoint is configured."""
    if settings.reranker_base_url is None:
        return UnconfiguredReranker(model_id=settings.reranker_model)
    credential = (
        settings.reranker_api_key.get_secret_value()
        if settings.reranker_api_key is not None
        else None
    )
    return BgeRerankerAdapter(
        endpoint=settings.reranker_base_url,
        model_id=settings.reranker_model,
        api_key=credential,
        timeout_seconds=settings.request_timeout_seconds,
    )
