"""Deterministic UTC window features and similar-history retrieval."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import sqrt

from pydantic import Field, field_validator

from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class TemporalEvent(KnowledgeModel):
    id: NonEmptyStr
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    series_id: NonEmptyStr
    occurred_at: datetime
    original_timezone: NonEmptyStr
    text: NonEmptyStr
    source_chunk_ids: tuple[NonEmptyStr, ...] = Field(min_length=1)

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("temporal event timestamp must be timezone-aware")
        return value.astimezone(UTC)


class TimePoint(KnowledgeModel):
    observed_at: datetime
    value: float | None

    @field_validator("observed_at")
    @classmethod
    def observed_at_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("time point must be timezone-aware")
        return value.astimezone(UTC)


class TimeWindow(KnowledgeModel):
    tenant_id: NonEmptyStr
    knowledge_base_id: NonEmptyStr
    series_id: NonEmptyStr
    start_at: datetime
    end_at: datetime
    original_timezone: NonEmptyStr
    count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    minimum: float | None
    maximum: float | None
    mean: float | None
    trend: float | None
    source_chunk_ids: tuple[NonEmptyStr, ...] = ()

    def feature(self) -> tuple[float, ...]:
        return tuple(
            value if value is not None else 0.0
            for value in (self.minimum, self.maximum, self.mean, self.trend)
        )


class TemporalRagService:
    def __init__(self, *, max_points: int = 1_000_000) -> None:
        self._max_points = max_points

    def timeline(self, events: tuple[TemporalEvent, ...]) -> tuple[TemporalEvent, ...]:
        return tuple(sorted(events, key=lambda item: (item.occurred_at, item.id)))

    def windows(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        series_id: str,
        original_timezone: str,
        points: tuple[TimePoint, ...],
        window_seconds: int,
        source_chunk_ids: tuple[str, ...] = (),
    ) -> tuple[TimeWindow, ...]:
        if len(points) > self._max_points or window_seconds < 1:
            raise ValueError("time series resource budget exceeded")
        if not points:
            return ()
        ordered = sorted(points, key=lambda item: item.observed_at)
        anchor = ordered[0].observed_at
        buckets: dict[int, list[TimePoint]] = {}
        for point in ordered:
            index = int((point.observed_at - anchor).total_seconds() // window_seconds)
            buckets.setdefault(index, []).append(point)
        result = []
        for index, bucket in sorted(buckets.items()):
            present = [point.value for point in bucket if point.value is not None]
            trend = None
            if len(present) >= 2:
                trend = (present[-1] - present[0]) / (len(present) - 1)
            start = anchor + timedelta(seconds=index * window_seconds)
            result.append(
                TimeWindow(
                    tenant_id=tenant_id,
                    knowledge_base_id=knowledge_base_id,
                    series_id=series_id,
                    start_at=start,
                    end_at=start + timedelta(seconds=window_seconds),
                    original_timezone=original_timezone,
                    count=len(present),
                    missing_count=len(bucket) - len(present),
                    minimum=min(present) if present else None,
                    maximum=max(present) if present else None,
                    mean=sum(present) / len(present) if present else None,
                    trend=trend,
                    source_chunk_ids=source_chunk_ids,
                )
            )
        return tuple(result)

    def similar(
        self, query: TimeWindow, candidates: tuple[TimeWindow, ...], *, top_k: int = 5
    ) -> tuple[TimeWindow, ...]:
        safe = [
            item
            for item in candidates
            if item.tenant_id == query.tenant_id
            and item.knowledge_base_id == query.knowledge_base_id
            and item.series_id == query.series_id
        ]
        distances = sorted(
            safe,
            key=lambda item: sqrt(
                sum(
                    (left - right) ** 2
                    for left, right in zip(query.feature(), item.feature(), strict=True)
                )
            ),
        )
        return tuple(distances[:top_k])
