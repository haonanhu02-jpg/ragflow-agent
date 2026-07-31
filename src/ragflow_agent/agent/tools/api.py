"""Allowlisted API Tool with fixed endpoint, Schema, credential, and size policy."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ragflow_agent.agent.domain.agentic import (
    ToolAuthorizationContext,
    ToolEffect,
    ToolInvocation,
    ToolRegistration,
    ToolRiskLevel,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.ports.agentic import ApiTransportPort, SecretProviderPort


class ApiToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    query: dict[str, object] = Field(default_factory=dict)
    body: object | None = None


class ApiEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: str
    version: str = "1"
    base_url: str
    path: str
    method: str = "GET"
    read_only: bool = True
    credential_ref: str | None = None
    input_schema: dict[str, object] = Field(default_factory=ApiToolInput.model_json_schema)
    output_schema: dict[str, object] = Field(default_factory=dict)
    allowed_roles: tuple[str, ...] = ()
    approval_roles: tuple[str, ...] = ("tool-approver",)
    sensitive_fields: tuple[str, ...] = ()

    @field_validator("base_url")
    @classmethod
    def base_url_is_fixed_http_origin(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("API base URL must be an absolute HTTP(S) origin")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("API base URL cannot contain credentials, query, or fragment")
        return value.rstrip("/") + "/"

    @field_validator("path")
    @classmethod
    def path_is_static(cls, value: str) -> str:
        if not value.startswith("/") or "://" in value or ".." in value or "{" in value:
            raise ValueError("API path must be a fixed absolute path")
        return value

    @field_validator("method")
    @classmethod
    def method_is_explicit(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"GET", "HEAD", "POST"}:
            raise ValueError("API method must be explicitly supported")
        return normalized


class AllowlistedApiTool:
    def __init__(
        self,
        *,
        endpoint: ApiEndpoint,
        transport: ApiTransportPort,
        secrets: SecretProviderPort,
        connect_timeout_seconds: float = 5,
        read_timeout_seconds: float = 15,
        max_response_bytes: int = 1_000_000,
    ) -> None:
        if endpoint.method == "POST" and not endpoint.read_only:
            effect = ToolEffect.SIDE_EFFECTING
            risk = ToolRiskLevel.HIGH
            requires_hitl = True
        else:
            effect = ToolEffect.READ_ONLY
            risk = ToolRiskLevel.MEDIUM
            requires_hitl = False
        self._endpoint = endpoint
        self._transport = transport
        self._secrets = secrets
        self._connect_timeout = connect_timeout_seconds
        self._read_timeout = read_timeout_seconds
        self._max_response_bytes = max_response_bytes
        self._registration = ToolRegistration(
            tool_name=endpoint.tool_name,
            version=endpoint.version,
            description=f"Call allowlisted {endpoint.method} {endpoint.path}",
            input_schema=endpoint.input_schema,
            output_schema=endpoint.output_schema,
            effect=effect,
            risk_level=risk,
            allowed_roles=endpoint.allowed_roles,
            approval_roles=endpoint.approval_roles if requires_hitl else (),
            timeout_seconds=read_timeout_seconds,
            max_retries=1 if endpoint.read_only else 0,
            max_output_bytes=max_response_bytes,
            idempotent=endpoint.read_only,
            requires_hitl=requires_hitl,
            sensitive_fields=endpoint.sensitive_fields,
        )

    @property
    def registration(self) -> ToolRegistration:
        return self._registration

    async def invoke(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> object:
        payload = ApiToolInput.model_validate(invocation.arguments)
        url = urljoin(self._endpoint.base_url, self._endpoint.path.lstrip("/"))
        expected_origin = urlparse(self._endpoint.base_url)
        actual = urlparse(url)
        if (actual.scheme, actual.netloc) != (expected_origin.scheme, expected_origin.netloc):
            raise AgentToolError(
                "API URL escaped its registered origin",
                error_code="api_url_denied",
            )
        headers = {
            "x-tenant-id": context.tenant_id,
            "x-actor-id": context.actor_id,
            "x-request-id": context.request_id,
        }
        if self._endpoint.credential_ref:
            headers.update(await self._secrets.headers_for(self._endpoint.credential_ref))
        try:
            return await self._transport.request(
                method=self._endpoint.method,
                url=url,
                headers=headers,
                query=payload.query,
                body=payload.body,
                connect_timeout_seconds=self._connect_timeout,
                read_timeout_seconds=self._read_timeout,
                max_response_bytes=self._max_response_bytes,
            )
        except AgentToolError:
            raise
        except Exception as exc:
            raise AgentToolError(
                "allowlisted API request failed",
                error_code="api_request_failed",
                status_code=502,
                details={"exception_type": type(exc).__name__},
            ) from exc
