import asyncio
from datetime import UTC, datetime
from typing import cast

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from ragflow_agent.agent.application.agentic_runtime import AgenticRagRuntime
from ragflow_agent.agent.application.evidence import EvidenceSufficiencyPolicy
from ragflow_agent.agent.application.hitl import ApprovalService
from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.application.planning import QueryPlannerPort
from ragflow_agent.agent.application.tool_policy import (
    SecureToolExecutionService,
    SecureToolRegistry,
)
from ragflow_agent.agent.domain.agentic import (
    AgenticAuthorizationSnapshot,
    AgenticResumeRequest,
    AgenticRunRequest,
    AgenticRunStatus,
    BudgetLimits,
    PlanStep,
    QueryPlan,
    ToolEffect,
    ToolRiskLevel,
)
from ragflow_agent.agent.domain.errors import AgentCheckpointError
from ragflow_agent.agent.graphs.agentic_rag import AgenticRagNodes
from ragflow_agent.agent.ports.agentic import (
    AgentRunRepositoryPort,
    AgentRunTraceMetricsPort,
    RegisteredToolHandler,
)
from ragflow_agent.agent.tools.api import AllowlistedApiTool, ApiEndpoint
from ragflow_agent.agent.tools.knowledge_base import AgentKnowledgeGateway, KnowledgeBaseTool
from ragflow_agent.agent.tools.sql import ReadOnlySqlTool, SqlAllowlist
from ragflow_agent.knowledge.application.fixed_rag import FixedRagService
from ragflow_agent.knowledge.application.knowledge_service import KnowledgeQueryService
from tests.fakes.agentic import (
    EchoKnowledgeQueryService,
    FakeApiTransport,
    FakeRegisteredTool,
    FakeSecretProvider,
    FakeSqlExecutor,
    MemoryAgenticMemoryRepository,
    MemoryAgentRunRepository,
    MemoryApprovalRepository,
)
from tests.fakes.knowledge import FixedClock, SequenceIdGenerator
from tests.fakes.minimum_rag import StubChatProvider


class StaticPlanner:
    def __init__(self, plan: QueryPlan) -> None:
        self._plan = plan

    async def plan(self, question: str) -> QueryPlan:
        del question
        return self._plan


class SlowPlanner:
    uses_model = False

    async def plan(self, question: str) -> QueryPlan:
        del question
        await asyncio.sleep(0.1)
        return QueryPlan(is_simple=True, steps=(PlanStep(step_id="q1", question="slow"),))


class FailingRunRepository:
    async def save(self, trace: object) -> None:
        del trace
        raise RuntimeError("trace store unavailable")

    async def get(self, *, tenant_id: str, run_id: str) -> None:
        del tenant_id, run_id
        raise RuntimeError("trace store unavailable")


class CountingTraceMetrics:
    def __init__(self) -> None:
        self.failures: list[tuple[str, str]] = []

    def record_write_failure(self, *, tenant_id: str, reason: str) -> None:
        self.failures.append((tenant_id, reason))


