"""Phase 08 Agentic RAG runtime over the existing LangGraph checkpoint boundary."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.types import Command

from ragflow_agent.agent.application.budgets import AgentBudgetExceeded, BudgetLedger
from ragflow_agent.agent.application.hitl import ApprovalDecision, ApprovalService
from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.application.sensitive import redact_secret_like_text
from ragflow_agent.agent.application.trace import LoggingAgentRunTraceMetrics
from ragflow_agent.agent.domain.agentic import (
    AgenticResumeRequest,
    AgenticRunRequest,
    AgenticRunResult,
    AgenticRunStatus,
    AgenticState,
    AgentRunTrace,
    ApprovalStatus,
    ToolAuthorizationContext,
)
from ragflow_agent.agent.domain.errors import AgentCheckpointError
from ragflow_agent.agent.graphs.agentic_rag import (
    AgenticGraphState,
    AgenticRagNodes,
    build_agentic_rag_graph,
)
from ragflow_agent.agent.infrastructure.checkpoint.scoped import agentic_checkpoint_config
from ragflow_agent.agent.ports.agentic import AgentRunRepositoryPort, AgentRunTraceMetricsPort
from ragflow_agent.shared.ports.time import Clock


class AgenticRagRuntime:
    """Start/resume Agentic runs while preserving budget and tenant scope."""

    def __init__(
        self,
        *,
        nodes: AgenticRagNodes,
        checkpointer: BaseCheckpointSaver[str],
        approvals: ApprovalService,
        memory: LongTermMemoryService,
        runs: AgentRunRepositoryPort,
        clock: Clock,
        trace_metrics: AgentRunTraceMetricsPort | None = None,
    ) -> None:
        self._graph = build_agentic_rag_graph(nodes, checkpointer)
        self._approvals = approvals
        self._memory = memory
        self._runs = runs
        self._clock = clock
        self._trace_metrics = trace_metrics or LoggingAgentRunTraceMetrics()

    async def run(self, request: AgenticRunRequest) -> AgenticRunResult:
        config = agentic_checkpoint_config(
            tenant_id=request.context.tenant_id,
            thread_id=request.thread_id,
        )
        snapshot = await self._graph.aget_state(config)
        if snapshot.values:
            raise AgentCheckpointError(
                "Agentic thread already has a checkpoint; use resume",
                error_code="agent_checkpoint_already_exists",
            )
        context = _knowledge_context(request.context)
        initial = AgenticState(
            run_id=request.run_id,
            thread_id=request.thread_id,
            request_id=request.context.request_id,
            authorization=request.context,
            question=redact_secret_like_text(request.question),
            memory_consent=await self._memory.consent_enabled(context),
            budget_limits=request.budget_limits,
            model_provider_ids=request.model_provider_ids,
        )
        await self._persist(initial)
        return await self._invoke(initial, config, {"payload": initial.model_dump(mode="json")})

    async def resume(self, request: AgenticResumeRequest) -> AgenticRunResult:
        config = agentic_checkpoint_config(
            tenant_id=request.tenant_id,
            thread_id=request.thread_id,
        )
        state = await self._load_state(config)
        if state.run_id != request.run_id or state.authorization.tenant_id != request.tenant_id:
            raise AgentCheckpointError(
                "Agentic resume identity does not own the run",
                error_code="agent_checkpoint_access_denied",
            )
        approval = await self._approvals.get_current(
            approval_id=request.approval_id,
            tenant_id=request.tenant_id,
        )
        if (
            approval.run_id != state.run_id
            or approval.thread_id != state.thread_id
            or state.approval_id != approval.approval_id
        ):
            raise AgentCheckpointError(
                "approval does not belong to the requested Agentic run",
                error_code="agent_approval_scope_mismatch",
            )
        if (
            approval.status is ApprovalStatus.SUCCEEDED
            and state.hitl_status is ApprovalStatus.SUCCEEDED
        ):
            return AgenticRunResult(state=state, interrupted=False)
        decision = ApprovalDecision(request.decision)
        await self._approvals.decide(
            approval_id=request.approval_id,
            context=ToolAuthorizationContext(
                tenant_id=request.tenant_id,
                actor_id=request.approver_id,
                request_id=request.approver_request_id,
                roles=request.approver_roles,
            ),
            decision=decision,
        )
        command: Command[object] = Command(resume={"approval_id": request.approval_id})
        return await self._invoke(state, config, command)

    async def get(self, *, tenant_id: str, thread_id: str, run_id: str) -> AgenticRunResult:
        state = await self._load_state(
            agentic_checkpoint_config(tenant_id=tenant_id, thread_id=thread_id)
        )
        if state.run_id != run_id or state.authorization.tenant_id != tenant_id:
            raise AgentCheckpointError(
                "Agentic run is outside the requested scope",
                error_code="agent_checkpoint_access_denied",
            )
        return AgenticRunResult(
            state=state,
            interrupted=state.final_status is AgenticRunStatus.APPROVAL_REQUIRED,
        )

    async def _invoke(
        self,
        prior: AgenticState,
        config: RunnableConfig,
        graph_input: AgenticGraphState | Command[object],
    ) -> AgenticRunResult:
        started = time.monotonic()
        remaining_runtime = (
            prior.budget_limits.max_active_runtime_seconds
            - prior.budget_usage.active_runtime_seconds
        )
        timed_out = remaining_runtime <= 0
        if not timed_out:
            try:
                async with asyncio.timeout(remaining_runtime):
                    await self._graph.ainvoke(graph_input, config)
            except TimeoutError:
                timed_out = True
        state = await self._load_state(config)
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        try:
            ledger.add_active_runtime(time.monotonic() - started)
            updated = state.model_copy(
                update={
                    "budget_usage": ledger.usage,
                    "final_status": (
                        AgenticRunStatus.BUDGET_EXHAUSTED
                        if timed_out
                        else state.final_status
                    ),
                    "stop_reason": (
                        "active_runtime_budget_exhausted"
                        if timed_out
                        else state.stop_reason
                    ),
                }
            )
        except AgentBudgetExceeded:
            if (
                state.final_status is AgenticRunStatus.COMPLETED
                and state.citations
                and ledger.can_finalize
            ):
                updated = state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "stop_reason": "active_runtime_exhausted_after_finalization",
                    }
                )
            else:
                updated = state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.BUDGET_EXHAUSTED,
                        "stop_reason": "active_runtime_budget_exhausted",
                    }
                )
        checkpoint_update = {"payload": updated.model_dump(mode="json")}
        await self._graph.aupdate_state(config, checkpoint_update)
        await self._persist(updated)
        return AgenticRunResult(
            state=updated,
            interrupted=updated.final_status is AgenticRunStatus.APPROVAL_REQUIRED,
        )

    async def _load_state(self, config: RunnableConfig) -> AgenticState:
        snapshot = await self._graph.aget_state(config)
        values = snapshot.values
        if not isinstance(values, Mapping):
            raise AgentCheckpointError("Agentic checkpoint has invalid values")
        raw = values.get("payload")
        if not isinstance(raw, Mapping):
            raise AgentCheckpointError("Agentic checkpoint payload is missing")
        return AgenticState.model_validate(raw)

    async def _persist(self, state: AgenticState) -> None:
        now = self._clock.now()
        try:
            existing = await self._runs.get(
                tenant_id=state.authorization.tenant_id,
                run_id=state.run_id,
            )
        except Exception as error:
            self._trace_metrics.record_write_failure(
                tenant_id=state.authorization.tenant_id,
                reason=f"read:{type(error).__name__}",
            )
            existing = None
        trace = AgentRunTrace(
            run_id=state.run_id,
            thread_id=state.thread_id,
            request_id=state.request_id,
            tenant_id=state.authorization.tenant_id,
            user_id=state.authorization.user_id,
            status=state.final_status,
            retrieval_trace_ids=state.retrieval_trace_ids,
            model_provider_ids=state.model_provider_ids,
            tool_calls=state.tool_calls,
            budget_limits=state.budget_limits,
            budget_usage=state.budget_usage,
            stop_reason=state.stop_reason,
            started_at=existing.started_at if existing is not None else now,
            updated_at=now,
        )
        try:
            await self._runs.save(trace)
        except Exception as error:
            self._trace_metrics.record_write_failure(
                tenant_id=state.authorization.tenant_id,
                reason=f"write:{type(error).__name__}",
            )


def _knowledge_context(snapshot: object) -> ToolAuthorizationContext:
    from ragflow_agent.agent.domain.agentic import AgenticAuthorizationSnapshot

    typed = AgenticAuthorizationSnapshot.model_validate(snapshot)
    return ToolAuthorizationContext(
        tenant_id=typed.tenant_id,
        actor_id=typed.user_id,
        request_id=typed.request_id,
        roles=typed.roles,
    )
