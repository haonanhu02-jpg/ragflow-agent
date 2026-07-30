"""Versioned, checkpoint-safe Agent state and request contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import ClassVar, Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ragflow_agent.agent.domain.errors import AgentCheckpointError, AgentStateVersionError

AGENT_STATE_VERSION = 1
CHECKPOINT_FORBIDDEN_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization_header",
        "cookie",
        "password",
        "private_key",
        "secret",
    }
)


class FrozenModel(BaseModel):
    """Immutable strict DTO base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AgentAuthorizationContext(FrozenModel):
    """Minimal trusted identity snapshot carried through Phase 02 checkpoints.

    Phase 03 will add PermissionChecker and the shared knowledge authorization
    contract. This snapshot deliberately contains no roles or ACL decisions.
    """

    tenant_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)


class AgentRunIdentity(FrozenModel):
    """Stable thread/run/trace identity used for checkpoint and event correlation."""

    authorization: AgentAuthorizationContext
    thread_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)


class AgentResumeToken(FrozenModel):
    """Tenant-bound resume capability without credentials or serialized state."""

    tenant_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)

    @classmethod
    def from_identity(cls, identity: AgentRunIdentity) -> AgentResumeToken:
        return cls(
            tenant_id=identity.authorization.tenant_id,
            thread_id=identity.thread_id,
            run_id=identity.run_id,
        )

    def validate_identity(self, identity: AgentRunIdentity) -> None:
        actual = (
            identity.authorization.tenant_id,
            identity.thread_id,
            identity.run_id,
        )
        expected = (self.tenant_id, self.thread_id, self.run_id)
        if actual != expected:
            raise AgentCheckpointError(
                "resume identity does not own the requested thread",
                error_code="agent_checkpoint_access_denied",
            )


class AgentMessage(FrozenModel):
    """Provider-neutral message safe for deterministic checkpoint serialization."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: str | None = None
    tool_call_id: str | None = None

    @model_validator(mode="after")
    def validate_tool_fields(self) -> AgentMessage:
        if self.role == "tool" and (not self.name or not self.tool_call_id):
            raise ValueError("tool messages require name and tool_call_id")
        return self


class ToolCall(FrozenModel):
    """Stable, idempotency-aware Tool request."""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, object] = Field(default_factory=dict)

    @field_validator("arguments")
    @classmethod
    def arguments_are_json_serializable(cls, value: dict[str, object]) -> dict[str, object]:
        _ensure_json_serializable(value)
        _ensure_checkpoint_safe(value)
        return value


class ToolExecutionResult(FrozenModel):
    """Structured Tool success or failure returned to the model."""

    call_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal["success", "error"]
    output: object | None = None
    error_code: str | None = None
    error_message: str | None = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> ToolExecutionResult:
        if self.status == "success" and (self.error_code or self.error_message):
            raise ValueError("successful Tool results cannot contain errors")
        if self.status == "error" and (not self.error_code or not self.error_message):
            raise ValueError("failed Tool results require error_code and error_message")
        _ensure_json_serializable(self.output)
        _ensure_checkpoint_safe(self.output)
        return self


class ModelDecision(FrozenModel):
    """Structured decision produced by an Agent model adapter."""

    kind: Literal["final", "tool"]
    content: str | None = None
    tool_name: str | None = None
    tool_arguments: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_decision(self) -> ModelDecision:
        if self.kind == "final" and not self.content:
            raise ValueError("final decisions require content")
        if self.kind == "tool" and not self.tool_name:
            raise ValueError("Tool decisions require tool_name")
        if self.kind == "final" and (self.tool_name or self.tool_arguments):
            raise ValueError("final decisions cannot contain Tool fields")
        _ensure_json_serializable(self.tool_arguments)
        _ensure_checkpoint_safe(self.tool_arguments)
        return self


class AgentState(FrozenModel):
    """AgentState v1 persisted by the LangGraph Checkpointer."""

    VERSION: ClassVar[int] = AGENT_STATE_VERSION

    version: Literal[1] = 1
    identity: AgentRunIdentity
    messages: tuple[AgentMessage, ...]
    route: Literal["undecided", "tool", "final"] = "undecided"
    pending_tool_call: ToolCall | None = None
    tool_results: tuple[ToolExecutionResult, ...] = ()
    current_node: str = "created"
    step_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    final_answer: str | None = None
    error_code: str | None = None
    termination_reason: Literal["completed", "failed"] | None = None
    event_sequence: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_terminal_state(self) -> AgentState:
        if self.termination_reason == "completed" and not self.final_answer:
            raise ValueError("completed state requires final_answer")
        if self.route == "tool" and self.pending_tool_call is None:
            raise ValueError("Tool route requires pending_tool_call")
        return self

    @classmethod
    def initial(cls, identity: AgentRunIdentity, user_input: str) -> AgentState:
        if not user_input.strip():
            raise ValueError("user_input must not be empty")
        return cls(
            identity=identity,
            messages=(AgentMessage(role="user", content=user_input.strip()),),
        )

    def checkpoint_payload(self) -> dict[str, object]:
        payload = cast(dict[str, object], self.model_dump(mode="json"))
        _ensure_checkpoint_safe(payload)
        return payload


class AgentGraphState(TypedDict):
    """LangGraph channel schema mirroring AgentState v1."""

    version: int
    identity: dict[str, object]
    messages: list[dict[str, object]]
    route: str
    pending_tool_call: dict[str, object] | None
    tool_results: list[dict[str, object]]
    current_node: str
    step_count: int
    retry_count: int
    final_answer: str | None
    error_code: str | None
    termination_reason: str | None
    event_sequence: int


class AgentRunRequest(FrozenModel):
    """Start a new deterministic Agent run."""

    identity: AgentRunIdentity
    user_input: str = Field(min_length=1)


class AgentResumeRequest(FrozenModel):
    """Resume a failed or interrupted run from its durable checkpoint."""

    identity: AgentRunIdentity
    resume_token: AgentResumeToken

    @model_validator(mode="after")
    def token_matches_identity(self) -> AgentResumeRequest:
        self.resume_token.validate_identity(self.identity)
        return self


class AgentRunResult(FrozenModel):
    """Successful Agent runtime outcome."""

    state: AgentState
    trace_degraded: bool = False

    @property
    def answer(self) -> str:
        if self.state.final_answer is None:
            raise AgentCheckpointError("completed run has no final answer")
        return self.state.final_answer


def graph_state_from_model(state: AgentState) -> AgentGraphState:
    """Convert the validated domain state to LangGraph's primitive channel map."""
    return cast(AgentGraphState, state.checkpoint_payload())


