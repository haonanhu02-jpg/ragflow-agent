from ragflow_agent.operations.performance import summarize_performance


def test_local_capacity_summary_records_latency_backpressure_and_cost_boundary() -> None:
    report = summarize_performance(
        tuple(float(value) for value in range(1, 101)),
        errors=0,
        max_concurrency=32,
        backpressure_observed=True,
    )
    assert 95 <= report.p95_ms <= 96
    assert report.error_rate == 0
    assert report.max_concurrency == 32
    assert report.cost_status == "local"
