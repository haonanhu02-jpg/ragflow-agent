import pytest

from ragflow_agent.operations.faults import exercise_fault


@pytest.mark.parametrize(
    "scenario",
    (
        "postgres_unavailable",
        "redis_unavailable",
        "minio_unavailable",
        "elasticsearch_unavailable",
        "worker_killed",
        "provider_timeout",
        "network_interrupted",
        "checkpoint_failed",
        "dlq_backlog",
    ),
)
def test_isolated_fault_is_detected_and_recovered(scenario: str) -> None:
    def inject() -> None:
        raise TimeoutError(scenario)

    result = exercise_fault(
        scenario,
        inject=inject,
        recover=lambda: True,
        elapsed_seconds=1.0,
    )
    assert result.detected and result.recovered and not result.data_loss
