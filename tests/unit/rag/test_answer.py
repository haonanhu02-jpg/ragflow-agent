"""Fixed RAG prompt and no-evidence behavior."""

from datetime import UTC, datetime

import pytest

from ragflow_agent.knowledge.application.fixed_rag import (
    FIXED_RAG_PROMPT_VERSION,
    NO_EVIDENCE_ANSWER,
    FixedRagRequest,
    FixedRagService,
)
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from ragflow_agent.knowledge.application.permission_service import DefaultPermissionChecker
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext, Visibility
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
    FixtureRetriever,
    MemoryKnowledgeStore,
    MemoryKnowledgeUnitOfWorkFactory,
)
from tests.fakes.minimum_rag import StubChatProvider

NOW = datetime(2026, 7, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_no_evidence_skips_model_and_returns_stable_answer() -> None:
    context = AuthorizationContext(
        tenant_id="tenant-a",
        actor_id="owner-a",
        request_id="trace-a",
    )
    query = RetrievalQuery(
        tenant_id="tenant-a",
        text="unknown failure",
        knowledge_base_ids=("kb-a",),
        top_k=20,
        top_n=5,
        trace_id="trace-a",
    )
    retrieval = RetrievalResult(
        query=query,
        candidates=(),
        trace=RetrievalTrace(
            trace_id="trace-a",
            tenant_id="tenant-a",
            original_query="unknown failure",
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
            question="unknown failure",
            knowledge_base_ids=("kb-a",),
        )
    )

    assert answer.answer == NO_EVIDENCE_ANSWER
    assert answer.citations == ()
    assert answer.prompt_version == FIXED_RAG_PROMPT_VERSION
    assert chat.requests == []
