"""Fail-closed first-version tenant, owner, and visibility policy."""

from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    PermissionAction,
    PermissionDecision,
    ResourceAuthorization,
    Visibility,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError


class DefaultPermissionChecker:
    """Implement the minimal policy while leaving complex ACL behind the port."""

    def check(
        self,
        context: AuthorizationContext,
        resource: ResourceAuthorization,
        action: PermissionAction,
    ) -> PermissionDecision:
        if context.tenant_id != resource.tenant_id:
            return PermissionDecision(allowed=False, reason_code="tenant_mismatch")
        if context.actor_id == resource.owner_id:
            return PermissionDecision(allowed=True, reason_code="owner_allowed")
        if resource.visibility is Visibility.TENANT and action is PermissionAction.READ:
            return PermissionDecision(allowed=True, reason_code="tenant_read_allowed")
        if resource.visibility is Visibility.PRIVATE:
            return PermissionDecision(allowed=False, reason_code="private_owner_required")
        return PermissionDecision(allowed=False, reason_code="owner_write_required")

    def require(
        self,
        context: AuthorizationContext,
        resource: ResourceAuthorization,
        action: PermissionAction,
    ) -> None:
        decision = self.check(context, resource, action)
        if not decision.allowed:
            raise KnowledgeAuthorizationError(
                reason_code=decision.reason_code,
                trace_id=context.request_id,
                details={
                    "action": action.value,
                    "tenant_id": context.tenant_id,
                },
            )
