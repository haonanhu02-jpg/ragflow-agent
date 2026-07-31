"""S3-compatible implementation with tenant and integrity enforcement."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterable, AsyncIterator
from hashlib import sha256
from typing import Any

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from ragflow_agent.config import ObjectStoreSettings
from ragflow_agent.knowledge.domain.authorization import AuthorizationContext
from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.ports.storage import (
    StorageWriteRequest,
    StoredObject,
)


class S3ObjectStorage:
    """Store source bytes in a configured S3-compatible bucket."""

    def __init__(
        self,
        settings: ObjectStoreSettings,
        *,
        client: Any | None = None,
    ) -> None:
        self._settings = settings
        self._bucket = settings.bucket
        credentials: dict[str, str] = {}
        if settings.access_key is not None and settings.secret_key is not None:
            credentials = {
                "aws_access_key_id": settings.access_key.get_secret_value(),
                "aws_secret_access_key": settings.secret_key.get_secret_value(),
            }
        self._client = client or boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            use_ssl=settings.secure,
            **credentials,
        )

    async def ensure_bucket(self) -> None:
        """Create the configured bucket when it is absent."""

        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as error:
                code = str(error.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                self._client.create_bucket(Bucket=self._bucket)

        await asyncio.to_thread(ensure)

    async def put(
        self,
        context: AuthorizationContext,
        request: StorageWriteRequest,
        content: AsyncIterable[bytes],
    ) -> StoredObject:
        self._require_tenant(context, request.tenant_id)
        payload = b"".join([part async for part in content])
        digest = sha256(payload).hexdigest()
        if len(payload) != request.size_bytes or digest != request.checksum_sha256:
            raise KnowledgeConflictError(
                "object integrity metadata does not match content",
                error_code="object_integrity_mismatch",
            )

        def upload() -> str | None:
            response = self._client.put_object(
                Bucket=self._bucket,
                Key=request.object_key,
                Body=payload,
                ContentType=request.media_type,
                Metadata={
                    "tenant-id": request.tenant_id,
                    "sha256": request.checksum_sha256,
                },
            )
            etag = response.get("ETag")
            return str(etag).strip('"') if etag else None

        etag = await asyncio.to_thread(upload)
        return StoredObject(
            tenant_id=request.tenant_id,
            object_key=request.object_key,
            media_type=request.media_type,
            size_bytes=request.size_bytes,
            checksum_sha256=digest,
            etag=etag,
        )

    def read(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> AsyncIterator[bytes]:
        if context.tenant_id != stored_object.tenant_id:
            return _DeniedRead()
        return self._read(stored_object)

    async def _read(self, stored_object: StoredObject) -> AsyncIterator[bytes]:
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=stored_object.object_key,
            )
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code not in {"404", "NoSuchKey", "NotFound"}:
                raise
            raise KnowledgeNotFoundError(
                "stored_object",
                stored_object.object_key,
            ) from error
        body = response["Body"]
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, 64 * 1024)
                if not chunk:
                    break
                yield bytes(chunk)
        finally:
            await asyncio.to_thread(body.close)

    async def delete(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> None:
        self._require_tenant(context, stored_object.tenant_id)
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=stored_object.object_key,
        )

    async def exists(
        self,
        context: AuthorizationContext,
        stored_object: StoredObject,
    ) -> bool:
        self._require_tenant(context, stored_object.tenant_id)
        try:
            await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=stored_object.object_key,
            )
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey", "NotFound"}:
                return False
            raise
        return True

    async def list_prefix(
        self,
        context: AuthorizationContext,
        *,
        tenant_id: str,
        prefix: str,
    ) -> tuple[str, ...]:
        self._require_tenant(context, tenant_id)
        tenant_prefix = f"tenants/{tenant_id}/"
        if not prefix.startswith(tenant_prefix):
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")

        def list_keys() -> tuple[str, ...]:
            paginator = self._client.get_paginator("list_objects_v2")
            keys: list[str] = []
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                keys.extend(str(item["Key"]) for item in page.get("Contents", ()))
            return tuple(sorted(keys))

        return await asyncio.to_thread(list_keys)

    @staticmethod
    def _require_tenant(context: AuthorizationContext, tenant_id: str) -> None:
        if context.tenant_id != tenant_id:
            raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")


class _DeniedRead:
    """Fail closed before yielding bytes for a cross-tenant read."""

    def __aiter__(self) -> _DeniedRead:
        return self

    async def __anext__(self) -> bytes:
        raise KnowledgeAuthorizationError(reason_code="tenant_mismatch")
