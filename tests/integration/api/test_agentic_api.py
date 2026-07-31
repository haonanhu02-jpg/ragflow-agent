from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine

from ragflow_agent.agent.application.agentic_runtime import AgenticRagRuntime
from ragflow_agent.agent.application.memory import LongTermMemoryService
from ragflow_agent.agent.application.tool_policy import SecureToolRegistry
from ragflow_agent.agent.domain.agentic import (
    AgenticRunRequest,
    AgenticRunResult,
    AgenticRunStatus,
    AgenticState,
    LongTermMemory,
    MemoryConsent,
    ToolAuthorizationContext,
)
from ragflow_agent.agent.runtime import AgenticRuntimeBundle
from ragflow_agent.api import create_app
from ragflow_agent.config import AppSettings, DatabaseSettings
from ragflow_agent.knowledge.runtime import MinimumRagRuntime


class FakeAgenticRuntime:
    def __init__(self) -> None:
        self.last_request: AgenticRunRequest | None = None
        self.result: AgenticRunResult | None = None

    async def run(self, request: AgenticRunRequest) -> AgenticRunResult:
        self.last_request = request
        self.result = AgenticRunResult(
            state=AgenticState(
                run_id=request.run_id,
                thread_id=request.thread_id,
                request_id=request.context.request_id,
                authorization=request.context,
                question=request.question,
                route="direct_rag",
                final_status=AgenticRunStatus.NO_EVIDENCE,
                stop_reason="no authorized eligible evidence",
            )
        )
        return self.result

    async def get(self, *, tenant_id: str, thread_id: str, run_id: str) -> AgenticRunResult:
        assert self.result is not None
        assert self.result.state.authorization.tenant_id == tenant_id
        assert self.result.state.thread_id == thread_id
        assert self.result.state.run_id == run_id
        return self.result


class FakeMemory:
    def __init__(self) -> None:
        self.items: list[LongTermMemory] = []

    async def set_consent(
        self, context: ToolAuthorizationContext, *, enabled: bool, consent_version: str
    ) -> MemoryConsent:
        return MemoryConsent(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            enabled=enabled,
            consent_version=consent_version if enabled else None,
            consented_at=datetime(2026, 7, 31, tzinfo=UTC) if enabled else None,
        )

    async def remember(
        self,
        context: ToolAuthorizationContext,
        *,
        content: str,
        source: str,
        explicit_user_request: bool,
    ) -> LongTermMemory:
        assert explicit_user_request
        now = datetime(2026, 7, 31, tzinfo=UTC)
        item = LongTermMemory(
            memory_id="memory-1",
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            content=content,
            source=source,
            consent_version="v1",
            consented_at=now,
            created_at=now,
            expires_at=now + timedelta(days=90),
        )
        self.items.append(item)
        return item

    async def list_active(self, context: ToolAuthorizationContext) -> tuple[LongTermMemory, ...]:
        return tuple(
            item
            for item in self.items
            if item.tenant_id == context.tenant_id and item.user_id == context.actor_id
        )

    async def delete(self, context: ToolAuthorizationContext, memory_id: str) -> bool:
        before = len(self.items)
        self.items = [
            item
            for item in self.items
            if not (
                item.tenant_id == context.tenant_id
                and item.user_id == context.actor_id
                and item.memory_id == memory_id
            )
        ]
        return len(self.items) != before


class ShellMinimumRuntime:
    def __init__(self) -> None:
        self.engine = cast(AsyncEngine, object())

    async def open(self) -> None: ...

    async def close(self) -> None: ...


async def _ready(engine: AsyncEngine) -> bool:
    del engine
    return True


@pytest.fixture
def agentic_client() -> Iterator[tuple[TestClient, FakeAgenticRuntime]]:
    runtime = FakeAgenticRuntime()
    memory = FakeMemory()
    bundle = AgenticRuntimeBundle(
        runtime=cast(AgenticRagRuntime, runtime),
        memory=cast(LongTermMemoryService, memory),
        tools=SecureToolRegistry(()),
    )
    settings = AppSettings(
        database=DatabaseSettings(url=SecretStr("postgresql+psycopg://test:test@localhost/test"))
    )
    app = create_app(
        settings,
        readiness_probe=_ready,
        minimum_rag_runtime=cast(MinimumRagRuntime, ShellMinimumRuntime()),
        agentic_runtime_bundle=bundle,
    )
    with TestClient(app) as client:
        yield client, runtime


def test_agentic_api_injects_identity_and_server_budget(
    agentic_client: tuple[TestClient, FakeAgenticRuntime],
) -> None:
    client, runtime = agentic_client
    response = client.post(
        "/v1/agentic-rag/runs",
        headers={"x-tenant-id": "tenant-a", "x-actor-id": "user-a", "x-roles": "reader"},
        json={"question": "What is the reset procedure?", "knowledge_base_ids": ["kb-a"]},
    )

    assert response.status_code == 201
    assert runtime.last_request is not None
    assert runtime.last_request.context.tenant_id == "tenant-a"
    assert runtime.last_request.context.user_id == "user-a"
    assert runtime.last_request.context.knowledge_base_ids == ("kb-a",)
    assert runtime.last_request.budget_limits.max_retrieval_rounds == 3
    assert runtime.last_request.model_provider_ids == ("chat:deepseek-chat",)


def test_memory_api_requires_explicit_true_and_scopes_to_identity(
    agentic_client: tuple[TestClient, FakeAgenticRuntime],
) -> None:
    client, _ = agentic_client
    headers = {"x-tenant-id": "tenant-a", "x-actor-id": "user-a"}
    invalid = client.post(
        "/v1/agentic-rag/memory",
        headers=headers,
        json={"content": "Use metric units", "source": "user", "explicit_user_request": False},
    )
    created = client.post(
        "/v1/agentic-rag/memory",
        headers=headers,
        json={"content": "Use metric units", "source": "user", "explicit_user_request": True},
    )
    listed = client.get("/v1/agentic-rag/memory", headers=headers)

    assert invalid.status_code == 422
    assert created.status_code == 201
    assert listed.json()[0]["tenant_id"] == "tenant-a"
    assert listed.json()[0]["user_id"] == "user-a"
