"""Persistent HITL approval state machine and idempotent resume service."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from enum import StrEnum

from ragflow_agent.agent.application.budgets import BudgetLedger
from ragflow_agent.agent.application.tool_policy import (
    SecureToolExecutionService,
    ToolPolicyAction,
)
from ragflow_agent.agent.domain.agentic import (
    ApprovalRequest,
    ApprovalStatus,
    ToolAuthorizationContext,
    ToolExecutionOutcome,
    ToolInvocation,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.ports.agentic import ApprovalRepositoryPort
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"


class ApprovalService:
    def __init__(
        self,
        *,
        repository: ApprovalRepositoryPort,
        tools: SecureToolExecutionService,
        id_generator: IdGenerator,
        clock: Clock,
        ttl_minutes: int = 30,
    ) -> None:
        self._repository = repository
        self._tools = tools
        self._id_generator = id_generator
        self._clock = clock
        self._ttl = timedelta(minutes=ttl_minutes)

    async def request(
        self,
        *,
        run_id: str,
        thread_id: str,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
        reason: str,
        required_roles: tuple[str, ...],
    ) -> ApprovalRequest:
        now = self._clock.now()
        idempotency_key = hashlib.sha256(
            f"{context.tenant_id}:{run_id}:{invocation.tool_call_id}:{invocation.argument_digest}".encode()
        ).hexdigest()
        existing = await self._repository.get_by_idempotency_key(
            tenant_id=context.tenant_id,
            idempotency_key=idempotency_key,
        )
        if existing is not None:
            return existing
        approval_id = self._id_generator.new_id()
        item = ApprovalRequest(
            approval_id=approval_id,
            run_id=run_id,
            thread_id=thread_id,
            tool_call_id=invocation.tool_call_id,
            tool_name=invocation.tool_name,
            tool_version=invocation.tool_version,
            argument_digest=invocation.argument_digest,
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            reason=reason,
            required_roles=required_roles,
            created_at=now,
            expires_at=now + self._ttl,
            idempotency_key=idempotency_key,
        )
        await self._repository.save(item)
        return item

    async def decide(
        self,
        *,
        approval_id: str,
        context: ToolAuthorizationContext,
        decision: ApprovalDecision,
    ) -> ApprovalRequest:
        item = await self._require(approval_id, context.tenant_id)
        item = await self._expire_if_needed(item)
        if item.status is not ApprovalStatus.APPROVAL_REQUIRED:
            return item
        if decision is ApprovalDecision.CANCEL:
            if context.actor_id != item.user_id and not set(context.roles).intersection(
                item.required_roles
            ):
                raise AgentToolError(
                    "approval cancellation is not authorized",
                    error_code="approval_forbidden",
                    status_code=403,
                )
            status = ApprovalStatus.CANCELLED
        else:
            if not item.required_roles or not set(context.roles).intersection(item.required_roles):
                raise AgentToolError(
                    "approval role is required",
                    error_code="approval_forbidden",
                    status_code=403,
                )
            status = (
                ApprovalStatus.APPROVED
                if decision is ApprovalDecision.APPROVE
                else ApprovalStatus.REJECTED
            )
        updated = item.model_copy(
            update={
                "status": status,
                "decided_by": context.actor_id,
                "decided_at": self._clock.now(),
                "revision": item.revision + 1,
            }
        )
        if not await self._repository.compare_and_set(
            tenant_id=item.tenant_id,
            approval_id=item.approval_id,
            expected_revision=item.revision,
            request=updated,
        ):
            return await self._require(approval_id, context.tenant_id)
        return updated

    async def get_current(self, *, approval_id: str, tenant_id: str) -> ApprovalRequest:
        item = await self._require(approval_id, tenant_id)
        return await self._expire_if_needed(item)

    async def resume(
        self,
        *,
        approval_id: str,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
        budget: BudgetLedger,
    ) -> ToolExecutionOutcome:
        item = await self._require(approval_id, context.tenant_id)
        item = await self._expire_if_needed(item)
        if (
            item.tool_call_id != invocation.tool_call_id
            or item.tool_name != invocation.tool_name
            or item.tool_version != invocation.tool_version
            or item.argument_digest != invocation.argument_digest
        ):
            raise AgentToolError(
                "approval does not match the current Tool call",
                error_code="approval_call_changed",
                status_code=409,
            )
        if item.status is ApprovalStatus.SUCCEEDED and item.result_summary is not None:
            return ToolExecutionOutcome(status="success", summary=item.result_summary)
        if item.status is not ApprovalStatus.APPROVED:
            raise AgentToolError(
                "approval is not executable",
                error_code=f"approval_{item.status.value}",
                status_code=409,
            )
        policy = self._tools.authorize(invocation, context)
        if policy.action is ToolPolicyAction.DENY:
            raise AgentToolError(
                "Tool policy changed after approval",
                error_code="approval_policy_changed",
                status_code=403,
            )
        executing = item.model_copy(
            update={"status": ApprovalStatus.EXECUTING, "revision": item.revision + 1}
        )
        claimed = await self._repository.compare_and_set(
            tenant_id=item.tenant_id,
            approval_id=item.approval_id,
            expected_revision=item.revision,
            request=executing,
        )
        if not claimed:
            current = await self._require(approval_id, context.tenant_id)
            if current.status is ApprovalStatus.SUCCEEDED and current.result_summary is not None:
                return ToolExecutionOutcome(status="success", summary=current.result_summary)
            raise AgentToolError(
                "approval execution is already claimed",
                error_code="approval_execution_conflict",
                status_code=409,
            )
        try:
            outcome = await self._tools.execute(invocation, context, budget, approved=True)
        except Exception:
            failed = executing.model_copy(
                update={"status": ApprovalStatus.FAILED, "revision": executing.revision + 1}
            )
            await self._repository.compare_and_set(
                tenant_id=item.tenant_id,
                approval_id=item.approval_id,
                expected_revision=executing.revision,
                request=failed,
            )
            raise
        succeeded = executing.model_copy(
            update={
                "status": ApprovalStatus.SUCCEEDED,
                "result_summary": outcome.summary,
                "revision": executing.revision + 1,
            }
        )
        if not await self._repository.compare_and_set(
            tenant_id=item.tenant_id,
            approval_id=item.approval_id,
            expected_revision=executing.revision,
            request=succeeded,
        ):
            raise AgentToolError(
                "approval result could not be persisted",
                error_code="approval_result_conflict",
                status_code=409,
            )
        return outcome

    async def _require(self, approval_id: str, tenant_id: str) -> ApprovalRequest:
        item = await self._repository.get(tenant_id=tenant_id, approval_id=approval_id)
        if item is None:
            raise AgentToolError(
                "approval request was not found",
                error_code="approval_not_found",
                status_code=404,
            )
        return item

    async def _expire_if_needed(self, item: ApprovalRequest) -> ApprovalRequest:
        if (
            item.status is not ApprovalStatus.APPROVAL_REQUIRED
            or self._clock.now() < item.expires_at
        ):
            return item
        expired = item.model_copy(
            update={"status": ApprovalStatus.EXPIRED, "revision": item.revision + 1}
        )
        await self._repository.compare_and_set(
            tenant_id=item.tenant_id,
            approval_id=item.approval_id,
            expected_revision=item.revision,
            request=expired,
        )
        return expired
