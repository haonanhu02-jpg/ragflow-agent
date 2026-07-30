"""Provider-neutral contract for the LangChain embedding adapter."""

import pytest
from langchain_core.embeddings import Embeddings

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.infrastructure.models import LangChainEmbeddingAdapter
from ragflow_agent.knowledge.ports.embedding import EmbeddingInput, EmbeddingRequest


class FixtureEmbeddings(Embeddings):
    """LangChain test double with the same async surface as a real provider."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), 1.0, 0.0] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text)), 1.0, 0.0]


@pytest.mark.asyncio
async def test_adapter_preserves_input_identity_and_model_metadata() -> None:
    adapter = LangChainEmbeddingAdapter(
        FixtureEmbeddings(),
        model_id="BAAI/bge-m3",
        expected_dimensions=3,
    )
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-a",
    )

    result = await adapter.embed(
        context,
        EmbeddingRequest(
            tenant_id="tenant-a",
            model_id="BAAI/bge-m3",
            inputs=(
                EmbeddingInput(id="chunk-1", text="reset"),
                EmbeddingInput(id="chunk-2", text="inspect"),
            ),
            trace_id="trace-a",
        ),
    )

    assert result.model_id == "BAAI/bge-m3"
    assert result.dimensions == 3
    assert [vector.input_id for vector in result.vectors] == ["chunk-1", "chunk-2"]


@pytest.mark.asyncio
async def test_adapter_rejects_model_and_dimension_drift() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-a",
    )
    adapter = LangChainEmbeddingAdapter(
        FixtureEmbeddings(),
        model_id="BAAI/bge-m3",
        expected_dimensions=2,
    )
    request = EmbeddingRequest(
        tenant_id="tenant-a",
        model_id="BAAI/bge-m3",
        inputs=(EmbeddingInput(id="chunk-1", text="reset"),),
        trace_id="trace-a",
    )

    with pytest.raises(KnowledgeConflictError) as mismatch:
        await adapter.embed(context, request)

    assert mismatch.value.error_code == "embedding_dimension_mismatch"
    assert mismatch.value.details["inputs"] == [
        {"input_id": "chunk-1", "actual_dimensions": 3}
    ]
