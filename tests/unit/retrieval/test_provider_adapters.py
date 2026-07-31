"""BGE HTTP and structured query Provider adapter tests without real models."""

import json

import httpx
import pytest
from tests.fakes.retrieval import retrieval_candidate

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import RetrievalQuery
from ragflow_agent.knowledge.infrastructure.models import BgeRerankerAdapter
from ragflow_agent.knowledge.ports.search import RerankRequest


@pytest.mark.asyncio
async def test_bge_adapter_maps_wire_scores_without_supplier_types() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "BAAI/bge-reranker-v2-m3"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.2},
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = BgeRerankerAdapter(
        endpoint="https://reranker.invalid/rerank",
        model_id="BAAI/bge-reranker-v2-m3",
        api_key=None,
        timeout_seconds=1,
        client=client,
    )
    context = AuthorizationContext(tenant_id="tenant-a", actor_id="owner-a", request_id="request-a")
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="reset",
        knowledge_base_ids=("kb-a",),
        trace_id="trace-a",
    )
    candidates = (
        retrieval_candidate("a", full_text_score=2),
        retrieval_candidate("b", vector_score=0.8),
    )
    try:
        result = await adapter.rerank(
            context,
            RerankRequest(query=query, candidates=candidates),
        )
    finally:
        await client.aclose()

    assert [item.chunk_id for item in result] == ["b", "a"]
    assert result[0].score.rerank_score == 0.9
    assert result[0].score.rerank_rank == 1