def _runtime(
    *,
    plan: QueryPlan,
    query: EchoKnowledgeQueryService,
    extra_tool: RegisteredToolHandler | None = None,
    planner: QueryPlannerPort | None = None,
    run_repository: AgentRunRepositoryPort | None = None,
    trace_metrics: AgentRunTraceMetricsPort | None = None,
) -> tuple[AgenticRagRuntime, AgentRunRepositoryPort]:
    ids = SequenceIdGenerator([f"id-{index}" for index in range(1, 50)])
    typed_query = cast(KnowledgeQueryService, query)
    knowledge_tool = KnowledgeBaseTool(typed_query, ids)
    fixed_rag = FixedRagService(
        query_service=typed_query,
        chat_provider=StubChatProvider(),
        chat_model_id="fake-chat",
        id_generator=ids,
    )
    handlers = (knowledge_tool,) if extra_tool is None else (knowledge_tool, extra_tool)
    registry = SecureToolRegistry(handlers)
    tool_execution = SecureToolExecutionService(registry=registry)
    clock = FixedClock(datetime(2026, 7, 31, tzinfo=UTC))
    approvals = ApprovalService(
        repository=MemoryApprovalRepository(),
        tools=tool_execution,
        id_generator=ids,
        clock=clock,
    )
    memory = LongTermMemoryService(
        repository=MemoryAgenticMemoryRepository(),
        id_generator=ids,
        clock=clock,
    )
    runs = run_repository or MemoryAgentRunRepository()
    nodes = AgenticRagNodes(
        planner=planner or StaticPlanner(plan),
        knowledge=AgentKnowledgeGateway(
            knowledge_tool=knowledge_tool,
            fixed_rag=fixed_rag,
        ),
        tools=tool_execution,
        approvals=approvals,
        evidence_policy=EvidenceSufficiencyPolicy(),
    )
    return (
        AgenticRagRuntime(
            nodes=nodes,
            checkpointer=InMemorySaver(),
            approvals=approvals,
            memory=memory,
            runs=runs,
            clock=clock,
            trace_metrics=trace_metrics,
        ),
        runs,
    )


def _request(*, run_id: str = "run-1", thread_id: str = "thread-1") -> AgenticRunRequest:
    return AgenticRunRequest(
        run_id=run_id,
        thread_id=thread_id,
        context=AgenticAuthorizationSnapshot(
            tenant_id="tenant-a",
            user_id="user-a",
            request_id="request-a",
            roles=("reader",),
            knowledge_base_ids=("kb-a",),
        ),
        question="How do I reset the relay?",
    )


@pytest.mark.asyncio
async def test_simple_question_uses_direct_rag_with_versioned_citation() -> None:
    runtime, runs = _runtime(
        plan=QueryPlan(is_simple=True, steps=(PlanStep(step_id="q1", question="reset"),)),
        query=EchoKnowledgeQueryService(),
    )

    result = await runtime.run(_request())

    assert result.state.route == "direct_rag"
    assert result.state.final_status is AgenticRunStatus.COMPLETED
    assert result.state.budget_usage.model_calls == 1
    assert result.state.budget_usage.retrieval_rounds == 1
    assert result.state.citations[0].knowledge is not None
    assert result.state.citations[0].knowledge.document_version_id == "version-1"
    trace = await runs.get(tenant_id="tenant-a", run_id="run-1")
    assert trace is not None
    assert trace.retrieval_trace_ids == result.state.retrieval_trace_ids


@pytest.mark.asyncio
async def test_active_runtime_budget_cancels_graph_before_slow_node_finishes() -> None:
    runtime, _ = _runtime(
        plan=QueryPlan(is_simple=True, steps=(PlanStep(step_id="q1", question="slow"),)),
        query=EchoKnowledgeQueryService(),
        planner=SlowPlanner(),
    )
    request = _request().model_copy(
        update={"budget_limits": BudgetLimits(max_active_runtime_seconds=0.01)}
    )

    result = await runtime.run(request)

    assert result.state.final_status is AgenticRunStatus.BUDGET_EXHAUSTED
    assert result.state.stop_reason == "active_runtime_budget_exhausted"


@pytest.mark.asyncio
async def test_agent_trace_store_failure_is_observable_but_does_not_block_answer() -> None:
    metrics = CountingTraceMetrics()
    runtime, _ = _runtime(
        plan=QueryPlan(is_simple=True, steps=(PlanStep(step_id="q1", question="reset"),)),
        query=EchoKnowledgeQueryService(),
        run_repository=FailingRunRepository(),
        trace_metrics=metrics,
    )

    result = await runtime.run(_request())

    assert result.state.final_status is AgenticRunStatus.COMPLETED
    assert metrics.failures
    assert all(tenant_id == "tenant-a" for tenant_id, _ in metrics.failures)


