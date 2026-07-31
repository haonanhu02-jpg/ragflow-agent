"""Compile the Phase 08 direct-RAG and bounded Agentic RAG LangGraph."""

from __future__ import annotations

from typing import Literal, TypedDict

from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from ragflow_agent.agent.application.budgets import AgentBudgetExceeded, BudgetLedger
from ragflow_agent.agent.application.evidence import EvidenceSufficiencyPolicy
from ragflow_agent.agent.application.hitl import ApprovalService
from ragflow_agent.agent.application.planning import QueryPlannerPort
from ragflow_agent.agent.application.sensitive import redact_secret_like_text
from ragflow_agent.agent.application.tool_policy import SecureToolExecutionService
from ragflow_agent.agent.domain.agentic import (
    AgentEvidenceCitation,
    AgenticRunStatus,
    AgenticState,
    ApprovalStatus,
    CostStatus,
    EvidenceItem,
    EvidenceStatus,
    KnowledgeCitation,
    ToolAuthorizationContext,
    ToolExecutionOutcome,
    ToolInvocation,
)
from ragflow_agent.agent.ports.agentic import AgentKnowledgeGatewayPort
from ragflow_agent.agent.tools.knowledge_base import KnowledgeBaseToolOutput


class AgenticGraphState(TypedDict):
    payload: dict[str, object]


