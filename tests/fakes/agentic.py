"""Deterministic Agentic RAG persistence and external-system fakes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta

from ragflow_agent.agent.domain.agentic import (
    AgentRunTrace,
    ApprovalRequest,
    LongTermMemory,
    MemoryConsent,
    ToolAuthorizationContext,
    ToolEffect,
    ToolInvocation,
    ToolRegistration,
    ToolRiskLevel,
)
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.retrieval import (
    Citation,
    RetrievalCandidate,
    RetrievalEmptyReason,
    RetrievalQuery,
    RetrievalResult,
    RetrievalTrace,
    RetrievalTraceStatus,
    ScoreBreakdown,
)


class MemoryApprovalRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], ApprovalRequest] = {}

    async def save(self, request: ApprovalRequest) -> None:
        key = (request.tenant_id, request.approval_id)
        if key in self.items:
            raise ValueError("duplicate approval")
        self.items[key] = request

    async def get(self, *, tenant_id: str, approval_id: str) -> ApprovalRequest | None:
        return self.items.get((tenant_id, approval_id))

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> ApprovalRequest | None:
        return next(
            (
                item
                for (tenant, _), item in self.items.items()
                if tenant == tenant_id and item.idempotency_key == idempotency_key
            ),
            None,
        )

    async def compare_and_set(
        self,
        *,
        tenant_id: str,
        approval_id: str,
        expected_revision: int,
        request: ApprovalRequest,
    ) -> bool:
        key = (tenant_id, approval_id)
        current = self.items.get(key)
        if current is None or current.revision != expected_revision:
            return False
        self.items[key] = request
        return True


class MemoryAgenticMemoryRepository:
    def __init__(self) -> None:
        self.consents: dict[tuple[str, str], MemoryConsent] = {}
        self.memories: dict[tuple[str, str, str], LongTermMemory] = {}

    async def save_consent(self, consent: MemoryConsent) -> None:
        self.consents[(consent.tenant_id, consent.user_id)] = consent

    async def get_consent(self, *, tenant_id: str, user_id: str) -> MemoryConsent | None:
        return self.consents.get((tenant_id, user_id))

    async def save_memory(self, memory: LongTermMemory) -> None:
        self.memories[(memory.tenant_id, memory.user_id, memory.memory_id)] = memory

    async def list_memories(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> tuple[LongTermMemory, ...]:
        return tuple(
            item
            for (tenant, user, _), item in self.memories.items()
            if tenant == tenant_id and user == user_id
        )

    async def delete_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        memory_id: str,
    ) -> bool:
        return self.memories.pop((tenant_id, user_id, memory_id), None) is not None

    async def delete_user_memories(self, *, tenant_id: str, user_id: str) -> int:
        keys = [key for key in self.memories if key[:2] == (tenant_id, user_id)]
        for key in keys:
            del self.memories[key]
        return len(keys)

    async def delete_expired(self, *, before: datetime) -> int:
        keys = [key for key, item in self.memories.items() if item.expires_at <= before]
        for key in keys:
            del self.memories[key]
        return len(keys)


class MemoryAgentRunRepository:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], AgentRunTrace] = {}

    async def save(self, trace: AgentRunTrace) -> None:
        self.items[(trace.tenant_id, trace.run_id)] = trace

    async def get(self, *, tenant_id: str, run_id: str) -> AgentRunTrace | None:
        return self.items.get((tenant_id, run_id))


class FakeRegisteredTool:
    def __init__(
        self,
        *,
        name: str = "fake_action",
        output: object = None,
        effect: ToolEffect = ToolEffect.READ_ONLY,
        risk: ToolRiskLevel = ToolRiskLevel.LOW,
        requires_hitl: bool = False,
        allowed_roles: tuple[str, ...] = (),
        approval_roles: tuple[str, ...] = (),
        max_retries: int = 0,
    ) -> None:
        self._registration = ToolRegistration(
            tool_name=name,
            version="1",
            description="deterministic fake registered Tool",
            input_schema={"type": "object", "additionalProperties": True},
            output_schema={},
            effect=effect,
            risk_level=risk,
            allowed_roles=allowed_roles,
            approval_roles=approval_roles,
            timeout_seconds=1,
            max_retries=max_retries,
            max_output_bytes=100_000,
            idempotent=True,
            requires_hitl=requires_hitl,
            sensitive_fields=("secret",),
        )
        self.output = output if output is not None else {"ok": True}
        self.calls: list[tuple[ToolInvocation, ToolAuthorizationContext]] = []
        self.error: Exception | None = None

    @property
    def registration(self) -> ToolRegistration:
        return self._registration

    async def invoke(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> object:
        self.calls.append((invocation, context))
        if self.error is not None:
            raise self.error
        return self.output


class FakeSqlExecutor:
    def __init__(self, rows: Sequence[Mapping[str, object]] = ()) -> None:
        self.rows = rows
        self.calls: list[dict[str, object]] = []

    async def execute(
        self,
        *,
        statement: str,
        parameters: Mapping[str, object],
        timeout_seconds: float,
        max_rows: int,
    ) -> Sequence[Mapping[str, object]]:
        self.calls.append(
            {
                "statement": statement,
                "parameters": dict(parameters),
                "timeout_seconds": timeout_seconds,
                "max_rows": max_rows,
            }
        )
        return self.rows


class FakeApiTransport:
    def __init__(self, output: object) -> None:
        self.output = output
        self.calls: list[dict[str, object]] = []

    async def request(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        return self.output


class FakeSecretProvider:
    def __init__(self, headers: Mapping[str, str] | None = None) -> None:
        self.headers = dict(headers or {})

    async def headers_for(self, credential_ref: str) -> Mapping[str, str]:
        del credential_ref
        return self.headers


class EchoKnowledgeQueryService:
    """Return one authorized candidate for every query, or a real empty result."""

    def __init__(self, *, empty: bool = False, content: str = "authorized evidence") -> None:
        self.empty = empty
        self.content = content
        self.calls: list[tuple[AuthorizationContext, RetrievalQuery]] = []

    async def retrieve(
        self,
        context: AuthorizationContext,
        query: RetrievalQuery,
    ) -> RetrievalResult:
        self.calls.append((context, query))
        now = datetime.now(UTC)
        trace = RetrievalTrace(
            trace_id=query.trace_id,
            request_id=query.request_id,
            tenant_id=context.tenant_id,
            original_query=query.text,
            authorization_applied=True,
            events=(),
            knowledge_base_ids=query.knowledge_base_ids,
            status=(
                RetrievalTraceStatus.NO_EVIDENCE if self.empty else RetrievalTraceStatus.SUCCESS
            ),
            started_at=now,
            completed_at=now,
            expires_at=now + timedelta(days=30),
        )
        if self.empty:
            return RetrievalResult(
                query=query,
                candidates=(),
                trace=trace,
                empty_reason=RetrievalEmptyReason.NO_EVIDENCE,
            )
        kb = query.knowledge_base_ids[0]
        citation = Citation(
            tenant_id=context.tenant_id,
            knowledge_base_id=kb,
            document_id="doc-1",
            document_version_id="version-1",
            chunk_id="chunk-1",
            quote=self.content,
            page_number=1,
        )
        candidate = RetrievalCandidate(
            tenant_id=context.tenant_id,
            knowledge_base_id=kb,
            document_id="doc-1",
            document_version_id="version-1",
            chunk_id="chunk-1",
            content=self.content,
            score=ScoreBreakdown(final_score=1, final_rank=1),
            citation=citation,
        )
        return RetrievalResult(query=query, candidates=(candidate,), trace=trace)
