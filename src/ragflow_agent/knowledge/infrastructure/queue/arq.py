"""Redis/ARQ publisher isolated behind IngestionQueuePort."""

from __future__ import annotations

from typing import Any, cast

import orjson
from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from ragflow_agent.config import QueueSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.domain.ingestion import IngestionEnvelope
from ragflow_agent.knowledge.ports.queue import QueueReceipt

ARQ_INGESTION_FUNCTION = "process_ingestion"


def arq_serialize(value: dict[str, Any]) -> bytes:
    """Avoid ARQ's default pickle payload for the controlled JSON envelope."""
    return orjson.dumps(value)


def arq_deserialize(value: bytes) -> dict[str, Any]:
    """Decode one ARQ job dictionary from JSON."""
    decoded = orjson.loads(value)
    if not isinstance(decoded, dict):
        raise ValueError("ARQ job payload must be an object")
    return cast(dict[str, Any], decoded)


class ArqIngestionQueue:
    """Publish versioned ingestion envelopes with deterministic job IDs."""

    def __init__(
        self,
        settings: QueueSettings,
        *,
        pool: ArqRedis | None = None,
    ) -> None:
        self._settings = settings
        self._pool = pool
        self._owns_pool = pool is None

    async def open(self) -> None:
        if self._pool is None:
            self._pool = await create_pool(
                RedisSettings.from_dsn(self._settings.url.get_secret_value()),
                default_queue_name=self._settings.queue_name,
                job_serializer=arq_serialize,
                job_deserializer=arq_deserialize,
            )

    async def close(self) -> None:
        if self._pool is not None and self._owns_pool:
            await self._pool.aclose()
            self._pool = None

    async def publish(
        self,
        context: AuthorizationContext,
        envelope: IngestionEnvelope,
    ) -> QueueReceipt:
        if context.tenant_id != envelope.tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
        if self._pool is None:
            await self.open()
        if self._pool is None:
            raise RuntimeError("ARQ pool did not open")
        job = await self._pool.enqueue_job(
            ARQ_INGESTION_FUNCTION,
            envelope.model_dump_json(),
            _job_id=envelope.message_id,
            _queue_name=self._settings.queue_name,
        )
        reference = (
            f"arq:{job.job_id}" if job is not None else f"arq:{envelope.message_id}:duplicate"
        )
        return QueueReceipt(
            message_id=envelope.message_id,
            transport_reference=reference,
        )
