"""Real PostgreSQL verification for tenant-scoped knowledge snapshots."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import SecretStr

from ragflow_agent.config import DatabaseSettings
from ragflow_agent.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from ragflow_agent.knowledge.domain.authorization import Visibility
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.infrastructure.database import (
    SqlAlchemyKnowledgeUnitOfWorkFactory,
)


def _database_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_DATABASE_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_DATABASE_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_knowledge_repository_round_trip_is_tenant_scoped() -> None:
    engine = create_database_engine(DatabaseSettings(url=SecretStr(_database_url())))
    factory = SqlAlchemyKnowledgeUnitOfWorkFactory(create_session_factory(engine))
    resource_id = f"kb-{uuid4().hex}"
    now = datetime.now(UTC)
    knowledge_base = KnowledgeBase(
        id=resource_id,
        tenant_id="tenant-repository-a",
        owner_id="owner-a",
        name="Repository integration",
        visibility=Visibility.PRIVATE,
        created_at=now,
        updated_at=now,
    )
    try:
        async with factory() as unit_of_work:
            await unit_of_work.knowledge_bases.add(
                tenant_id=knowledge_base.tenant_id,
                entity=knowledge_base,
            )
            await unit_of_work.commit()

        async with factory() as unit_of_work:
            loaded = await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-repository-a",
                resource_id=resource_id,
            )
            hidden = await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-repository-b",
                resource_id=resource_id,
            )

        assert loaded == knowledge_base
        assert hidden is None
    finally:
        await engine.dispose()
