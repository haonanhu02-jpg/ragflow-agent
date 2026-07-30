"""Permission evaluation boundary for every protected knowledge operation."""

from typing import Protocol, runtime_checkable

from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    PermissionAction,
    PermissionDecision,
    ResourceAuthorization,
)


@runtime_checkable
class PermissionChecker(Protocol):
    """Evaluate access without exposing policy implementation details."""

    def check(
        self,
        context: AuthorizationContext,
        resource: ResourceAuthorization,
        action: PermissionAction,
    ) -> PermissionDecision: ...

    def require(
        self,
        context: AuthorizationContext,
        resource: ResourceAuthorization,
        action: PermissionAction,
    ) -> None: ...
