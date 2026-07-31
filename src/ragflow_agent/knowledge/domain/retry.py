"""Provider-neutral lifecycle failure classification and bounded retry policy."""

import random
from dataclasses import dataclass
from typing import Protocol

from ragflow_agent.knowledge.domain.errors import (
    KnowledgeAuthorizationError,
    KnowledgeConflictError,
    KnowledgeNotFoundError,
)
from ragflow_agent.knowledge.domain.lifecycle import FailureClass


class RandomSource(Protocol):
    def random(self) -> float: ...


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 6
    concurrency_attempts: int = 3
    base_seconds: float = 1
    max_seconds: float = 300

    def delay_seconds(
        self,
        attempt: int,
        *,
        retry_after: float | None = None,
        random_source: RandomSource | None = None,
    ) -> float:
        if retry_after is not None:
            return min(max(0, retry_after), self.max_seconds)
        source = random_source or random
        ceiling = min(
            float(self.max_seconds),
            float(self.base_seconds * (2 ** max(0, attempt - 1))),
        )
        return float(ceiling * source.random())


@dataclass(frozen=True, slots=True)
class FailureDecision:
    classification: FailureClass
    retryable: bool
    code: str
    retry_after_seconds: float | None = None


_CONCURRENCY_CODES = frozenset(
    {
        "document_revision_conflict",
        "lifecycle_fencing_conflict",
        "index_alias_conflict",
        "operation_lease_lost",
    }
)


def classify_failure(error: BaseException) -> FailureDecision:
    if isinstance(error, (KnowledgeAuthorizationError, KnowledgeNotFoundError)):
        return FailureDecision(FailureClass.PERMANENT, False, error.error_code)
    if isinstance(error, KnowledgeConflictError):
        retryable = error.error_code in _CONCURRENCY_CODES
        return FailureDecision(
            FailureClass.CONCURRENCY if retryable else FailureClass.PERMANENT,
            retryable,
            error.error_code,
        )
    if isinstance(error, (TimeoutError, ConnectionError)):
        return FailureDecision(FailureClass.TRANSIENT, True, type(error).__name__)
    raw_status: object = getattr(error, "status_code", None)
    if isinstance(raw_status, int):
        retryable = raw_status in {408, 409, 425, 429} or raw_status >= 500
        return FailureDecision(
            FailureClass.TRANSIENT if retryable else FailureClass.PERMANENT,
            retryable,
            f"http_{raw_status}",
            _retry_after(getattr(error, "retry_after", None)),
        )
    return FailureDecision(FailureClass.UNKNOWN, False, type(error).__name__)


def may_retry(decision: FailureDecision, *, attempt: int, policy: RetryPolicy) -> bool:
    limit = (
        policy.concurrency_attempts
        if decision.classification is FailureClass.CONCURRENCY
        else policy.max_attempts
    )
    return decision.retryable and attempt < limit


def _retry_after(value: object) -> float | None:
    if not isinstance(value, (int, float, str)):
        return None
    try:
        return max(0, float(value))
    except (TypeError, ValueError):
        return None
