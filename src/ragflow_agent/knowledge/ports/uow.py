"""Knowledge application transaction boundary."""

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from ragflow_agent.knowledge.ports.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    IngestionJobRepository,
    IngestionTaskRepository,
    KnowledgeBaseRepository,
)


@runtime_checkable
class KnowledgeUnitOfWork(Protocol):
    """Own all repositories used by one atomic knowledge application operation."""

    @property
    def knowledge_bases(self) -> KnowledgeBaseRepository: ...

    @property
    def documents(self) -> DocumentRepository: ...

    @property
    def document_versions(self) -> DocumentVersionRepository: ...

    @property
    def ingestion_jobs(self) -> IngestionJobRepository: ...

    @property
    def ingestion_tasks(self) -> IngestionTaskRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


@runtime_checkable
class KnowledgeUnitOfWorkFactory(Protocol):
    """Create an isolated UnitOfWork per application command or query."""

    def __call__(self) -> KnowledgeUnitOfWork: ...
