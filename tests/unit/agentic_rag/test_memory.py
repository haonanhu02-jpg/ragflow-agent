from datetime import UTC, datetime, timedelta

import pytest

from ragflow_agent.agent.application.memory import LongTermMemoryService, MemoryPolicyError
from ragflow_agent.agent.domain.agentic import ToolAuthorizationContext
from tests.fakes.agentic import MemoryAgenticMemoryRepository
from tests.fakes.knowledge import FixedClock, SequenceIdGenerator


def _context(tenant: str = "tenant-a", user: str = "user-a") -> ToolAuthorizationContext:
    return ToolAuthorizationContext(tenant_id=tenant, actor_id=user, request_id="request-a")


@pytest.mark.asyncio
async def test_memory_is_off_by_default_and_requires_explicit_request() -> None:
    service = LongTermMemoryService(
        repository=MemoryAgenticMemoryRepository(),
        id_generator=SequenceIdGenerator(["memory-1"]),
        clock=FixedClock(datetime(2026, 7, 31, tzinfo=UTC)),
    )
    with pytest.raises(MemoryPolicyError):
        await service.remember(
            _context(),
            content="I prefer concise answers",
            source="user",
            explicit_user_request=True,
        )


@pytest.mark.asyncio
async def test_memory_consent_isolated_expired_revoked_and_physically_deleted() -> None:
    now = datetime(2026, 7, 31, tzinfo=UTC)
    repository = MemoryAgenticMemoryRepository()
    service = LongTermMemoryService(
        repository=repository,
        id_generator=SequenceIdGenerator(["memory-1", "memory-2"]),
        clock=FixedClock(now),
        ttl_days=90,
    )
    await service.set_consent(_context(), enabled=True, consent_version="v1")
    item = await service.remember(
        _context(),
        content="I prefer concise answers",
        source="explicit_user_request",
        explicit_user_request=True,
    )

    assert item.expires_at == now + timedelta(days=90)
    assert await service.list_active(_context()) == (item,)
    assert await service.list_active(_context("tenant-b", "user-a")) == ()
    assert await service.list_active(_context("tenant-a", "user-b")) == ()
    await service.set_consent(_context(), enabled=False, consent_version="v1")
    assert await service.list_active(_context()) == ()
    assert repository.memories == {}


@pytest.mark.asyncio
async def test_memory_rejects_secret_like_content_and_cleanup_is_executable() -> None:
    now = datetime(2026, 7, 31, tzinfo=UTC)
    repository = MemoryAgenticMemoryRepository()
    service = LongTermMemoryService(
        repository=repository,
        id_generator=SequenceIdGenerator(["memory-1"]),
        clock=FixedClock(now),
        ttl_days=0,
    )
    await service.set_consent(_context(), enabled=True, consent_version="v1")
    with pytest.raises(MemoryPolicyError):
        await service.remember(
            _context(), content="api_key=secret", source="user", explicit_user_request=True
        )
    await service.remember(
        _context(), content="Use metric units", source="user", explicit_user_request=True
    )
    assert await service.cleanup_expired() == 1
