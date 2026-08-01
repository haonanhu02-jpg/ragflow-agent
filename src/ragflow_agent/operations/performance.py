"""Local-only latency, concurrency, capacity, and cost summaries."""

from dataclasses import dataclass
from statistics import quantiles


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    sample_count: int
    p95_ms: float
    error_rate: float
    max_concurrency: int
    backpressure_observed: bool
    cost_status: str


def summarize_performance(
    latencies_ms: tuple[float, ...],
    *,
    errors: int,
    max_concurrency: int,
    backpressure_observed: bool,
    cost_status: str = "local",
) -> PerformanceReport:
    if not latencies_ms or errors < 0 or errors > len(latencies_ms):
        raise ValueError("performance samples and error count are invalid")
    p95 = latencies_ms[0] if len(latencies_ms) == 1 else quantiles(latencies_ms, n=100)[94]
    return PerformanceReport(
        sample_count=len(latencies_ms),
        p95_ms=p95,
        error_rate=errors / len(latencies_ms),
        max_concurrency=max_concurrency,
        backpressure_observed=backpressure_observed,
        cost_status=cost_status,
    )
