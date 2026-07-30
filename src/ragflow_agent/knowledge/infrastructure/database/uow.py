"""Knowledge UnitOfWork backed by one SQLAlchemy AsyncSession."""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from ragflow_agent.infrastructure.database import AsyncSessionFactory
from ragflow_agent.knowledge.infrastructure.database.repositories import (
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentVersionRepository,
    SqlAlchemyIngestionJobRepository,
    SqlAlchemyIngestionTaskRepository,
    SqlAlchemyKnowledgeBaseRepository,
)


class SqlAlchemyKnowledgeUnitOfWork:
    """Bind all knowledge repositories to one explicit transaction."""

    def __init__(self, factory: AsyncSessionFactory) -> None:
        self._factory = factory
        self._session: AsyncSession | None = None
        self._committed = False

    async def __aenter__(self) -> Self:
        self._session = self._factory()
        self._committed = False
        self.knowledge_bases = SqlAlchemyKnowledgeBaseRepository(self._session)
        self.documents = SqlAlchemyDocumentRepository(self._session)
        self.document_versions = SqlAlchemyDocumentVersionRepository(self._session)
        self.ingestion_jobs = SqlAlchemyIngestionJobRepository(self._session)
        self.ingestion_tasks = SqlAlchemyIngestionTaskRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_value, traceback
        if self._session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                await self._session.rollback()
        finally:
            await self._session.close()
            self._session = None

    @property
    def _active_session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("knowledge unit of work has not been entered")
        return self._session

    async def commit(self) -> None:
        await self._active_session.commit()
        self._committed = True

    async def rollback(self) -> None:
        await self._active_session.rollback()
        self._committed = False


class SqlAlchemyKnowledgeUnitOfWorkFactory:
    """Create an isolated SQLAlchemy knowledge transaction."""

    def __init__(self, factory: AsyncSessionFactory) -> None:
        self._factory = factory

    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork:
        return SqlAlchemyKnowledgeUnitOfWork(self._factory)
