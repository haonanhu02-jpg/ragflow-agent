"""Consent-first, tenant-and-user scoped long-term memory governance."""

from __future__ import annotations

import re
from datetime import timedelta

from ragflow_agent.agent.domain.agentic import (
    LongTermMemory,
    MemoryConsent,
    ToolAuthorizationContext,
)
from ragflow_agent.agent.domain.errors import AgentError
from ragflow_agent.agent.ports.agentic import MemoryRepositoryPort
from ragflow_agent.shared.ports.identity import IdGenerator
from ragflow_agent.shared.ports.time import Clock

_FORBIDDEN_MEMORY = re.compile(
    r"(?i)(password|passwd|api[_ -]?key|access[_ -]?token|authorization:|"
    r"private[_ -]?key|密码|密钥|令牌)"
)


class MemoryPolicyError(AgentError):
    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message, error_code=error_code, status_code=403)


class LongTermMemoryService:
    def __init__(
        self,
        *,
        repository: MemoryRepositoryPort,
        id_generator: IdGenerator,
        clock: Clock,
        ttl_days: int = 90,
    ) -> None:
        self._repository = repository
        self._id_generator = id_generator
        self._clock = clock
        self._ttl = timedelta(days=ttl_days)

    async def set_consent(
        self,
        context: ToolAuthorizationContext,
        *,
        enabled: bool,
        consent_version: str,
    ) -> MemoryConsent:
        now = self._clock.now()
        consent = MemoryConsent(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            enabled=enabled,
            consent_version=consent_version if enabled else None,
            consented_at=now if enabled else None,
            revoked_at=None if enabled else now,
        )
        await self._repository.save_consent(consent)
        if not enabled:
            await self._repository.delete_user_memories(
                tenant_id=context.tenant_id,
                user_id=context.actor_id,
            )
        return consent

    async def remember(
        self,
        context: ToolAuthorizationContext,
        *,
        content: str,
        source: str,
        explicit_user_request: bool,
    ) -> LongTermMemory:
        consent = await self._repository.get_consent(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
        )
        if not explicit_user_request or consent is None or not consent.enabled:
            raise MemoryPolicyError(
                "long-term memory requires explicit current consent and request",
                error_code="memory_consent_required",
            )
        normalized = content.strip()
        if not normalized or len(normalized) > 2_000:
            raise MemoryPolicyError(
                "memory content is invalid",
                error_code="memory_content_invalid",
            )
        if _FORBIDDEN_MEMORY.search(normalized):
            raise MemoryPolicyError(
                "secret-like content cannot be stored in long-term memory",
                error_code="memory_sensitive_content",
            )
        now = self._clock.now()
        item = LongTermMemory(
            memory_id=self._id_generator.new_id(),
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            content=normalized,
            source=source,
            consent_version=consent.consent_version or "unknown",
            consented_at=consent.consented_at or now,
            created_at=now,
            expires_at=now + self._ttl,
        )
        await self._repository.save_memory(item)
        return item

    async def list_active(self, context: ToolAuthorizationContext) -> tuple[LongTermMemory, ...]:
        consent = await self._repository.get_consent(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
        )
        if consent is None or not consent.enabled:
            return ()
        now = self._clock.now()
        return tuple(
            item
            for item in await self._repository.list_memories(
                tenant_id=context.tenant_id,
                user_id=context.actor_id,
            )
            if item.deleted_at is None and item.expires_at > now
        )

    async def consent_enabled(self, context: ToolAuthorizationContext) -> bool:
        consent = await self._repository.get_consent(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
        )
        return consent is not None and consent.enabled

    async def delete(self, context: ToolAuthorizationContext, memory_id: str) -> bool:
        return await self._repository.delete_memory(
            tenant_id=context.tenant_id,
            user_id=context.actor_id,
            memory_id=memory_id,
        )

    async def cleanup_expired(self) -> int:
        return await self._repository.delete_expired(before=self._clock.now())