@pytest.mark.asyncio
async def test_agent_selects_knowledge_tool_and_bounds_multi_step_retrieval() -> None:
    query = EchoKnowledgeQueryService()
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(step_id="q1", question="relay procedure"),
                PlanStep(step_id="q2", question="relay safety limits"),
            ),
        ),
        query=query,
    )

    result = await runtime.run(_request())

    assert result.state.route == "agent"
    assert result.state.final_status is AgenticRunStatus.COMPLETED
    assert result.state.budget_usage.retrieval_rounds == 2
    assert result.state.budget_usage.retrieval_rounds <= 3
    assert len(query.calls) == 2
    assert all(call[0].tenant_id == "tenant-a" for call in query.calls)
    assert all(call[1].knowledge_base_ids == ("kb-a",) for call in query.calls)


@pytest.mark.asyncio
async def test_agent_combines_knowledge_with_tenant_scoped_sql_evidence() -> None:
    executor = FakeSqlExecutor(({"tenant_id": "tenant-a", "order_id": "wo-1"},))
    sql_tool = ReadOnlySqlTool(
        executor=executor,
        allowlist=SqlAllowlist(
            schema_name="public",
            tables={"work_orders": ("tenant_id", "order_id")},
        ),
    )
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(step_id="q1", question="manual procedure"),
                PlanStep(
                    step_id="q2",
                    question="matching work order",
                    preferred_tool="readonly_sql",
                    tool_arguments={
                        "statement": "SELECT order_id FROM public.work_orders",
                        "parameters": {},
                    },
                ),
            ),
        ),
        query=EchoKnowledgeQueryService(),
        extra_tool=sql_tool,
    )

    result = await runtime.run(_request())

    assert result.state.final_status is AgenticRunStatus.COMPLETED
    assert {citation.source_kind for citation in result.state.citations} == {
        "knowledge",
        "sql",
    }
    assert executor.calls[0]["parameters"] == {
        "_agent_tenant_id": "tenant-a",
        "_agent_limit": 200,
    }


@pytest.mark.asyncio
async def test_agent_combines_knowledge_with_allowlisted_api_evidence() -> None:
    transport = FakeApiTransport({"status": "healthy"})
    api_tool = AllowlistedApiTool(
        endpoint=ApiEndpoint(
            tool_name="asset_status_api",
            base_url="https://assets.example.test/",
            path="/v1/status",
        ),
        transport=transport,
        secrets=FakeSecretProvider(),
    )
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(step_id="q1", question="manual procedure"),
                PlanStep(
                    step_id="q2",
                    question="current asset status",
                    preferred_tool="asset_status_api",
                    tool_arguments={"query": {"asset_id": "asset-1"}, "body": None},
                ),
            ),
        ),
        query=EchoKnowledgeQueryService(),
        extra_tool=api_tool,
    )

    result = await runtime.run(_request())

    assert result.state.final_status is AgenticRunStatus.COMPLETED
    assert {citation.source_kind for citation in result.state.citations} == {
        "api",
        "knowledge",
    }
    assert transport.calls[0]["url"] == "https://assets.example.test/v1/status"


@pytest.mark.asyncio
async def test_no_evidence_stops_after_three_retrievals_not_as_system_failure() -> None:
    query = EchoKnowledgeQueryService(empty=True)
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(PlanStep(step_id="q1", question="missing evidence"),),
        ),
        query=query,
    )

    result = await runtime.run(_request())

    assert result.state.final_status is AgenticRunStatus.NO_EVIDENCE
    assert result.state.budget_usage.retrieval_rounds <= 3
    assert len(query.calls) == 1
    assert result.state.tool_calls[-1].status == "reused"


