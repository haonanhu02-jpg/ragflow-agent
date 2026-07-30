"""Fixed RAG answer flow shared independently from the Agent runtime."""

from __future__ import annotations

from pydantic import Field

from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    RetrievalCandidate,
    RetrievalQuery,
    RetrievalTrace,
)
from ragflow_agent.knowledge.ports.generation import (
    ChatGenerationRequest,
    ChatProviderPort,
)

FIXED_RAG_PROMPT_VERSION = "fixed-rag-v1"
NO_EVIDENCE_ANSWER = "未检索到可用于回答该问题的授权证据。"


class FixedRagRequest(KnowledgeModel):
    """Tenant-scoped fixed RAG request."""

    context: AuthorizationContext
    question: NonEmptyStr
    knowledge_base_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)
    top_k: int = Field(default=20, ge=1, le=1000)
    top_n: int = Field(default=5, ge=1, le=50)


class FixedRagAnswer(KnowledgeModel):
    """Answer with version-bound citations and retrieval trace."""

    answer: NonEmptyStr
    citations: tuple[Citation, ...]
    retrieval_trace: RetrievalTrace
    prompt_version: NonEmptyStr
    model_id: str | None = None


class FixedRagService:
    """Retrieve, build bounded context, generate, and return validated sources."""

    def __init__(
        self,
        *,
        query_service: KnowledgeQueryService,
        chat_provider: ChatProviderPort,
        chat_model_id: str,
        max_context_characters: int = 12_000,
    ) -> None:
        self._query_service = query_service
        self._chat_provider = chat_provider
        self._chat_model_id = chat_model_id
        self._max_context_characters = max_context_characters

    async def answer(self, request: FixedRagRequest) -> FixedRagAnswer:
        retrieval = await self._query_service.retrieve(
            request.context,
            RetrievalQuery(
                tenant_id=request.context.tenant_id,
                text=request.question,
                knowledge_base_ids=request.knowledge_base_ids,
                top_k=request.top_k,
                top_n=request.top_n,
                trace_id=request.context.request_id,
            ),
        )
        if not retrieval.candidates:
            return FixedRagAnswer(
                answer=NO_EVIDENCE_ANSWER,
                citations=(),
                retrieval_trace=retrieval.trace,
                prompt_version=FIXED_RAG_PROMPT_VERSION,
            )
        selected: list[tuple[RetrievalCandidate, str]] = []
        consumed = 0
        for candidate in retrieval.candidates:
            marker = f"[{len(selected) + 1}] {candidate.content}\n"
            if selected and consumed + len(marker) > self._max_context_characters:
                break
            selected.append((candidate, marker))
            consumed += len(marker)
        context_text = "".join(marker for _, marker in selected)
        generated = await self._chat_provider.generate(
            request.context,
            ChatGenerationRequest(
                model_id=self._chat_model_id,
                system_prompt=(
                    "你是企业知识库问答助手。只能依据提供的证据回答;"
                    "无法从证据确定时必须明确说明。引用证据时使用 [1]、[2] 编号。"
                ),
                user_prompt=f"问题: {request.question}\n\n证据:\n{context_text}",
                trace_id=request.context.request_id,
            ),
        )
        citations = tuple(candidate.citation for candidate, _ in selected)
        return FixedRagAnswer(
            answer=generated.content,
            citations=citations,
            retrieval_trace=retrieval.trace,
            prompt_version=FIXED_RAG_PROMPT_VERSION,
            model_id=generated.model_id,
        )
