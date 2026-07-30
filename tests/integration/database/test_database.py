"""Integration tests for PostgreSQL lifecycle and transaction rollback."""

import os

import pytest
from pydantic import SecretStr
from sqlalchemy import text

from ragflow_agent.config import DatabaseSettings
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
    session_scope,
)


def database_url() -> str:
    """Return the explicitly provisioned integration database URL."""
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_engine_connects_and_disposes() -> None:
    engine = create_database_engine(DatabaseSettings(url=SecretStr(database_url())))
    try:
        async with engine.connect() as connection:
            assert await connection.scalar(text("select 1")) == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_session_scope_rolls_back_on_error() -> None:
    engine = create_database_engine(DatabaseSettings(url=SecretStr(database_url())))
    factory = create_session_factory(engine)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("drop table if exists phase01_rollback_probe"))

        with pytest.raises(RuntimeError, match="force rollback"):
            async with session_scope(factory) as session:
                await session.execute(text("create table phase01_rollback_probe (id integer)"))
                raise RuntimeError("force rollback")

        async with engine.connect() as connection:
            relation = await connection.scalar(
                text("select to_regclass('public.phase01_rollback_probe')")
            )
        assert relation is None
    finally:
        await engine.dispose()
