"""Ports for Phase 08 Tool execution, persistence, SQL, API, and secrets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from ragflow_agent.agent.domain.agentic import (
    AgentRunTrace,
    ApprovalRequest,
    DirectRagAnswer,
    LongTermMemory,
    MemoryConsent,
    ToolAuthorizationContext,
    ToolInvocation,
    ToolRegistration,
)


@runtime_checkable
class RegisteredToolHandler(Protocol):
    @property
    def registration(self) -> ToolRegistration: ...

    async def invoke(
        self,
        invocation: ToolInvocation,
        context: ToolAuthorizationContext,
    ) -> object: ...


@runtime_checkable
class ReadOnlySqlExecutorPort(Protocol):
    async def execute(
        self,
        *,
        statement: str,
        parameters: Mapping[str, object],
        timeout_seconds: float,
        max_rows: int,
    ) -> Sequence[Mapping[str, object]]: ...


@runtime_checkable
class ApiTransportPort(Protocol):
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
    ) -> object: ...


@runtime_checkable
class SecretProviderPort(Protocol):
    async def headers_for(self, credential_ref: str) -> Mapping[str, str]: ...


@runtime_checkable
class ApprovalRepositoryPort(Protocol):
    async def save(self, request: ApprovalRequest) -> None: ...

    async def get(self, *, tenant_id: str, approval_id: str) -> ApprovalRequest | None: ...

    async def get_by_idempotency_key(
        self, *, tenant_id: str, idempotency_key: str
    ) -> ApprovalRequest | None: ...

    async def compare_and_set(
        self,
        *,
        tenant_id: str,
        approval_id: str,
        expected_revision: int,
        request: ApprovalRequest,
    ) -> bool: ...


@runtime_checkable
class MemoryRepositoryPort(Protocol):
    async def save_consent(self, consent: MemoryConsent) -> None: ...

    async def get_consent(self, *, tenant_id: str, user_id: str) -> MemoryConsent | None: ...

    async def save_memory(self, memory: LongTermMemory) -> None: ...

    async def list_memories(
        self,
        *,
        tenant_id: str,
        user_id: str,
    ) -> tuple[LongTermMemory, ...]: ...

    async def delete_memory(
        self,
        *,
        tenant_id: str,
        user_id: str,
        memory_id: str,
    ) -> bool: ...

    async def delete_user_memories(self, *, tenant_id: str, user_id: str) -> int: ...

    async def delete_expired(self, *, before: datetime) -> int: ...


@runtime_checkable
class AgentRunRepositoryPort(Protocol):
    async def save(self, trace: AgentRunTrace) -> None: ...

    async def get(self, *, tenant_id: str, run_id: str) -> AgentRunTrace | None: ...


@runtime_checkable
class AgentRunTraceMetricsPort(Protocol):
    def record_write_failure(self, *, tenant_id: str, reason: str) -> None: ...


@runtime_checkable
class ModelCallBudgetPort(Protocol):
    def begin_model_call(self) -> None: ...


@runtime_checkable
class AgentKnowledgeGatewayPort(Protocol):
    async def direct_answer(
        self,
        *,
        context: ToolAuthorizationContext,
        question: str,
        knowledge_base_ids: tuple[str, ...],
        model_budget: ModelCallBudgetPort,
    ) -> DirectRagAnswer: ...
