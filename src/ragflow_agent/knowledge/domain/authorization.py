"""First-version tenant, owner, and visibility authorization contracts."""

from enum import StrEnum

from pydantic import field_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class Visibility(StrEnum):
    """Supported Phase 03 resource visibility values."""

    PRIVATE = "private"
    TENANT = "tenant"


class PermissionAction(StrEnum):
    """Stable actions evaluated by the first-version PermissionChecker."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    MANAGE = "manage"


class AuthorizationContext(KnowledgeModel):
    """Trusted request identity propagated to every knowledge boundary."""

    tenant_id: NonEmptyStr
    actor_id: NonEmptyStr
    request_id: NonEmptyStr
    roles: tuple[NonEmptyStr, ...] = ()

    @field_validator("roles")
    @classmethod
    def roles_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("authorization roles must be unique")
        return value


class ResourceAuthorization(KnowledgeModel):
    """Authorization attributes carried by every protected aggregate."""

    tenant_id: NonEmptyStr
    owner_id: NonEmptyStr
    visibility: Visibility


class PermissionDecision(KnowledgeModel):
    """Auditable allow or deny result with a stable reason code."""

    allowed: bool
    reason_code: NonEmptyStr
