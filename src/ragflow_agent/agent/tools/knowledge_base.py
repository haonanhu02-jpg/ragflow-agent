"""LangChain-compatible KnowledgeBaseTool over the one query service."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.agent.application.budgets import BudgetLedger
from ragflow_agent.agent.application.sensitive import redact_secret_like_text
from ragflow_agent.agent.domain.agentic import (
    AgentEvidenceCitation,
    DirectRagAnswer,
    EvidenceItem,
    KnowledgeCitation,
    ToolAuthorizationContext,
    ToolEffect,
    ToolInvocation,
    ToolRegistration,
    ToolRiskLevel,
)
from ragflow_agent.agent.ports.agentic import ModelCallBudgetPort
from ragflow_agent.knowledge.application.fixed_rag import FixedRagRequest, FixedRagService
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import Citation, RetrievalQuery
from ragflow_agent.shared.ports.identity import IdGenerator


class KnowledgeBaseToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: str = Field(min_length=1, max_length=8_000)
    knowledge_base_ids: tuple[str, ...] = Field(min_length=1, max_length=64)
    top_k: int = Field(default=20, ge=1, le=1_000)
    top_n: int = Field(default=5, ge=1, le=50)


class KnowledgeEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    document_id: str
    document_version_id: str
    knowledge_base_id: str
    excerpt: str
    normalized_rank_score: float = Field(ge=0, le=1)
    citation: Citation


class KnowledgeBaseToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence: tuple[KnowledgeEvidence, ...]
    citations: tuple[Citation, ...]
    retrieval_trace_id: str
    empty_reason: str | None = None


class KnowledgeBaseTool:
    """Registered read-only Tool; tenant and actor are injected by the server."""

    def __init__(self, query_service: KnowledgeQueryService, id_generator: IdGenerator) -> None:
        self._query_service = query_service
        self._id_generator = id_generator
        self._registration = ToolRegistration(
            tool_name="knowledge_base",
            version="1",
            description="Retrieve authorized evidence from explicitly scoped knowledge bases.",
            input_schema=KnowledgeBaseToolInput.model_json_schema(),
            output_schema=KnowledgeBaseToolOutput.model_json_schema(),
            effect=ToolEffect.READ_ONLY,
            risk_level=ToolRiskLevel.LOW,
            timeout_seconds=15,
            max_retries=1,
            max_output_bytes=1_000_000,
            idempotent=True,
            requires_hitl=False,
            sensitive_fields=(),
        )

    @property
    def registration(self) -> ToolRegistration:
        return self._registration

    async def invoke(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> object:
        payload = KnowledgeBaseToolInput.model_validate(invocation.arguments)
        knowledge_context = _knowledge_context(context)
        result = await self._query_service.retrieve(
            knowledge_context,
            RetrievalQuery(
                tenant_id=knowledge_context.tenant_id,
                text=payload.query,
                knowledge_base_ids=payload.knowledge_base_ids,
                top_k=payload.top_k,
                top_n=payload.top_n,
                trace_id=self._id_generator.new_id(),
                request_id=knowledge_context.request_id,
            ),
        )
        evidence = tuple(
            KnowledgeEvidence(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                document_version_id=candidate.document_version_id,
                knowledge_base_id=candidate.knowledge_base_id,
                excerpt=candidate.content[:2_000],
                normalized_rank_score=1.0 / float(candidate.score.final_rank or index),
                citation=candidate.citation,
            )
            for index, candidate in enumerate(result.candidates, start=1)
        )
        return KnowledgeBaseToolOutput(
            evidence=evidence,
            citations=tuple(item.citation for item in evidence),
            retrieval_trace_id=result.trace.trace_id,
            empty_reason=result.empty_reason.value if result.empty_reason else None,
        ).model_dump(mode="json")

    def as_langchain_tool(self, context: ToolAuthorizationContext) -> object:
        """Return a context-bound LangChain StructuredTool without exposing tenant input."""
        from langchain_core.tools import StructuredTool

        async def invoke_bound(**arguments: object) -> object:
            invocation = ToolInvocation(
                tool_call_id=self._id_generator.new_id(),
                tool_name=self.registration.tool_name,
                tool_version=self.registration.version,
                arguments=dict(arguments),
            )
            return await self.invoke(invocation, context)

        return StructuredTool.from_function(
            coroutine=invoke_bound,
            name=self.registration.tool_name,
            description=self.registration.description,
            args_schema=KnowledgeBaseToolInput,
        )


class AgentKnowledgeGateway:
    """Adapter sharing the fixed-RAG and KnowledgeQueryService core."""

    def __init__(
        self,
        *,
        knowledge_tool: KnowledgeBaseTool,
        fixed_rag: FixedRagService,
    ) -> None:
        self._knowledge_tool = knowledge_tool
        self._fixed_rag = fixed_rag

    async def direct_answer(
        self,
        *,
        context: ToolAuthorizationContext,
        question: str,
        knowledge_base_ids: tuple[str, ...],
        model_budget: ModelCallBudgetPort,
    ) -> DirectRagAnswer:
        answer = await self._fixed_rag.answer(
            FixedRagRequest(
                context=_knowledge_context(context),
                question=question,
                knowledge_base_ids=knowledge_base_ids,
            ),
            before_model_call=model_budget.begin_model_call,
        )
        return DirectRagAnswer(
            answer=redact_secret_like_text(answer.answer),
            citations=tuple(
                KnowledgeCitation.model_validate(item.model_dump(mode="python")).model_copy(
                    update={"quote": redact_secret_like_text(item.quote)}
                )
                for item in answer.citations
            ),
            trace_id=answer.trace_id,
            input_tokens=answer.input_tokens,
            output_tokens=answer.output_tokens,
        )

    async def retrieve_step(
        self,
        *,
        context: ToolAuthorizationContext,
        step_id: str,
        question: str,
        knowledge_base_ids: tuple[str, ...],
        budget: BudgetLedger,
    ) -> tuple[tuple[EvidenceItem, ...], str]:
        budget.consume_retrieval()
        raw = await self._knowledge_tool.invoke(
            ToolInvocation(
                tool_call_id=f"retrieval:{step_id}:{budget.usage.retrieval_rounds}",
                tool_name=self._knowledge_tool.registration.tool_name,
                tool_version=self._knowledge_tool.registration.version,
                arguments=KnowledgeBaseToolInput(
                    query=question,
                    knowledge_base_ids=knowledge_base_ids,
                ).model_dump(mode="json"),
            ),
            context,
        )
        output = KnowledgeBaseToolOutput.model_validate(raw)
        evidence = tuple(
            EvidenceItem(
                evidence_id=item.chunk_id,
                step_id=step_id,
                source_kind="knowledge",
                tenant_id=context.tenant_id,
                knowledge_base_id=item.knowledge_base_id,
                excerpt=item.excerpt,
                normalized_score=item.normalized_rank_score,
                citation=AgentEvidenceCitation(
                    citation_id=f"kb:{item.chunk_id}",
                    source_kind="knowledge",
                    knowledge=KnowledgeCitation.model_validate(
                        item.citation.model_dump(mode="python")
                    ),
                ),
            )
            for item in output.evidence
        )
        return evidence, output.retrieval_trace_id


def _knowledge_context(context: ToolAuthorizationContext) -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=context.tenant_id,
        actor_id=context.actor_id,
        request_id=context.request_id,
        roles=context.roles,
    )