def model_from_graph_state(raw: Mapping[str, object]) -> AgentState:
    """Validate and migrate a state restored from a checkpoint."""
    migrated = migrate_state_payload(raw)
    return AgentState.model_validate(migrated)


def migrate_state_payload(raw: Mapping[str, object]) -> dict[str, object]:
    """Migrate known historical payloads and reject unknown future versions."""
    payload = dict(raw)
    version = payload.get("version")
    if version == AGENT_STATE_VERSION:
        return payload
    if version == 0:
        payload["version"] = AGENT_STATE_VERSION
        payload.setdefault("route", "undecided")
        payload.setdefault("pending_tool_call", None)
        payload.setdefault("tool_results", [])
        payload.setdefault("current_node", "migrated")
        payload.setdefault("step_count", 0)
        payload.setdefault("retry_count", 0)
        payload.setdefault("final_answer", None)
        payload.setdefault("error_code", None)
        payload.setdefault("termination_reason", None)
        payload.setdefault("event_sequence", 0)
        return payload
    raise AgentStateVersionError(version)


def checkpoint_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Extract Agent channels from a raw LangGraph checkpoint."""
    allowed = AgentGraphState.__required_keys__
    return {key: value for key, value in raw.items() if key in allowed}


def _ensure_json_serializable(value: object) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("checkpoint value must be JSON serializable") from exc


def _ensure_checkpoint_safe(value: object, path: Sequence[str] = ()) -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).lower()
            if key in CHECKPOINT_FORBIDDEN_KEYS or key.endswith("_secret"):
                location = ".".join((*path, str(raw_key)))
                raise ValueError(f"secret-like field is not checkpoint-safe: {location}")
            _ensure_checkpoint_safe(item, (*path, str(raw_key)))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _ensure_checkpoint_safe(item, (*path, str(index)))
