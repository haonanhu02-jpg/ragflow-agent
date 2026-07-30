"""Versioned Agent trace events with conservative payload redaction."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ragflow_agent.agent.domain.state import AgentRunIdentity

REDACTED = "[REDACTED]"
SENSITIVE_EVENT_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "document_text",
        "password",
        "private_key",
        "secret",
        "token",
    }
)


class AgentEventType(StrEnum):
    RUN_STARTED = "run_started"
    RUN_RESUMED = "run_resumed"
    CHECKPOINT_RESTORED = "checkpoint_restored"
    NODE_COMPLETED = "node_completed"
    MODEL_COMPLETED = "model_completed"
    TOOL_COMPLETED = "tool_completed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_CANCELLED = "run_cancelled"


class AgentEvent(BaseModel):
    """Safe event envelope emitted to realtime and durable sinks."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    VERSION: ClassVar[int] = 1

    version: int = 1
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    event_type: AgentEventType
    tenant_id: str
    thread_id: str
    run_id: str
    trace_id: str
    request_id: str
    sequence: int = Field(ge=0)
    node: str | None = None
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, object] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: AgentEventType,
        identity: AgentRunIdentity,
        *,
        sequence: int,
        node: str | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> AgentEvent:
        return cls(
            event_type=event_type,
            tenant_id=identity.authorization.tenant_id,
            thread_id=identity.thread_id,
            run_id=identity.run_id,
            trace_id=identity.trace_id,
            request_id=identity.authorization.request_id,
            sequence=sequence,
            node=node,
            payload=redact_event_payload(payload or {}),
        )


def redact_event_payload(value: Mapping[str, object]) -> dict[str, object]:
    """Redact forbidden keys recursively without retaining original values."""

    def redact(item: object) -> object:
        if isinstance(item, Mapping):
            cleaned: dict[str, object] = {}
            for raw_key, child in item.items():
                key = str(raw_key)
                lowered = key.lower()
                cleaned[key] = REDACTED if lowered in SENSITIVE_EVENT_KEYS else redact(child)
            return cleaned
        if isinstance(item, (list, tuple)):
            return [redact(child) for child in item]
        return item

    redacted = redact(dict(value))
    if not isinstance(redacted, dict):
        raise TypeError("event payload redaction must preserve a mapping")
    return redacted
