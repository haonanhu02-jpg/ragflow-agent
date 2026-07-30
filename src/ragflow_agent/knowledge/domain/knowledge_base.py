"""KnowledgeBase aggregate contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from ragflow_agent.knowledge.domain.authorization import ResourceAuthorization, Visibility
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class KnowledgeBaseStatus(StrEnum):
    """Minimal lifecycle needed before document lifecycle implementation."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class KnowledgeBase(KnowledgeModel):
    """Tenant-scoped knowledge-base aggregate."""

    id: NonEmptyStr
    tenant_id: NonEmptyStr
    owner_id: NonEmptyStr
    name: NonEmptyStr
    description: str = ""
    visibility: Visibility = Visibility.PRIVATE
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("knowledge timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def updated_after_creation(self) -> KnowledgeBase:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot precede created_at")
        return self

    @property
    def authorization(self) -> ResourceAuthorization:
        return ResourceAuthorization(
            tenant_id=self.tenant_id,
            owner_id=self.owner_id,
            visibility=self.visibility,
        )
