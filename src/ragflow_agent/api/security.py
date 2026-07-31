"""Trusted authentication boundary and explicitly local development identity."""

from dataclasses import dataclass
from typing import Protocol

from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from ragflow_agent.shared import AppError


@dataclass(frozen=True, slots=True)
class TrustedIdentity:
    """Identity facts produced by a trusted authentication adapter."""

    tenant_id: str
    subject_id: str
    roles: tuple[str, ...] = ()


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


class DevelopmentIdentityMiddleware:
    """Translate local headers outside production; production still needs an IdP."""

    def __init__(self, app: ASGIApp, *, enabled: bool) -> None:
        self._app = app
        self._enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._enabled and scope["type"] == "http":
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            tenant_id = headers.get("x-tenant-id", "").strip()
            actor_id = headers.get("x-actor-id", "").strip()
            if tenant_id and actor_id:
                roles = tuple(
                    dict.fromkeys(
                        role.strip()
                        for role in headers.get("x-roles", "").split(",")
                        if role.strip()
                    )
                )
                scope.setdefault("state", {})["trusted_identity"] = TrustedIdentity(
                    tenant_id=tenant_id,
                    subject_id=actor_id,
                    roles=roles,
                )
        await self._app(scope, receive, send)
