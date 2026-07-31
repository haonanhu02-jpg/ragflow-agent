"""HTTP and environment-secret adapters for registered API Tools."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping

import httpx

from ragflow_agent.agent.domain.errors import AgentToolError


class EnvironmentSecretProvider:
    """Resolve configured credential references without returning env names to the model."""

    def __init__(self, credential_environment: Mapping[str, str]) -> None:
        self._credential_environment = dict(credential_environment)

    async def headers_for(self, credential_ref: str) -> Mapping[str, str]:
        environment_name = self._credential_environment.get(credential_ref)
        if environment_name is None:
            raise AgentToolError(
                "API credential is not configured",
                error_code="api_credential_missing",
            )
        value = os.environ.get(environment_name)
        if not value:
            raise AgentToolError(
                "API credential is unavailable",
                error_code="api_credential_missing",
            )
        return {"authorization": f"Bearer {value}"}


class HttpxApiTransport:
    """No-redirect transport with bounded response reads."""

    async def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        query: Mapping[str, object],
        body: object | None,
        connect_timeout_seconds: float,
        read_timeout_seconds: float,
        max_response_bytes: int,
    ) -> object:
        timeout = httpx.Timeout(
            connect=connect_timeout_seconds,
            read=read_timeout_seconds,
            write=read_timeout_seconds,
            pool=connect_timeout_seconds,
        )
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.request(
                method,
                url,
                headers=dict(headers),
                params={key: str(value) for key, value in query.items()},
                json=body,
            )
        if 300 <= response.status_code < 400:
            raise AgentToolError(
                "API redirects are forbidden",
                error_code="api_redirect_denied",
            )
        if response.status_code >= 400:
            raise AgentToolError(
                "API returned an error",
                error_code="api_upstream_error",
                status_code=502,
                details={"upstream_status": response.status_code},
            )
        if len(response.content) > max_response_bytes:
            raise AgentToolError(
                "API response is too large",
                error_code="api_response_too_large",
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise AgentToolError(
                "API response is not valid JSON",
                error_code="api_response_invalid",
            ) from exc
