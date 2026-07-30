"""AuthorizationContext and first-version PermissionChecker tests."""

import pytest
from pydantic import ValidationError

from ragflow_agent.knowledge.application.permission_service import (
    DefaultPermissionChecker,
)
from ragflow_agent.knowledge.domain.authorization import (
    AuthorizationContext,
    PermissionAction,
    ResourceAuthorization,
    Visibility,
)
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError


def _context(*, tenant_id: str = "tenant-a", actor_id: str = "owner-a") -> AuthorizationContext:
    return AuthorizationContext(
        tenant_id=tenant_id,
        actor_id=actor_id,
        request_id="request-1",
    )


def _resource(
    *,
    tenant_id: str = "tenant-a",
    owner_id: str = "owner-a",
    visibility: Visibility = Visibility.PRIVATE,
) -> ResourceAuthorization:
    return ResourceAuthorization(
        tenant_id=tenant_id,
        owner_id=owner_id,
        visibility=visibility,
    )


def test_authorization_context_rejects_blank_trusted_identity() -> None:
    with pytest.raises(ValidationError):
        AuthorizationContext(tenant_id=" ", actor_id="actor", request_id="request")


@pytest.mark.parametrize("action", list(PermissionAction))
def test_owner_is_allowed_inside_the_same_tenant(action: PermissionAction) -> None:
    decision = DefaultPermissionChecker().check(_context(), _resource(), action)

    assert decision.allowed is True
    assert decision.reason_code == "owner_allowed"


def test_cross_tenant_owner_is_always_denied() -> None:
    checker = DefaultPermissionChecker()
    context = _context(tenant_id="tenant-b", actor_id="owner-a")

    decision = checker.check(context, _resource(), PermissionAction.READ)

    assert decision.allowed is False
    assert decision.reason_code == "tenant_mismatch"
    with pytest.raises(KnowledgeAuthorizationError) as captured:
        checker.require(context, _resource(), PermissionAction.READ)
    assert captured.value.error_code == "tenant_mismatch"


def test_private_resource_requires_owner() -> None:
    decision = DefaultPermissionChecker().check(
        _context(actor_id="member-a"),
        _resource(),
        PermissionAction.READ,
    )

    assert decision.allowed is False
    assert decision.reason_code == "private_owner_required"


def test_tenant_resource_allows_read_but_not_write_for_non_owner() -> None:
    checker = DefaultPermissionChecker()
    context = _context(actor_id="member-a")
    resource = _resource(visibility=Visibility.TENANT)

    assert checker.check(context, resource, PermissionAction.READ).allowed is True
    denied = checker.check(context, resource, PermissionAction.WRITE)
    assert denied.allowed is False
    assert denied.reason_code == "owner_write_required"
