"""CAS and authoritative retrieval validation reject stale lifecycle work."""

import pytest
from tests.fakes.knowledge import (
    FixtureRetriever,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
)
from tests.fakes.lifecycle import NOW, seed_active_document

from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.errors import KnowledgeConflictError
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    RetrievalCandidate,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalTrace,
    ScoreBreakdown,
)


@pytest.mark.asyncio
async def test_compare_and_set_rejects_stale_document_revision() -> None:
    store = MemoryKnowledgeStore()
    document, _version = seed_active_document(store)
    factory = MemoryKnowledgeUnitOfWorkFactory(store)
    async with factory() as unit_of_work:
        with pytest.raises(KnowledgeConflictError, match="revision"):
            await unit_of_work.documents.save_if_revision(
                tenant_id="tenant-a",
                entity=document.model_copy(update={"revision": 2}),
                expected_revision=1,
            )


@pytest.mark.asyncio
async def test_stale_search_candidate_is_removed_by_authoritative_state() -> None:
    store = MemoryKnowledgeStore()
    store.knowledge_bases["kb-a"] = KnowledgeBase(
        id="kb-a",
        tenant_id="tenant-a",
        owner_id="owner-a",
        name="Operations",
        visibility=Visibility.TENANT,
        created_at=NOW,
        updated_at=NOW,
    )
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="reset",
        knowledge_base_ids=("kb-a",),
        trace_id="trace-a",
    )
    citation = Citation(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="deleted-doc",
        document_version_id="old-version",
        chunk_id="chunk-a",
        quote="stale",
    )
    candidate = RetrievalCandidate(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="deleted-doc",
        document_version_id="old-version",
        chunk_id="chunk-a",
        content="stale",
        score=ScoreBreakdown(final_score=1),
        citation=citation,
    )
    result = RetrievalResult(
        query=query,
        candidates=(candidate,),
        trace=RetrievalTrace(
            trace_id="trace-a",
            tenant_id="tenant-a",
            original_query="reset",
            authorization_applied=True,
            events=(),
        ),
    )
    service = KnowledgeQueryService(
        unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
        permission_checker=DefaultPermissionChecker(),
        retriever=FixtureRetriever(result),
    )
    filtered = await service.retrieve(
        AuthorizationContext(tenant_id="tenant-a", actor_id="owner-a", request_id="request-a"),
        query,
    )
    assert filtered.candidates == ()
    assert filtered.empty_reason is RetrievalEmptyReason.NO_EVIDENCE
