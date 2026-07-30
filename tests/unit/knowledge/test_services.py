"""KnowledgeService and shared KnowledgeQueryService boundary tests."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.knowledge_service import (
    CreateKnowledgeBaseCommand,
    KnowledgeQueryService,
    KnowledgeService,
    RegisterDocumentCommand,
)
from ragflow_agent.knowledge.application.permission_service import (
    DefaultPermissionChecker,
)
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.retrieval import (
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
)
from tests.fakes.knowledge import (
    FixedClock,
    FixtureRetriever,
    MemoryKnowledgeTrace,
    MemoryKnowledgeUnitOfWorkFactory,
    SequenceIdGenerator,
)

NOW = datetime(2026, 7, 30, 8, 0, tzinfo=UTC)
OWNER = AuthorizationContext(
    tenant_id="tenant-a",
    actor_id="owner-a",
    request_id="request-1",
)


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
                    elapsed_ms=1,
                    candidate_count=0,
                ),
            ),
        ),
        empty_reason=RetrievalEmptyReason.NO_MATCH,
    )


def _service(
    factory: MemoryKnowledgeUnitOfWorkFactory,
    *,
    identifiers: list[str],
    trace: MemoryKnowledgeTrace | None = None,
) -> KnowledgeService:
    return KnowledgeService(
        unit_of_work_factory=factory,
        permission_checker=DefaultPermissionChecker(),
        id_generator=SequenceIdGenerator(identifiers),
        clock=FixedClock(NOW),
        trace=trace or MemoryKnowledgeTrace(),
    )


@pytest.mark.asyncio
async def test_create_knowledge_base_uses_context_tenant_actor_and_trace() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    trace = MemoryKnowledgeTrace()
    service = _service(factory, identifiers=["kb-1"], trace=trace)

    created = await service.create_knowledge_base(
        CreateKnowledgeBaseCommand(
            context=OWNER,
            name="Operations",
            visibility=Visibility.TENANT,
        )
    )

    assert created.tenant_id == OWNER.tenant_id
    assert created.owner_id == OWNER.actor_id
    assert trace.events[0].resource_id == "kb-1"
    async with factory() as unit_of_work:
        assert (
            await unit_of_work.knowledge_bases.get(
                tenant_id="tenant-a",
                resource_id="kb-1",
            )
            == created
        )


@pytest.mark.asyncio
async def test_get_hides_cross_tenant_resource_and_enforces_private_visibility() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    service = _service(factory, identifiers=[])
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=KnowledgeBase(
                id="kb-1",
                tenant_id="tenant-a",
                owner_id="owner-a",
                name="Private",
                created_at=NOW,
                updated_at=NOW,
            ),
        )
        await unit_of_work.commit()

    with pytest.raises(KnowledgeNotFoundError):
        await service.get_knowledge_base(
            AuthorizationContext(
                tenant_id="tenant-b",
                actor_id="owner-a",
                request_id="request-2",
            ),
            "kb-1",
        )
    with pytest.raises(KnowledgeAuthorizationError):
        await service.get_knowledge_base(
            AuthorizationContext(
                tenant_id="tenant-a",
                actor_id="member-a",
                request_id="request-3",
            ),
            "kb-1",
        )


@pytest.mark.asyncio
async def test_register_document_checks_knowledge_base_write_before_commit() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    service = _service(factory, identifiers=["document-1", "version-1"])
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=KnowledgeBase(
                id="kb-1",
                tenant_id="tenant-a",
                owner_id="owner-a",
                name="Operations",
                visibility=Visibility.TENANT,
                created_at=NOW,
                updated_at=NOW,
            ),
        )
        await unit_of_work.commit()

    with pytest.raises(KnowledgeAuthorizationError):
        await service.register_document(
            RegisterDocumentCommand(
                context=AuthorizationContext(
                    tenant_id="tenant-a",
                    actor_id="member-a",
                    request_id="request-2",
                ),
                knowledge_base_id="kb-1",
                name="manual.pdf",
                object_key="tenants/tenant-a/kb-1/source",
                media_type="application/pdf",
                content_hash="abc123",
                size_bytes=10,
            )
        )
    assert factory.store.documents == {}


@pytest.mark.asyncio
async def test_register_document_atomically_creates_document_and_version() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    trace = MemoryKnowledgeTrace()
    service = _service(
        factory,
        identifiers=["kb-1", "document-1", "version-1"],
        trace=trace,
    )
    await service.create_knowledge_base(
        CreateKnowledgeBaseCommand(context=OWNER, name="Operations")
    )

    registered = await service.register_document(
        RegisterDocumentCommand(
            context=OWNER,
            knowledge_base_id="kb-1",
            name="manual.pdf",
            object_key="tenants/tenant-a/kb-1/document-1/source",
            media_type="application/pdf",
            content_hash="abc123",
            size_bytes=10,
        )
    )

    assert registered.document.tenant_id == "tenant-a"
    assert registered.version.document_id == registered.document.id
    assert registered.document.current_version_id is None
    assert trace.events[-1].action == "registered"


@pytest.mark.asyncio
async def test_query_service_authorizes_before_calling_retriever() -> None:
    factory = MemoryKnowledgeUnitOfWorkFactory()
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="breaker",
        knowledge_base_ids=("kb-1",),
        trace_id="trace-1",
    )
    retriever = FixtureRetriever(_empty_result(query))
    service = KnowledgeQueryService(
        unit_of_work_factory=factory,
        permission_checker=DefaultPermissionChecker(),
        retriever=retriever,
    )
    async with factory() as unit_of_work:
        await unit_of_work.knowledge_bases.add(
            tenant_id="tenant-a",
            entity=KnowledgeBase(
                id="kb-1",
                tenant_id="tenant-a",
                owner_id="owner-a",
                name="Operations",
                visibility=Visibility.TENANT,
                created_at=NOW,
                updated_at=NOW,
            ),
        )
        await unit_of_work.commit()

    result = await service.retrieve(
        AuthorizationContext(
            tenant_id="tenant-a",
            actor_id="member-a",
            request_id="request-2",
        ),
        query,
    )
    assert result.empty_reason is RetrievalEmptyReason.NO_MATCH
    assert retriever.calls == 1

    with pytest.raises(KnowledgeAuthorizationError):
        await service.retrieve(
            AuthorizationContext(
                tenant_id="tenant-b",
                actor_id="member-a",
                request_id="request-3",
            ),
            query,
        )
    assert retriever.calls == 1
