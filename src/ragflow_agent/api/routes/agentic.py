"""Phase 08 Agentic RAG run, HITL-resume, and governed-memory HTTP API."""

from __future__ import annotations

from typing import Literal, cast

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.agent.domain.agentic import (
    AgenticAuthorizationSnapshot,
    AgenticResumeRequest,
    AgenticRunRequest,
    AgenticRunResult,
    BudgetLimits,
    LongTermMemory,
    MemoryConsent,
    ToolAuthorizationContext,
)
from ragflow_agent.agent.runtime import AgenticRuntimeBundle
from ragflow_agent.api.security import require_trusted_identity
from ragflow_agent.config import AgenticRagSettings
from ragflow_agent.observability import current_trace_context, new_correlation_id
from ragflow_agent.shared.ports.identity import Uuid4Generator


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartAgenticRunBody(ApiModel):
    question: str = Field(min_length=1, max_length=8_000)
    knowledge_base_ids: tuple[str, ...] = Field(min_length=1, max_length=32)
    thread_id: str | None = Field(default=None, min_length=1, max_length=128)


class ResumeAgenticRunBody(ApiModel):
    thread_id: str = Field(min_length=1, max_length=128)
    approval_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve", "reject", "cancel"]


class MemoryConsentBody(ApiModel):
    enabled: bool
    consent_version: str = Field(min_length=1, max_length=64)


class RememberBody(ApiModel):
    content: str = Field(min_length=1, max_length=2_000)
    source: str = Field(min_length=1, max_length=128)
    explicit_user_request: Literal[True]


def build_agentic_router() -> APIRouter:
    router = APIRouter(prefix="/v1/agentic-rag", tags=["agentic-rag"])
    ids = Uuid4Generator()

    @router.post("/runs", response_model=AgenticRunResult, status_code=201)
    async def start_run(request: Request, body: StartAgenticRunBody) -> AgenticRunResult:
        identity = require_trusted_identity(request)
        request_id = _request_id()
        settings = cast(AgenticRagSettings, request.app.state.settings.agentic_rag)
        run_id = ids.new_id()
        return await _bundle(request).runtime.run(
            AgenticRunRequest(
                run_id=run_id,
                thread_id=body.thread_id or ids.new_id(),
                context=AgenticAuthorizationSnapshot(
                    tenant_id=identity.tenant_id,
                    user_id=identity.subject_id,
                    request_id=request_id,
                    roles=identity.roles,
                    knowledge_base_ids=body.knowledge_base_ids,
                ),
                question=body.question,
                budget_limits=_budget_limits(settings),
                model_provider_ids=(
                    f"chat:{request.app.state.settings.models.chat_model}",
                ),
            )
        )

    @router.post("/runs/{run_id}/resume", response_model=AgenticRunResult)
    async def resume_run(
        request: Request,
        run_id: str,
        body: ResumeAgenticRunBody,
    ) -> AgenticRunResult:
        identity = require_trusted_identity(request)
        return await _bundle(request).runtime.resume(
            AgenticResumeRequest(
                run_id=run_id,
                thread_id=body.thread_id,
                approval_id=body.approval_id,
                tenant_id=identity.tenant_id,
                approver_id=identity.subject_id,
                approver_request_id=_request_id(),
                approver_roles=identity.roles,
                decision=body.decision,
            )
        )

    @router.get("/runs/{run_id}", response_model=AgenticRunResult)
    async def get_run(
        request: Request,
        run_id: str,
        thread_id: str = Query(min_length=1, max_length=128),
    ) -> AgenticRunResult:
        identity = require_trusted_identity(request)
        return await _bundle(request).runtime.get(
            tenant_id=identity.tenant_id,
            thread_id=thread_id,
            run_id=run_id,
        )

    @router.put("/memory/consent", response_model=MemoryConsent)
    async def set_memory_consent(
        request: Request,
        body: MemoryConsentBody,
    ) -> MemoryConsent:
        return await _bundle(request).memory.set_consent(
            _context(request),
            enabled=body.enabled,
            consent_version=body.consent_version,
        )

    @router.post("/memory", response_model=LongTermMemory, status_code=201)
    async def remember(request: Request, body: RememberBody) -> LongTermMemory:
        return await _bundle(request).memory.remember(
            _context(request),
            content=body.content,
            source=body.source,
            explicit_user_request=body.explicit_user_request,
        )

    @router.get("/memory", response_model=tuple[LongTermMemory, ...])
    async def list_memory(request: Request) -> tuple[LongTermMemory, ...]:
        return await _bundle(request).memory.list_active(_context(request))

    @router.delete("/memory/{memory_id}", status_code=204)
    async def delete_memory(request: Request, memory_id: str) -> None:
        await _bundle(request).memory.delete(_context(request), memory_id)

    return router


def _bundle(request: Request) -> AgenticRuntimeBundle:
    runtime = getattr(request.app.state, "agentic_runtime_bundle", None)
    if runtime is None:
        raise RuntimeError("Agentic RAG runtime is not configured")
    return cast(AgenticRuntimeBundle, runtime)


def _request_id() -> str:
    trace = current_trace_context()
    return trace.trace_id if trace is not None else new_correlation_id()


def _context(request: Request) -> ToolAuthorizationContext:
    identity = require_trusted_identity(request)
    return ToolAuthorizationContext(
        tenant_id=identity.tenant_id,
        actor_id=identity.subject_id,
        request_id=_request_id(),
        roles=identity.roles,
    )


def _budget_limits(settings: AgenticRagSettings) -> BudgetLimits:
    return BudgetLimits(
        max_agent_iterations=settings.max_agent_iterations,
        max_model_calls=settings.max_model_calls,
        max_retrieval_rounds=settings.max_retrieval_rounds,
        max_tool_attempts=settings.max_tool_attempts,
        max_total_tokens=settings.max_total_tokens,
        max_generated_tokens=settings.max_generated_tokens,
        finalization_token_reserve=settings.finalization_token_reserve,
        max_active_runtime_seconds=settings.max_active_runtime_seconds,
        max_known_cost_usd=settings.max_known_cost_usd,
        model_input_cost_per_million_tokens_usd=(
            settings.model_input_cost_per_million_tokens_usd
        ),
        model_output_cost_per_million_tokens_usd=(
            settings.model_output_cost_per_million_tokens_usd
        ),
    )
