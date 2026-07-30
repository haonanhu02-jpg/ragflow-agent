"""Cross-port negative tenant, owner, and visibility contract tests."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from hashlib import sha256
from inspect import signature
from typing import Any

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.application.permission_service import (
    DefaultPermissionChecker,
)
from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    PermissionAction,
    ResourceAuthorization,
    Visibility,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.domain.ingestion import (
    IngestionEnvelope,
    IngestionStage,
    IngestionTask,
)
from ragflow_agent.knowledge.domain.retrieval import (
    EmbeddingMetadata,
    IndexVersion,
    IndexVersionStatus,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
)
from ragflow_agent.knowledge.ports.repositories import (
    DocumentRepository,
    DocumentVersionRepository,
    IngestionJobRepository,
    IngestionTaskRepository,
    KnowledgeBaseRepository,
)
from ragflow_agent.knowledge.ports.storage import StorageWriteRequest
from ragflow_agent.knowledge.ports.trace import KnowledgeTraceEvent, KnowledgeTraceKind
from tests.fakes.knowledge import (
    FixtureRetriever,
    MemoryIngestionQueue,
    MemoryObjectStorage,
    MemorySearchIndex,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
TENANT_A = AuthorizationContext(
    tenant_id="tenant-a",
    actor_id="owner-a",
    request_id="request-a",
)
TENANT_B = AuthorizationContext(
    tenant_id="tenant-b",
    actor_id="owner-a",
    request_id="request-b",
)


async def _content(payload: bytes) -> AsyncIterator[bytes]:
    yield payload


def _empty_result(query: RetrievalQuery) -> RetrievalResult:
    return RetrievalResult(
        query=query,
        candidates=(),
        trace=RetrievalTrace(
            trace_id=query.trace_id,
            tenant_id=query.tenant_id,
            original_query=query.text,
            authorization_applied=True,
            events=(
                RetrievalTraceEvent(
                    sequence=0,
                    stage=RetrievalStage.AUTHORIZATION,
                    elapsed_ms=0,
                    candidate_count=0,
                ),
            ),
        ),
        empty_reason=RetrievalEmptyReason.NO_MATCH,
    )


@pytest.mark.parametrize(
    ("visibility", "action", "allowed"),
    [
        (Visibility.PRIVATE, PermissionAction.READ, False),
        (Visibility.PRIVATE, PermissionAction.WRITE, False),
        (Visibility.TENANT, PermissionAction.READ, True),
        (Visibility.TENANT, PermissionAction.WRITE, False),
        (Visibility.TENANT, PermissionAction.DELETE, False),
        (Visibility.TENANT, PermissionAction.MANAGE, False),
    ],
)
def test_non_owner_permission_matrix(
    visibility: Visibility,
    action: PermissionAction,
    allowed: bool,
) -> None:
    decision = DefaultPermissionChecker().check(
        AuthorizationContext(
            tenant_id="tenant-a",
            actor_id="member-a",
            request_id="request-a",
        ),
        ResourceAuthorization(
            tenant_id="tenant-a",
            owner_id="owner-a",
            visibility=visibility,
        ),
        action,
    )

    assert decision.allowed is allowed


@pytest.mark.asyncio
async def test_object_storage_denies_cross_tenant_write_and_read() -> None:
    adapter = MemoryObjectStorage()
    payload = b"secret document"
    request = StorageWriteRequest(
        tenant_id="tenant-a",
        object_key="tenants/tenant-a/kb-1/source",
        media_type="text/plain",
        size_bytes=len(payload),
        checksum_sha256=sha256(payload).hexdigest(),
        trace_id="trace-a",
    )
    with pytest.raises(KnowledgeAuthorizationError):
        await adapter.put(TENANT_B, request, _content(payload))

    stored = await adapter.put(TENANT_A, request, _content(payload))
    with pytest.raises(KnowledgeAuthorizationError):
        _ = [chunk async for chunk in adapter.read(TENANT_B, stored)]


def test_object_key_cannot_escape_tenant_namespace() -> None:
    with pytest.raises(ValidationError):
        StorageWriteRequest(
            tenant_id="tenant-a",
            object_key="tenants/tenant-b/kb-1/source",
            media_type="text/plain",
            size_bytes=0,
            checksum_sha256=sha256(b"").hexdigest(),
            trace_id="trace-a",
        )


@pytest.mark.asyncio
async def test_queue_search_and_retriever_deny_cross_tenant_context() -> None:
    task = IngestionTask(
        id="task-1",
        tenant_id="tenant-a",
        job_id="job-1",
        document_version_id="version-1",
        stage=IngestionStage.PARSE,
        idempotency_key="job-1:parse",
        trace_id="trace-a",
        created_at=NOW,
        updated_at=NOW,
    )
    envelope = IngestionEnvelope.from_task(
        task,
        message_id="message-1",
        created_at=NOW,
    )
    with pytest.raises(KnowledgeAuthorizationError):
        await MemoryIngestionQueue().publish(TENANT_B, envelope)

    version = IndexVersion(
        id="index-v1",
        tenant_id="tenant-a",
        knowledge_base_id="kb-1",
        embedding=EmbeddingMetadata(model_id="fixture", dimensions=3, normalized=False),
        status=IndexVersionStatus.BUILDING,
        created_at=NOW,
    )
    with pytest.raises(KnowledgeAuthorizationError):
        await MemorySearchIndex().activate(TENANT_B, version)

    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="breaker",
        knowledge_base_ids=("kb-1",),
        trace_id="trace-a",
    )
    with pytest.raises(KnowledgeAuthorizationError):
        await FixtureRetriever(_empty_result(query)).retrieve(TENANT_B, query)


@pytest.mark.parametrize(
    "repository",
    [
        KnowledgeBaseRepository,
        DocumentRepository,
        DocumentVersionRepository,
        IngestionJobRepository,
        IngestionTaskRepository,
    ],
)
def test_every_repository_get_requires_explicit_tenant(repository: Any) -> None:
    parameters = signature(repository.get).parameters

    assert "tenant_id" in parameters
    assert "resource_id" in parameters
    assert not hasattr(repository, "get_by_id")


def test_trace_event_requires_tenant_actor_request_and_trace_identity() -> None:
    with pytest.raises(ValidationError):
        KnowledgeTraceEvent(
            trace_id="trace-a",
            request_id="",
            tenant_id="tenant-a",
            actor_id="owner-a",
            kind=KnowledgeTraceKind.AUTHORIZATION,
            action="checked",
            resource_type="knowledge_base",
            resource_id="kb-1",
            occurred_at=NOW,
        )
