"""Real Redis verifies ARQ publication and deterministic deduplication."""

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic import SecretStr

from ragflow_agent.config import QueueSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope, IngestionStage
from ragflow_agent.knowledge.infrastructure.queue import (
    ArqIngestionQueue,
    arq_deserialize,
    arq_serialize,
)


def _redis_url() -> str:
    value = os.environ.get("RAGFLOW_AGENT_TEST_REDIS_URL")
    if value is None:
        pytest.skip("RAGFLOW_AGENT_TEST_REDIS_URL is not configured")
    return value


@pytest.mark.asyncio
async def test_arq_publish_is_tenant_scoped_and_idempotent() -> None:
    suffix = uuid4().hex
    settings = QueueSettings(
        url=SecretStr(_redis_url()),
        queue_name=f"arq:ragflow-agent:test:{suffix}",
    )
    pool = await create_pool(
        RedisSettings.from_dsn(_redis_url()),
        default_queue_name=settings.queue_name,
        job_serializer=arq_serialize,
        job_deserializer=arq_deserialize,
    )
    queue = ArqIngestionQueue(settings, pool=pool)
    context = AuthorizationContext(
        tenant_id="tenant-queue-a",
        actor_id="owner-a",
        request_id="trace-queue",
    )
    envelope = IngestionEnvelope(
        message_id=f"ingestion:{suffix}",
        tenant_id=context.tenant_id,
        job_id=f"job-{suffix}",
        task_id=f"job-{suffix}:parse",
        document_version_id=f"version-{suffix}",
        stage=IngestionStage.PARSE,
        attempt=1,
        idempotency_key=f"upload-{suffix}:parse",
        trace_id=context.request_id,
        created_at=datetime.now(UTC),
    )
    try:
        first = await queue.publish(context, envelope)
        duplicate = await queue.publish(context, envelope)

        assert first.transport_reference == f"arq:{envelope.message_id}"
        assert duplicate.transport_reference.endswith(":duplicate")
        assert await pool.zscore(settings.queue_name, envelope.message_id) is not None
    finally:
        await pool.zrem(settings.queue_name, envelope.message_id)
        await pool.delete(f"arq:job:{envelope.message_id}")
        await pool.aclose()
