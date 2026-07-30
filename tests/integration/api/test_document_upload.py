"""Document upload API persists an idempotent job and publishes after commit."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.api import create_app
from ragflow_agent.config import AppSettings, DatabaseSettings, IngestionSettings
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeService
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.application.upload import UploadService
from ragflow_agent.knowledge.runtime import MinimumRagRuntime
from tests.fakes.knowledge import (
    FixedClock,
    MemoryIngestionQueue,
    MemoryKnowledgeStore,
    MemoryKnowledgeTrace,
    MemoryKnowledgeUnitOfWorkFactory,
    MemoryObjectStorage,
    SequenceIdGenerator,
)

NOW = datetime(2026, 7, 30, tzinfo=UTC)


class UploadRuntime:
    """Only the runtime surface exercised by upload routes."""

    def __init__(
        self,
        *,
        knowledge_service: KnowledgeService,
        upload_service: UploadService,
    ) -> None:
        self.engine = cast(AsyncEngine, object())
        self.knowledge_service = knowledge_service
        self.upload_service = upload_service
        self.opened = False
        self.fixed_rag_service = cast(object, None)

    async def open(self) -> None:
        self.opened = True

    async def close(self) -> None:
        self.opened = False


async def _ready(engine: AsyncEngine) -> bool:
    del engine
    return True


@pytest.fixture
def upload_client() -> Iterator[tuple[TestClient, MemoryIngestionQueue]]:
    store = MemoryKnowledgeStore()
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    ids = SequenceIdGenerator(["kb-a", "doc-a", "version-a"])
    clock = FixedClock(NOW)
    queue = MemoryIngestionQueue()
    knowledge = KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=DefaultPermissionChecker(),
        id_generator=ids,
        clock=clock,
        trace=MemoryKnowledgeTrace(),
    )
    runtime = UploadRuntime(
        knowledge_service=knowledge,
        upload_service=UploadService(
            knowledge_service=knowledge,
            unit_of_work_factory=factory,
            storage=MemoryObjectStorage(),
            queue=queue,
            id_generator=ids,
            clock=clock,
            max_upload_bytes=1024,
        ),
    )
    settings = AppSettings(
        database=DatabaseSettings(
            url=SecretStr("postgresql+psycopg://test:test@localhost/test")
        ),
        ingestion=IngestionSettings(
            max_upload_bytes=1024,
            chunk_max_tokens=32,
            chunk_overlap_tokens=4,
        ),
    )
    app = create_app(
        settings,
        readiness_probe=_ready,
        minimum_rag_runtime=cast(MinimumRagRuntime, runtime),
    )
    with TestClient(app) as client:
        yield client, queue


def test_upload_is_async_idempotent_and_tenant_scoped(
    upload_client: tuple[TestClient, MemoryIngestionQueue],
) -> None:
    client, queue = upload_client
    headers = {
        "x-tenant-id": "tenant-a",
        "x-actor-id": "owner-a",
    }
    created = client.post(
        "/v1/knowledge-bases",
        headers=headers,
        json={"name": "Maintenance", "visibility": "tenant"},
    )
    assert created.status_code == 201

    first = client.post(
        "/v1/knowledge-bases/kb-a/documents",
        headers={**headers, "Idempotency-Key": "upload-1"},
        files={"file": ("manual.md", b"# Reset\n\nInspect relay.", "text/markdown")},
    )
    duplicate = client.post(
        "/v1/knowledge-bases/kb-a/documents",
        headers={**headers, "Idempotency-Key": "upload-1"},
        files={"file": ("manual.md", b"# Reset\n\nInspect relay.", "text/markdown")},
    )

    assert first.status_code == 202
    assert first.json()["status"] == "pending"
    assert first.json()["duplicate"] is False
    assert duplicate.status_code == 202
    assert duplicate.json()["job_id"] == first.json()["job_id"]
    assert duplicate.json()["duplicate"] is True
    assert len(queue.envelopes) == 2
    assert all(envelope.tenant_id == "tenant-a" for envelope in queue.envelopes)


def test_upload_rejects_missing_identity(
    upload_client: tuple[TestClient, MemoryIngestionQueue],
) -> None:
    client, _ = upload_client

    response = client.post(
        "/v1/knowledge-bases/kb-a/documents",
        headers={"Idempotency-Key": "upload-1"},
        files={"file": ("manual.md", b"content", "text/markdown")},
    )

    assert response.status_code == 401
