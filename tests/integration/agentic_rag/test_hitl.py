from datetime import UTC, datetime, timedelta

import pytest

from ragflow_agent.agent.application.budgets import BudgetLedger
from ragflow_agent.agent.application.hitl import ApprovalDecision, ApprovalService
from ragflow_agent.agent.application.tool_policy import (
    SecureToolExecutionService,
    SecureToolRegistry,
)
from ragflow_agent.agent.domain.agentic import (
    ApprovalStatus,
    BudgetLimits,
    ToolAuthorizationContext,
    ToolEffect,
    ToolInvocation,
    ToolRiskLevel,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from tests.fakes.agentic import FakeRegisteredTool, MemoryApprovalRepository
from tests.fakes.knowledge import FixedClock, SequenceIdGenerator


def _context(*, user: str = "user-a", roles: tuple[str, ...] = ()) -> ToolAuthorizationContext:
    return ToolAuthorizationContext(
        tenant_id="tenant-a", actor_id=user, request_id=f"request-{user}", roles=roles
    )


def _tool() -> FakeRegisteredTool:
    return FakeRegisteredTool(
        effect=ToolEffect.SIDE_EFFECTING,
        risk=ToolRiskLevel.HIGH,
        requires_hitl=True,
        approval_roles=("tool-approver",),
        output={"changed": True},
    )


@pytest.mark.asyncio
async def test_hitl_pause_authorize_parameter_binding_and_idempotent_resume() -> None:
    tool = _tool()
    tools = SecureToolExecutionService(registry=SecureToolRegistry((tool,)))
    repository = MemoryApprovalRepository()
    service = ApprovalService(
        repository=repository,
        tools=tools,
        id_generator=SequenceIdGenerator(["approval-1"]),
        clock=FixedClock(datetime(2026, 7, 31, tzinfo=UTC)),
    )
    invocation = ToolInvocation(
        tool_call_id="call-1", tool_name="fake_action", tool_version="1", arguments={"x": 1}
    )
    paused = await tools.execute(invocation, _context(), BudgetLedger(BudgetLimits()))
    approval = await service.request(
        run_id="run-1",
        thread_id="thread-1",
        invocation=invocation,
        context=_context(),
        reason=paused.approval_reason or "high risk",
        required_roles=paused.required_roles,
    )
    repeated_request = await service.request(
        run_id="run-1",
        thread_id="thread-1",
        invocation=invocation,
        context=_context(),
        reason=paused.approval_reason or "high risk",
        required_roles=paused.required_roles,
    )
    assert approval.status is ApprovalStatus.APPROVAL_REQUIRED
    assert repeated_request == approval

    with pytest.raises(AgentToolError, match="role"):
        await service.decide(
            approval_id="approval-1",
            context=_context(user="intruder"),
            decision=ApprovalDecision.APPROVE,
        )
    await service.decide(
        approval_id="approval-1",
        context=_context(user="approver-a", roles=("tool-approver",)),
        decision=ApprovalDecision.APPROVE,
    )
    changed = invocation.model_copy(update={"arguments": {"x": 2}})
    with pytest.raises(AgentToolError, match="does not match"):
        await service.resume(
            approval_id="approval-1",
            invocation=changed,
            context=_context(),
            budget=BudgetLedger(BudgetLimits()),
        )

    ledger = BudgetLedger(BudgetLimits())
    first = await service.resume(
        approval_id="approval-1", invocation=invocation, context=_context(), budget=ledger
    )
    second = await service.resume(
        approval_id="approval-1", invocation=invocation, context=_context(), budget=ledger
    )
    assert first.summary == second.summary
    assert len(tool.calls) == 1
    assert (
        await service.get_current(approval_id="approval-1", tenant_id="tenant-a")
    ).status is ApprovalStatus.SUCCEEDED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (ApprovalDecision.REJECT, ApprovalStatus.REJECTED),
        (ApprovalDecision.CANCEL, ApprovalStatus.CANCELLED),
    ],
)
async def test_hitl_reject_and_cancel_are_terminal(
    decision: ApprovalDecision, expected: ApprovalStatus
) -> None:
    tools = SecureToolExecutionService(registry=SecureToolRegistry((_tool(),)))
    service = ApprovalService(
        repository=MemoryApprovalRepository(),
        tools=tools,
        id_generator=SequenceIdGenerator(["approval-1"]),
        clock=FixedClock(datetime(2026, 7, 31, tzinfo=UTC)),
    )
    invocation = ToolInvocation(
        tool_call_id="call-1", tool_name="fake_action", tool_version="1", arguments={}
    )
    approval = await service.request(
        run_id="run-1",
        thread_id="thread-1",
        invocation=invocation,
        context=_context(),
        reason="high risk",
        required_roles=("tool-approver",),
    )
    if decision is ApprovalDecision.REJECT:
        actor = _context(roles=("tool-approver",))
    else:
        actor = _context()
    decided = await service.decide(
        approval_id=approval.approval_id, context=actor, decision=decision
    )
    assert decided.status is expected


@pytest.mark.asyncio
async def test_hitl_expires_without_execution() -> None:
    now = datetime(2026, 7, 31, tzinfo=UTC)
    repository = MemoryApprovalRepository()
    tools = SecureToolExecutionService(registry=SecureToolRegistry((_tool(),)))
    service = ApprovalService(
        repository=repository,
        tools=tools,
        id_generator=SequenceIdGenerator(["approval-1"]),
        clock=FixedClock(now),
    )
    invocation = ToolInvocation(
        tool_call_id="call-1", tool_name="fake_action", tool_version="1", arguments={}
    )
    approval = await service.request(
        run_id="run-1",
        thread_id="thread-1",
        invocation=invocation,
        context=_context(),
        reason="high risk",
        required_roles=("tool-approver",),
    )
    expired = approval.model_copy(
        update={"expires_at": now - timedelta(seconds=1), "revision": approval.revision + 1}
    )
    repository.items[("tenant-a", "approval-1")] = expired
    current = await service.get_current(approval_id="approval-1", tenant_id="tenant-a")
    assert current.status is ApprovalStatus.EXPIRED