class AgenticRagNodes:
    def __init__(
        self,
        *,
        planner: QueryPlannerPort,
        knowledge: AgentKnowledgeGatewayPort,
        tools: SecureToolExecutionService,
        approvals: ApprovalService,
        evidence_policy: EvidenceSufficiencyPolicy,
    ) -> None:
        self._planner = planner
        self._knowledge = knowledge
        self._tools = tools
        self._approvals = approvals
        self._evidence_policy = evidence_policy

    async def route(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        try:
            if getattr(self._planner, "uses_model", False):
                ledger.begin_model_call()
            plan = await self._planner.plan(state.question)
            if getattr(self._planner, "uses_model", False):
                _record_model_usage(
                    ledger,
                    input_tokens=_estimated_tokens(state.question),
                    generated_tokens=_estimated_tokens(plan.model_dump_json()),
                )
        except AgentBudgetExceeded:
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.BUDGET_EXHAUSTED,
                        "stop_reason": "planning_budget_exhausted",
                    }
                )
            )
        except Exception:
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.FAILED,
                        "stop_reason": "planning_failed",
                    }
                )
            )
        route = "direct_rag" if plan.is_simple else "agent"
        return _wrap(
            state.model_copy(
                update={"plan": plan, "route": route, "budget_usage": ledger.usage}
            )
        )

    async def direct_rag(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        context = _context(state)
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        answer = None
        try:
            ledger.consume_retrieval()
            answer = await self._knowledge.direct_answer(
                context=context,
                question=state.question,
                knowledge_base_ids=state.authorization.knowledge_base_ids,
                model_budget=ledger,
            )
            if answer.citations:
                _record_model_usage(
                    ledger,
                    input_tokens=answer.input_tokens,
                    generated_tokens=answer.output_tokens,
                )
            state = state.model_copy(update={"budget_usage": ledger.usage})
        except AgentBudgetExceeded:
            if answer is not None and answer.citations and ledger.can_finalize:
                citations = tuple(
                    AgentEvidenceCitation(
                        citation_id=f"kb:{citation.chunk_id}",
                        source_kind="knowledge",
                        knowledge=KnowledgeCitation.model_validate(
                            citation.model_dump(mode="python")
                        ),
                    )
                    for citation in answer.citations
                )
                return _wrap(
                    state.model_copy(
                        update={
                            "budget_usage": ledger.usage,
                            "citations": citations,
                            "retrieval_trace_ids": (answer.trace_id,),
                            "final_answer": redact_secret_like_text(answer.answer),
                            "final_status": AgenticRunStatus.COMPLETED,
                            "stop_reason": "budget_exhausted_after_sufficient_evidence",
                        }
                    )
                )
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.BUDGET_EXHAUSTED,
                        "stop_reason": "model_budget_exhausted",
                    }
                )
            )
        except Exception:
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.FAILED,
                        "stop_reason": "direct_rag_failed",
                    }
                )
            )
        if answer.citations:
            citations = tuple(
                AgentEvidenceCitation(
                    citation_id=f"kb:{citation.chunk_id}",
                    source_kind="knowledge",
                    knowledge=KnowledgeCitation.model_validate(citation.model_dump(mode="python")),
                )
                for citation in answer.citations
            )
            status = AgenticRunStatus.COMPLETED
        else:
            citations = ()
            status = AgenticRunStatus.NO_EVIDENCE
        return _wrap(
            state.model_copy(
                update={
                    "citations": citations,
                    "retrieval_trace_ids": (answer.trace_id,),
                    "final_answer": redact_secret_like_text(answer.answer),
                    "final_status": status,
                    "stop_reason": "direct_rag_completed",
                }
            )
        )

    async def execute_step(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        if state.plan is None:
            raise ValueError("Agentic execution requires a plan")
        if state.current_step >= len(state.plan.steps):
            return _wrap(state)
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        try:
            ledger.consume_iteration()
            step = state.plan.steps[state.current_step]
            if step.preferred_tool == "knowledge_base":
                ledger.consume_retrieval()
            invocation = ToolInvocation(
                tool_call_id=f"{state.run_id}:{step.step_id}:{state.budget_usage.retrieval_rounds}",
                tool_name=step.preferred_tool,
                tool_version=step.tool_version,
                arguments=(
                    {
                        "query": step.question,
                        "knowledge_base_ids": list(state.authorization.knowledge_base_ids),
                        "top_k": 20,
                        "top_n": 5,
                    }
                    if step.preferred_tool == "knowledge_base"
                    else step.tool_arguments
                ),
            )
            outcome = await self._tools.execute(invocation, _context(state), ledger)
        except AgentBudgetExceeded:
            decision = (
                self._evidence_policy.evaluate(
                    tenant_id=state.authorization.tenant_id,
                    plan=state.plan,
                    evidence=state.evidence,
                )
                if state.plan is not None
                else None
            )
            completed_with_evidence = (
                decision is not None
                and decision.status is EvidenceStatus.SUFFICIENT
                and ledger.can_finalize
            )
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": (
                            AgenticRunStatus.COMPLETED
                            if completed_with_evidence
                            else AgenticRunStatus.BUDGET_EXHAUSTED
                        ),
                        "stop_reason": (
                            "budget_exhausted_after_sufficient_evidence"
                            if completed_with_evidence
                            else "budget_exhausted"
                        ),
                    }
                )
            )
        except Exception:
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.FAILED,
                        "stop_reason": "tool_failure",
                    }
                )
            )
        if outcome.status == "approval_required":
            approval = await self._approvals.request(
                run_id=state.run_id,
                thread_id=state.thread_id,
                invocation=invocation,
                context=_context(state),
                reason=outcome.approval_reason or "Tool approval required",
                required_roles=outcome.required_roles,
            )
            return _wrap(
                state.model_copy(
                    update={
                        "pending_tool_invocation": invocation,
                        "approval_id": approval.approval_id,
                        "hitl_status": ApprovalStatus.APPROVAL_REQUIRED,
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.APPROVAL_REQUIRED,
                        "stop_reason": "approval_required",
                    }
                )
            )
        if outcome.status == "failed":
            return _wrap(
                state.model_copy(
                    update={
                        "tool_calls": (*state.tool_calls, outcome.summary),
                        "iteration": state.iteration + 1,
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.FAILED,
                        "stop_reason": outcome.summary.error_code or "tool_failure",
                    }
                )
            )
        return _wrap(_apply_tool_outcome(state, step.step_id, outcome, ledger))

    async def await_approval(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        if state.approval_id is None or state.pending_tool_invocation is None:
            raise ValueError("approval node requires a persisted approval and Tool call")
        interrupt(
            {
                "approval_id": state.approval_id,
                "run_id": state.run_id,
                "tool_name": state.pending_tool_invocation.tool_name,
                "tool_version": state.pending_tool_invocation.tool_version,
                "argument_digest": state.pending_tool_invocation.argument_digest,
            }
        )
        approval = await self._approvals.get_current(
            approval_id=state.approval_id,
            tenant_id=state.authorization.tenant_id,
        )
        if approval.status in {
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
            ApprovalStatus.CANCELLED,
        }:
            mapped = {
                ApprovalStatus.REJECTED: AgenticRunStatus.REJECTED,
                ApprovalStatus.EXPIRED: AgenticRunStatus.REJECTED,
                ApprovalStatus.CANCELLED: AgenticRunStatus.CANCELLED,
            }[approval.status]
            return _wrap(
                state.model_copy(
                    update={
                        "hitl_status": approval.status,
                        "final_status": mapped,
                        "stop_reason": f"approval_{approval.status.value}",
                    }
                )
            )
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        try:
            outcome = await self._approvals.resume(
                approval_id=state.approval_id,
                invocation=state.pending_tool_invocation,
                context=_context(state),
                budget=ledger,
            )
        except Exception:
            return _wrap(
                state.model_copy(
                    update={
                        "budget_usage": ledger.usage,
                        "final_status": AgenticRunStatus.FAILED,
                        "stop_reason": "approval_resume_failed",
                    }
                )
            )
        step_id = state.plan.steps[state.current_step].step_id if state.plan else "tool"
        applied = _apply_tool_outcome(state, step_id, outcome, ledger)
        return _wrap(
            applied.model_copy(
                update={
                    "pending_tool_invocation": None,
                    "hitl_status": ApprovalStatus.SUCCEEDED,
                    "final_status": None,
                    "stop_reason": None,
                }
            )
        )

    async def evaluate(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        if state.plan is None:
            raise ValueError("evidence evaluation requires a plan")
        decision = self._evidence_policy.evaluate(
            tenant_id=state.authorization.tenant_id,
            plan=state.plan,
            evidence=state.evidence,
        )
        if decision.status is EvidenceStatus.SUFFICIENT:
            status = AgenticRunStatus.COMPLETED
        elif decision.status is EvidenceStatus.PARTIAL_EVIDENCE:
            status = AgenticRunStatus.PARTIAL_EVIDENCE
        elif decision.status is EvidenceStatus.NO_EVIDENCE:
            status = AgenticRunStatus.NO_EVIDENCE
        else:
            status = AgenticRunStatus.CONFLICTING_EVIDENCE
        ledger = BudgetLedger(state.budget_limits, state.budget_usage)
        can_retry = (
            decision.status in {EvidenceStatus.PARTIAL_EVIDENCE, EvidenceStatus.NO_EVIDENCE}
            and ledger.usage.retrieval_rounds < ledger.limits.max_retrieval_rounds
            and (not state.tool_calls or state.tool_calls[-1].status != "reused")
        )
        return _wrap(
            state.model_copy(
                update={
                    "final_status": None if can_retry else status,
                    "stop_reason": "additional_retrieval" if can_retry else decision.reason,
                    "current_step": (0 if can_retry else len(state.plan.steps)),
                }
            )
        )

    async def finalize(self, raw: AgenticGraphState) -> AgenticGraphState:
        state = _state(raw)
        if state.final_status is None:
            raise ValueError("finalize requires a terminal status")
        eligible = tuple(item for item in state.evidence if item.citation is not None)
        citations = tuple(item.citation for item in eligible if item.citation is not None)
        answer: str | None
        if state.final_status is AgenticRunStatus.COMPLETED:
            answer = "\n".join(f"[{_citation_id(item)}] {item.excerpt}" for item in eligible)
        elif state.final_status is AgenticRunStatus.PARTIAL_EVIDENCE:
            answer = "仅获得部分证据:\n" + "\n".join(
                f"[{_citation_id(item)}] {item.excerpt}" for item in eligible
            )
        elif state.final_status is AgenticRunStatus.CONFLICTING_EVIDENCE:
            answer = "检索到尚未解决的冲突证据, 无法给出单一确定结论。"
        elif state.final_status is AgenticRunStatus.NO_EVIDENCE:
            answer = "未检索到足够的授权证据。"
        elif state.final_status is AgenticRunStatus.BUDGET_EXHAUSTED:
            answer = "运行预算已耗尽, 且没有足够证据完成回答。"
        else:
            answer = state.final_answer
        return _wrap(state.model_copy(update={"citations": citations, "final_answer": answer}))


def build_agentic_rag_graph(
    nodes: AgenticRagNodes,
    checkpointer: BaseCheckpointSaver[str],
) -> CompiledStateGraph[AgenticGraphState, None, AgenticGraphState, AgenticGraphState]:
    builder = StateGraph(AgenticGraphState)
    builder.add_node("route", RunnableLambda(nodes.route))
    builder.add_node("direct_rag", RunnableLambda(nodes.direct_rag))
    builder.add_node("execute_step", RunnableLambda(nodes.execute_step))
    builder.add_node("await_approval", RunnableLambda(nodes.await_approval))
    builder.add_node("evaluate", RunnableLambda(nodes.evaluate))
    builder.add_node("finalize", RunnableLambda(nodes.finalize))
    builder.add_edge(START, "route")
    builder.add_conditional_edges(
        "route",
        _after_route,
        {"direct_rag": "direct_rag", "agent": "execute_step", "finalize": "finalize"},
    )
    builder.add_edge("direct_rag", END)
    builder.add_conditional_edges(
        "execute_step",
        _after_execute,
        {
            "approval": "await_approval",
            "continue": "execute_step",
            "evaluate": "evaluate",
            "finalize": "finalize",
        },
    )
    builder.add_conditional_edges(
        "await_approval",
        _after_approval,
        {"continue": "execute_step", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "evaluate",
        lambda raw: "retry" if _state(raw).final_status is None else "finalize",
        {"retry": "execute_step", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=checkpointer, name="phase08_agentic_rag")


def _after_execute(raw: AgenticGraphState) -> str:
    state = _state(raw)
    if state.final_status is AgenticRunStatus.APPROVAL_REQUIRED:
        return "approval"
    if state.final_status in {AgenticRunStatus.FAILED, AgenticRunStatus.BUDGET_EXHAUSTED}:
        return "finalize"
    if state.plan is not None and state.current_step < len(state.plan.steps):
        return "continue"
    return "evaluate"


def _after_route(raw: AgenticGraphState) -> str:
    state = _state(raw)
    return "finalize" if state.final_status is not None else state.route


def _after_approval(raw: AgenticGraphState) -> str:
    state = _state(raw)
    return "finalize" if state.final_status is not None else "continue"


def _apply_tool_outcome(
    state: AgenticState,
    step_id: str,
    outcome: object,
    ledger: BudgetLedger,
) -> AgenticState:
    typed = ToolExecutionOutcome.model_validate(outcome)
    items: tuple[EvidenceItem, ...]
    trace_id: str | None = None
    if typed.summary.tool_name == "knowledge_base":
        output = KnowledgeBaseToolOutput.model_validate(typed.output)
        trace_id = output.retrieval_trace_id
        items = tuple(
            EvidenceItem(
                evidence_id=item.chunk_id,
                step_id=step_id,
                source_kind="knowledge",
                tenant_id=state.authorization.tenant_id,
                knowledge_base_id=item.knowledge_base_id,
                excerpt=redact_secret_like_text(item.excerpt),
                normalized_score=item.normalized_rank_score,
                citation=AgentEvidenceCitation(
                    citation_id=f"kb:{item.chunk_id}",
                    source_kind="knowledge",
                    knowledge=KnowledgeCitation.model_validate(
                        item.citation.model_dump(mode="python")
                    ),
                ),
                injection_detected=typed.injection_detected,
            )
            for item in output.evidence
        )
    else:
        source_kind: Literal["sql", "api"] = (
            "sql" if typed.summary.tool_name == "readonly_sql" else "api"
        )
        items = _structured_tool_evidence(
            state=state,
            step_id=step_id,
            source_kind=source_kind,
            outcome=typed,
        )
    next_step = state.current_step + 1
    if (
        typed.summary.tool_name == "knowledge_base"
        and ledger.usage.retrieval_rounds >= ledger.limits.max_retrieval_rounds
        and state.plan is not None
    ):
        next_step = len(state.plan.steps)
    return state.model_copy(
        update={
            "evidence": (*state.evidence, *items),
            "tool_calls": (*state.tool_calls, typed.summary),
            "retrieval_trace_ids": (
                (*state.retrieval_trace_ids, trace_id)
                if trace_id is not None
                else state.retrieval_trace_ids
            ),
            "current_step": next_step,
            "iteration": state.iteration + 1,
            "budget_usage": ledger.usage,
        }
    )


def _structured_tool_evidence(
    *,
    state: AgenticState,
    step_id: str,
    source_kind: Literal["sql", "api"],
    outcome: ToolExecutionOutcome,
) -> tuple[EvidenceItem, ...]:
    citation = AgentEvidenceCitation(
        citation_id=f"{source_kind}:{outcome.summary.tool_call_id}",
        source_kind=source_kind,
        tool_name=outcome.summary.tool_name,
        result_digest=outcome.summary.output_digest,
    )
    raw_items: object = None
    if isinstance(outcome.output, dict):
        raw_items = outcome.output.get("evidence")
    if isinstance(raw_items, list):
        parsed: list[EvidenceItem] = []
        for index, raw in enumerate(raw_items, start=1):
            if not isinstance(raw, dict):
                continue
            excerpt = redact_secret_like_text(str(raw.get("excerpt", "")).strip()[:2_000])
            if not excerpt:
                continue
            score = raw.get("normalized_score", 1)
            normalized_score = float(score) if isinstance(score, (int, float)) else 0
            parsed.append(
                EvidenceItem(
                    evidence_id=f"tool:{outcome.summary.tool_call_id}:{index}",
                    step_id=step_id,
                    source_kind=source_kind,
                    tenant_id=state.authorization.tenant_id,
                    excerpt=excerpt,
                    normalized_score=max(0, min(1, normalized_score)),
                    citation=citation.model_copy(
                        update={"citation_id": f"{citation.citation_id}:{index}"}
                    ),
                    injection_detected=outcome.injection_detected,
                    fact_key=(
                        str(raw["fact_key"])[:256] if raw.get("fact_key") is not None else None
                    ),
                    stance=(str(raw["stance"])[:256] if raw.get("stance") is not None else None),
                )
            )
        if parsed:
            return tuple(parsed)
    return (
        EvidenceItem(
            evidence_id=f"tool:{outcome.summary.tool_call_id}",
            step_id=step_id,
            source_kind=source_kind,
            tenant_id=state.authorization.tenant_id,
            excerpt=redact_secret_like_text(str(outcome.output)[:2_000]),
            normalized_score=1,
            citation=citation,
            injection_detected=outcome.injection_detected,
        ),
    )


def _context(state: AgenticState) -> ToolAuthorizationContext:
    return ToolAuthorizationContext(
        tenant_id=state.authorization.tenant_id,
        actor_id=state.authorization.user_id,
        request_id=state.request_id,
        roles=state.authorization.roles,
    )


def _state(raw: AgenticGraphState) -> AgenticState:
    return AgenticState.model_validate(raw["payload"])


def _wrap(state: AgenticState) -> AgenticGraphState:
    return {"payload": state.model_dump(mode="json")}


def _citation_id(item: EvidenceItem) -> str:
    if item.citation is None:
        raise ValueError("eligible evidence has no citation")
    return item.citation.citation_id


def _estimated_tokens(value: str) -> int:
    return max(1, (len(value) + 3) // 4)


def _record_model_usage(
    ledger: BudgetLedger,
    *,
    input_tokens: int,
    generated_tokens: int,
) -> None:
    input_rate = ledger.limits.model_input_cost_per_million_tokens_usd
    output_rate = ledger.limits.model_output_cost_per_million_tokens_usd
    if input_rate is not None and output_rate is not None:
        cost = (input_tokens * input_rate + generated_tokens * output_rate) / 1_000_000
        cost_status = CostStatus.KNOWN
    else:
        cost = None
        cost_status = CostStatus.UNKNOWN
    ledger.record_model_usage(
        input_tokens=input_tokens,
        generated_tokens=generated_tokens,
        cost_usd=cost,
        cost_status=cost_status,
    )
