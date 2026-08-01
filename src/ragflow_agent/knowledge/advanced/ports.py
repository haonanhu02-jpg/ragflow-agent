"""Provider, persistence, and derived-index ports for Phase 09."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.advanced.domain import AdvancedArtifact, AdvancedBuild
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import RetrievalCandidate, RetrievalQuery


@runtime_checkable
class StructuredGenerationPort(Protocol):
    async def generate(self, *, task: str, text: str, limit: int) -> tuple[str, ...]: ...


@runtime_checkable
class VisionDescriptionPort(Protocol):
    async def describe(self, *, media_type: str, content: bytes) -> str: ...


@runtime_checkable
class SpeechRecognitionPort(Protocol):
    async def transcribe(self, *, media_type: str, content: bytes) -> tuple[str, ...]: ...


@runtime_checkable
class AdvancedArtifactRepository(Protocol):
    async def put(self, artifact: AdvancedArtifact) -> None: ...

    async def list_for_version(
        self,
        *,
        tenant_id: str,
        document_version_id: str,
    ) -> tuple[AdvancedArtifact, ...]: ...

    async def delete_version(self, *, tenant_id: str, document_version_id: str) -> int: ...


@runtime_checkable
class AdvancedBuildRepository(Protocol):
    async def get(self, *, tenant_id: str, build_id: str) -> AdvancedBuild | None: ...

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> AdvancedBuild | None: ...

    async def save(self, build: AdvancedBuild) -> None: ...


@runtime_checkable
class AdvancedCandidatePort(Protocol):
    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> tuple[RetrievalCandidate, ...]: ...
