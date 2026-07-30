"""Trusted authentication boundary placeholder.

Phase 01 does not trust tenant or owner identifiers supplied directly by an
HTTP caller. A future authentication adapter must resolve them and attach a
TrustedIdentity before Phase 03 creates AuthorizationContext.
"""

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request

from ragflow_agent.shared import AppError


@dataclass(frozen=True, slots=True)
class TrustedIdentity:
    """Identity facts produced by a trusted authentication adapter."""

    tenant_id: str
    subject_id: str


class TrustedIdentityResolver(Protocol):
    """Resolve authenticated identity without coupling routes to an IdP SDK."""

    async def resolve(self, request: Request) -> TrustedIdentity: ...


def require_trusted_identity(request: Request) -> TrustedIdentity:
    """Read identity only from trusted server-side request state."""
    identity = getattr(request.state, "trusted_identity", None)
    if not isinstance(identity, TrustedIdentity):
        raise AppError(
            "authenticated identity is required",
            error_code="authentication_required",
            status_code=401,
        )
    return identity
