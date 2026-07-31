"""Default-deny Tool registry, schema checks, policy, redaction, and execution."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from ragflow_agent.agent.application.budgets import BudgetLedger
from ragflow_agent.agent.application.evidence import contains_prompt_injection
from ragflow_agent.agent.application.sensitive import (
    redact_secret_like_text,
    reject_secret_arguments,
)
from ragflow_agent.agent.domain.agentic import (
    ToolAuthorizationContext,
    ToolCallSummary,
    ToolEffect,
    ToolExecutionOutcome,
    ToolInvocation,
    ToolRegistration,
    ToolRiskLevel,
)
from ragflow_agent.agent.domain.errors import AgentToolError
from ragflow_agent.agent.ports.agentic import RegisteredToolHandler


class ToolPolicyAction(StrEnum):
    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    action: ToolPolicyAction
    reason: str
    required_roles: tuple[str, ...] = ()


class ToolPolicyEngine:
    """Policy is server-owned and evaluated immediately before every call."""

    def evaluate(
        self,
        registration: ToolRegistration,
        context: ToolAuthorizationContext,
        *,
        business_scope: str | None,
    ) -> ToolPolicyDecision:
        if registration.allowed_tenant_ids and context.tenant_id not in set(
            registration.allowed_tenant_ids
        ):
            return ToolPolicyDecision(ToolPolicyAction.DENY, "tenant_not_allowed")
        if registration.allowed_roles and not set(context.roles).intersection(
            registration.allowed_roles
        ):
            return ToolPolicyDecision(ToolPolicyAction.DENY, "role_not_allowed")
        if registration.allowed_business_scopes and business_scope not in set(
            registration.allowed_business_scopes
        ):
            return ToolPolicyDecision(ToolPolicyAction.DENY, "business_scope_not_allowed")
        if (
            registration.requires_hitl
            or registration.effect is ToolEffect.SIDE_EFFECTING
            or registration.risk_level in {ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL}
        ):
            return ToolPolicyDecision(
                ToolPolicyAction.REQUIRE_APPROVAL,
                "high_risk_or_side_effecting",
                registration.approval_roles,
            )
        return ToolPolicyDecision(ToolPolicyAction.ALLOW, "registered_read_only_tool")


class SecureToolRegistry:
    """Exact name/version registry; fabricated names can never resolve."""

    def __init__(self, handlers: tuple[RegisteredToolHandler, ...]) -> None:
        self._handlers: dict[tuple[str, str], RegisteredToolHandler] = {}
        for handler in handlers:
            key = (handler.registration.tool_name, handler.registration.version)
            if key in self._handlers:
                raise ValueError(f"duplicate Tool registration: {key[0]}@{key[1]}")
            self._handlers[key] = handler

    @property
    def registrations(self) -> tuple[ToolRegistration, ...]:
        return tuple(handler.registration for handler in self._handlers.values())

    def resolve(self, name: str, version: str) -> RegisteredToolHandler:
        handler = self._handlers.get((name, version))
        if handler is None:
            raise AgentToolError(
                "Tool is not registered",
                error_code="agent_tool_unknown",
                status_code=403,
                details={"tool_name": name, "tool_version": version},
            )
        return handler


class SecureToolExecutionService:
    """Validate, re-authorize, budget, invoke, redact, and trace one Tool call."""

    def __init__(
        self,
        *,
        registry: SecureToolRegistry,
        policy: ToolPolicyEngine | None = None,
    ) -> None:
        self._registry = registry
        self._policy = policy or ToolPolicyEngine()
        self._completed: dict[tuple[str, str, str], ToolExecutionOutcome] = {}
        self._successful_signatures: dict[tuple[str, str, str, str, str], ToolExecutionOutcome] = {}

    def authorize(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> ToolPolicyDecision:
        handler = self._registry.resolve(invocation.tool_name, invocation.tool_version)
        reject_secret_arguments(invocation.arguments)
        _validate_json_schema(invocation.arguments, handler.registration.input_schema)
        return self._policy.evaluate(
            handler.registration,
            context,
            business_scope=invocation.business_scope,
        )

    async def execute(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
        budget: BudgetLedger,
        *,
        approved: bool = False,
    ) -> ToolExecutionOutcome:
        handler = self._registry.resolve(invocation.tool_name, invocation.tool_version)
        registration = handler.registration
        reject_secret_arguments(invocation.arguments)
        _validate_json_schema(invocation.arguments, registration.input_schema)
        decision = self._policy.evaluate(
            registration,
            context,
            business_scope=invocation.business_scope,
        )
        if decision.action is ToolPolicyAction.DENY:
            raise AgentToolError(
                "Tool policy denied execution",
                error_code="agent_tool_forbidden",
                status_code=403,
                details={"reason": decision.reason, "tool_name": invocation.tool_name},
            )
        completed_key = (context.tenant_id, context.actor_id, invocation.tool_call_id)
        existing = self._completed.get(completed_key)
        if existing is not None:
            if existing.summary.argument_digest != invocation.argument_digest:
                raise AgentToolError(
                    "Tool call ID was reused with different arguments",
                    error_code="agent_tool_call_collision",
                )
            return existing
        signature = (
            context.tenant_id,
            context.actor_id,
            invocation.tool_name,
            invocation.tool_version,
            invocation.argument_digest,
        )
        successful = self._successful_signatures.get(signature)
        if successful is not None:
            reused = successful.model_copy(
                update={
                    "summary": successful.summary.model_copy(
                        update={"tool_call_id": invocation.tool_call_id, "status": "reused"}
                    )
                }
            )
            self._completed[completed_key] = reused
            return reused
        summary = ToolCallSummary(
            tool_call_id=invocation.tool_call_id,
            tool_name=invocation.tool_name,
            tool_version=invocation.tool_version,
            argument_digest=invocation.argument_digest,
            status="approval_required",
        )
        if decision.action is ToolPolicyAction.REQUIRE_APPROVAL and not approved:
            return ToolExecutionOutcome(
                status="approval_required",
                summary=summary,
                approval_reason=decision.reason,
                required_roles=decision.required_roles,
            )
        raw_output: object | None = None
        error_code: str | None = None
        for attempt in range(registration.max_retries + 1):
            budget.consume_tool()
            try:
                async with asyncio.timeout(registration.timeout_seconds):
                    raw_output = await handler.invoke(invocation, context)
                error_code = None
                break
            except AgentToolError:
                raise
            except TimeoutError:
                error_code = "agent_tool_timeout"
            except Exception:
                error_code = "agent_tool_failed"
            if attempt >= registration.max_retries:
                break
        if error_code is not None:
            failed = ToolExecutionOutcome(
                status="failed",
                summary=summary.model_copy(
                    update={"status": "failed", "error_code": error_code}
                ),
            )
            self._completed[completed_key] = failed
            return failed
        safe_output = _redact(raw_output, frozenset(registration.sensitive_fields))
        _validate_json_schema(safe_output, registration.output_schema)
        serialized = json.dumps(safe_output, sort_keys=True, default=str, separators=(",", ":"))
        if len(serialized.encode("utf-8")) > registration.max_output_bytes:
            raise AgentToolError(
                "Tool response exceeded the configured size limit",
                error_code="agent_tool_output_too_large",
            )
        injection = contains_prompt_injection(serialized)
        outcome = ToolExecutionOutcome(
            status="success",
            summary=summary.model_copy(
                update={
                    "status": "success",
                    "output_digest": hashlib.sha256(serialized.encode()).hexdigest(),
                }
            ),
            output=safe_output,
            injection_detected=injection,
        )
        self._completed[completed_key] = outcome
        self._successful_signatures[signature] = outcome
        return outcome


def _validate_json_schema(value: object, schema: dict[str, object]) -> None:
    """Validate the deliberately small JSON-Schema subset used by registered Tools."""
    if not schema:
        return
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            raise AgentToolError("Tool arguments do not match Schema", error_code="tool_schema")
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            raise ValueError("Tool registry contains an invalid properties Schema")
        required = schema.get("required", [])
        if not isinstance(required, list):
            raise ValueError("Tool registry contains an invalid required Schema")
        missing = [name for name in required if name not in value]
        if missing:
            raise AgentToolError(
                "Tool arguments are missing required fields",
                error_code="tool_schema",
                details={"missing": missing},
            )
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                raise AgentToolError(
                    "Tool arguments contain unknown fields",
                    error_code="tool_schema",
                    details={"fields": sorted(extras)},
                )
        for key, child in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                _validate_json_schema(child, child_schema)
        return
    checks = {
        "string": lambda item: isinstance(item, str),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "array": lambda item: isinstance(item, (list, tuple)),
    }
    check = checks.get(str(expected_type))
    if check is not None and not check(value):
        raise AgentToolError("Tool value does not match Schema", error_code="tool_schema")


def _redact(value: object, sensitive_fields: frozenset[str]) -> object:
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]"
            if str(key).lower() in {name.lower() for name in sensitive_fields}
            else _redact(child, sensitive_fields)
            for key, child in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(child, sensitive_fields) for child in value]
    if isinstance(value, str):
        return redact_secret_like_text(value)
    return value
