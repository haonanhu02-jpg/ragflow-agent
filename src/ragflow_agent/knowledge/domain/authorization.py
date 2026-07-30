"""First-version tenant, owner, and visibility authorization contracts."""

from enum import StrEnum

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


class ResourceAuthorization(KnowledgeModel):
    """Authorization attributes carried by every protected aggregate."""

    tenant_id: NonEmptyStr
    owner_id: NonEmptyStr
    visibility: Visibility


class PermissionDecision(KnowledgeModel):
    """Auditable allow or deny result with a stable reason code."""

    allowed: bool
    reason_code: NonEmptyStr
