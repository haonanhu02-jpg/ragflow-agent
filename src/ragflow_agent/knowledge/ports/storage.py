"""Tenant-scoped object-storage requests and streaming boundary."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator
from typing import Protocol, runtime_checkable

from pydantic import Field, model_validator

from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class StorageWriteRequest(KnowledgeModel):
    """Immutable identity and integrity metadata for one source object."""

    tenant_id: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    size_bytes: int = Field(ge=0)
    checksum_sha256: NonEmptyStr
    trace_id: NonEmptyStr

    @model_validator(mode="after")
    def key_is_tenant_namespaced(self) -> StorageWriteRequest:
        expected_prefix = f"tenants/{self.tenant_id}/"
        if not self.object_key.startswith(expected_prefix):
            raise ValueError("object_key must use the tenant namespace")
        return self


class StoredObject(KnowledgeModel):
    """Storage-neutral object metadata returned by an adapter."""

    tenant_id: NonEmptyStr
    object_key: NonEmptyStr
    media_type: NonEmptyStr
    size_bytes: int = Field(ge=0)
    checksum_sha256: NonEmptyStr
    etag: str | None = None


@runtime_checkable
class ObjectStoragePort(Protocol):
    """Stream source objects without exposing boto3 or filesystem types."""

    async def put(
        self,
        context: AuthorizationContext,
        request: StorageWriteRequest,
        content: AsyncIterable[bytes],
    ) -> StoredObject: ...

    def read(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> AsyncIterator[bytes]: ...

    async def delete(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> None: ...

    async def exists(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> bool: ...

    async def list_prefix(
        self,
        context: AuthorizationContext,
        *,
        tenant_id: str,
        prefix: str,
    ) -> tuple[str, ...]: ...
