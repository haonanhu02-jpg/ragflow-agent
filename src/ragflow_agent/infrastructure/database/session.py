"""Async SQLAlchemy engine, session factory, and transaction lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ragflow_agent.config import DatabaseSettings

type AsyncSessionFactory = async_sessionmaker[AsyncSession]


def create_database_engine(settings: DatabaseSettings) -> AsyncEngine:
    """Create an async engine without opening a connection at import time."""
    return create_async_engine(
        settings.url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout_seconds,
    )


def create_session_factory(engine: AsyncEngine) -> AsyncSessionFactory:
    """Create the shared async-session factory."""
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def session_scope(factory: AsyncSessionFactory) -> AsyncIterator[AsyncSession]:
    """Commit on success, roll back on failure, and always close the session."""
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
