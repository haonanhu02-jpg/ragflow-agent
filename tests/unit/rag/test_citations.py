"""Citation provenance stays version-bound through answer generation."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest, FixedRagService
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
from ragflow_agent.knowledge.domain.knowledge_base import KnowledgeBase
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStage,
    RetrievalTrace,
    RetrievalTraceEvent,
    ScoreBreakdown,
)
from tests.fakes.knowledge import (
    FixtureRetriever,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
)
from tests.fakes.minimum_rag import StubChatProvider

NOW = datetime(2026, 7, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_selected_citation_and_source_version_are_returned_unchanged() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-a",
    )
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="reset",
        knowledge_base_ids=("kb-a",),
        top_k=20,
        top_n=5,
        trace_id="trace-a",
    )
    citation = Citation(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        chunk_id="chunk-a",
        quote="Reset controller.",
        page_number=2,
        source_uri="documents/doc-a/versions/version-a",
    )
    candidate = RetrievalCandidate(
        tenant_id="tenant-a",
        knowledge_base_id="kb-a",
        document_id="doc-a",
        document_version_id="version-a",
        chunk_id="chunk-a",
        content="Reset controller.",
        score=ScoreBreakdown(final_score=1),
        citation=citation,
    )
    retrieval = RetrievalResult(
        query=query,
        candidates=(candidate,),
        trace=RetrievalTrace(
            trace_id="trace-a",
            tenant_id="tenant-a",
            original_query="reset",
            authorization_applied=True,
            events=(
                RetrievalTraceEvent(
                    sequence=0,
                    stage=RetrievalStage.AUTHORIZATION,
                    elapsed_ms=0,
                    candidate_count=1,
                ),
            ),
        ),
    )
    store = MemoryKnowledgeStore()
    store.knowledge_bases["kb-a"] = KnowledgeBase(
        id="kb-a",
        tenant_id="tenant-a",
        owner_id="owner-a",
        name="Maintenance",
        visibility=Visibility.PRIVATE,
        created_at=NOW,
        updated_at=NOW,
    )
    chat = StubChatProvider()
    service = FixedRagService(
        query_service=KnowledgeQueryService(
            unit_of_work_factory=MemoryKnowledgeUnitOfWorkFactory(store),
            permission_checker=DefaultPermissionChecker(),
            retriever=FixtureRetriever(retrieval),
        ),
        chat_provider=chat,
        chat_model_id=chat.model_id,
    )

    answer = await service.answer(
        FixedRagRequest(
            context=context,
            question="reset",
            knowledge_base_ids=("kb-a",),
        )
    )

    assert answer.citations == (citation,)
    assert answer.citations[0].document_version_id == "version-a"
    assert answer.retrieval_trace == retrieval.trace
    assert "[1] Reset controller." in chat.requests[0].user_prompt