@pytest.mark.asyncio
async def test_high_risk_tool_interrupts_and_resume_is_checkpoint_idempotent() -> None:
    action = FakeRegisteredTool(
        name="high_risk_action",
        output={"result": "done"},
        effect=ToolEffect.SIDE_EFFECTING,
        risk=ToolRiskLevel.HIGH,
        requires_hitl=True,
        approval_roles=("tool-approver",),
    )
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(
                    step_id="q1",
                    question="perform approved operation",
                    preferred_tool="high_risk_action",
                ),
            ),
        ),
        query=EchoKnowledgeQueryService(),
        extra_tool=action,
    )
    paused = await runtime.run(_request())
    assert paused.interrupted
    assert paused.state.final_status is AgenticRunStatus.APPROVAL_REQUIRED
    assert paused.state.approval_id is not None

    resume = AgenticResumeRequest(
        run_id="run-1",
        thread_id="thread-1",
        approval_id=paused.state.approval_id,
        tenant_id="tenant-a",
        approver_id="approver-a",
        approver_request_id="approval-request",
        approver_roles=("tool-approver",),
        decision="approve",
    )
    completed = await runtime.resume(resume)
    repeated = await runtime.resume(resume)

    assert completed.state.final_status is AgenticRunStatus.COMPLETED
    assert repeated.state == completed.state
    assert len(action.calls) == 1
    assert repeated.state.budget_usage == completed.state.budget_usage


@pytest.mark.asyncio
async def test_approval_cannot_be_reused_for_another_run_in_the_same_tenant() -> None:
    action = FakeRegisteredTool(
        name="high_risk_action",
        output={"result": "done"},
        effect=ToolEffect.SIDE_EFFECTING,
        risk=ToolRiskLevel.HIGH,
        requires_hitl=True,
        approval_roles=("tool-approver",),
    )
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(
                    step_id="q1",
                    question="perform approved operation",
                    preferred_tool="high_risk_action",
                ),
            ),
        ),
        query=EchoKnowledgeQueryService(),
        extra_tool=action,
    )
    first = await runtime.run(_request(run_id="run-1", thread_id="thread-1"))
    second = await runtime.run(_request(run_id="run-2", thread_id="thread-2"))
    assert first.state.approval_id is not None

    with pytest.raises(AgentCheckpointError, match="does not belong"):
        await runtime.resume(
            AgenticResumeRequest(
                run_id="run-2",
                thread_id="thread-2",
                approval_id=first.state.approval_id,
                tenant_id="tenant-a",
                approver_id="approver-a",
                approver_request_id="approval-request",
                approver_roles=("tool-approver",),
                decision="approve",
            )
        )

    assert second.state.final_status is AgenticRunStatus.APPROVAL_REQUIRED
    assert action.calls == []


@pytest.mark.asyncio
async def test_conflicting_structured_tool_evidence_is_a_terminal_policy_result() -> None:
    conflict_tool = FakeRegisteredTool(
        name="asset_api",
        output={
            "evidence": [
                {"excerpt": "asset A is active", "fact_key": "asset_state", "stance": "on"},
                {"excerpt": "asset A is inactive", "fact_key": "asset_state", "stance": "off"},
            ]
        },
    )
    runtime, _ = _runtime(
        plan=QueryPlan(
            is_simple=False,
            steps=(
                PlanStep(
                    step_id="q1",
                    question="asset state",
                    preferred_tool="asset_api",
                ),
            ),
        ),
        query=EchoKnowledgeQueryService(),
        extra_tool=conflict_tool,
    )

    result = await runtime.run(_request())

    assert result.state.final_status is AgenticRunStatus.CONFLICTING_EVIDENCE
    assert "conflict" in (result.state.stop_reason or "")


@pytest.mark.asyncio
async def test_checkpoint_state_redacts_secret_like_user_input() -> None:
    runtime, _ = _runtime(
        plan=QueryPlan(is_simple=True, steps=(PlanStep(step_id="q1", question="reset"),)),
        query=EchoKnowledgeQueryService(),
    )
    request = _request().model_copy(
        update={"question": "Reset device with api_key=real-secret-value"}
    )

    result = await runtime.run(request)

    serialized = result.state.model_dump_json()
    assert "real-secret-value" not in serialized
    assert "[REDACTED]" in result.state.question
