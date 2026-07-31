"""Isolated read-only SQL execution adapter for explicitly configured data sources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


class SqlAlchemyReadOnlyExecutor:
    """Execute already-validated SQL with transaction-level read-only enforcement."""

    def __init__(self, database_url: str) -> None:
        if not database_url:
            raise ValueError("read-only SQL database URL must not be blank")
        self._engine: AsyncEngine = create_async_engine(database_url, pool_pre_ping=True)

    async def execute(
        self,
        *,
        statement: str,
        parameters: Mapping[str, object],
        timeout_seconds: float,
        max_rows: int,
    ) -> Sequence[Mapping[str, object]]:
        timeout_ms = max(1, int(timeout_seconds * 1_000))
        async with self._engine.begin() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            await connection.execute(text(f"SET LOCAL statement_timeout = {timeout_ms:d}"))
            result = await connection.execute(text(statement), dict(parameters))
            return tuple(dict(row) for row in result.mappings().fetchmany(max_rows))

    async def close(self) -> None:
        await self._engine.dispose()
