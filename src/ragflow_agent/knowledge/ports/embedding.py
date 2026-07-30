"""Provider-neutral embedding request, result, and port."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import Field, model_validator

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class EmbeddingInput(KnowledgeModel):
    """Stable correlation identity and text for one embedding."""

    id: NonEmptyStr
    text: NonEmptyStr


class EmbeddingRequest(KnowledgeModel):
    """Batch embedding request scoped to one tenant and model."""

    tenant_id: NonEmptyStr
    model_id: NonEmptyStr
    inputs: tuple[EmbeddingInput, ...] = Field(min_length=1)
    trace_id: NonEmptyStr


class EmbeddingVector(KnowledgeModel):
    """One output vector correlated by input ID."""

    input_id: NonEmptyStr
    values: tuple[float, ...] = Field(min_length=1)


class EmbeddingResult(KnowledgeModel):
    """Batch result with explicit dimensions and normalization semantics."""

    model_id: NonEmptyStr
    dimensions: int = Field(ge=1)
    normalized: bool
    vectors: tuple[EmbeddingVector, ...]

    @model_validator(mode="after")
    def vectors_match_dimensions_and_inputs(self) -> EmbeddingResult:
        identifiers = [vector.input_id for vector in self.vectors]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("embedding output identifiers must be unique")
        if any(len(vector.values) != self.dimensions for vector in self.vectors):
            raise ValueError("embedding vector dimensions do not match result metadata")
        return self


@runtime_checkable
class EmbeddingPort(Protocol):
    """Generate embeddings without exposing a provider SDK."""

    async def embed(
        self,
        context: AuthorizationContext,
        request: EmbeddingRequest,
    ) -> EmbeddingResult: ...
