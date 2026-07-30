"""Real MinIO/S3-compatible storage round trip."""

import os
from collections.abc import AsyncIterator
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import SecretStr

from ragflow_agent.config import ObjectStoreSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import KnowledgeAuthorizationError
from ragflow_agent.knowledge.infrastructure.object_store import S3ObjectStorage
from ragflow_agent.knowledge.ports.storage import StorageWriteRequest


def _settings() -> ObjectStoreSettings:
    endpoint = os.environ.get("RAGFLOW_AGENT_TEST_S3_ENDPOINT_URL")
    access_key = os.environ.get("RAGFLOW_AGENT_TEST_S3_ACCESS_KEY")
    secret_key = os.environ.get("RAGFLOW_AGENT_TEST_S3_SECRET_KEY")
    if endpoint is None or access_key is None or secret_key is None:
        pytest.skip("S3-compatible integration settings are not configured")
    return ObjectStoreSettings(
        endpoint_url=endpoint,
        bucket="ragflow-agent-phase04-tests",
        access_key=SecretStr(access_key),
        secret_key=SecretStr(secret_key),
    )


@pytest.mark.asyncio
async def test_s3_round_trip_integrity_and_tenant_denial() -> None:
    storage = S3ObjectStorage(_settings())
    await storage.ensure_bucket()
    payload = b"phase-04 object-store integration"
    object_key = f"tenants/tenant-s3-a/integration/{uuid4().hex}.txt"
    owner = AuthorizationContext(
        tenant_id="tenant-s3-a",
        actor_id="owner-a",
        request_id="trace-s3",
    )

    async def content() -> AsyncIterator[bytes]:
        yield payload[:8]
        yield payload[8:]

    stored = await storage.put(
        owner,
        StorageWriteRequest(
            tenant_id=owner.tenant_id,
            object_key=object_key,
            media_type="text/plain",
            size_bytes=len(payload),
            checksum_sha256=sha256(payload).hexdigest(),
            trace_id=owner.request_id,
        ),
        content(),
    )
    loaded = b"".join([part async for part in storage.read(owner, stored)])
    assert loaded == payload

    other = AuthorizationContext(
        tenant_id="tenant-s3-b",
        actor_id="owner-b",
        request_id="trace-s3-other",
    )
    with pytest.raises(KnowledgeAuthorizationError):
        _ = b"".join([part async for part in storage.read(other, stored)])

    await storage.delete(owner, stored)
