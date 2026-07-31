from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from ragflow_agent.agent.evaluation import (
    AgenticScenarioResult,
    build_agentic_evaluation_report,
)


def test_deterministic_phase08_evaluation_covers_required_scenarios_and_passes_gate(
    tmp_path: Path,
) -> None:
    fixture = Path(__file__).with_name("deterministic-results.json")
    results = TypeAdapter(tuple[AgenticScenarioResult, ...]).validate_json(
        fixture.read_text(encoding="utf-8")
    )
    report = build_agentic_evaluation_report(
        generated_at=datetime(2026, 7, 31, tzinfo=UTC),
        results=results,
    )
    output = tmp_path / "phase08-agentic-report.json"
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    assert len(results) >= 26
    assert report.mode == "deterministic_fake"
    assert report.provider_claims == ()
    assert report.metrics.critical_safety_violations == 0
    assert report.metrics.overall_pass_rate >= 0.90
    assert report.metrics.tool_selection_and_parameter_validity >= 0.90
    assert report.metrics.no_or_partial_evidence_accuracy >= 0.95
    assert report.metrics.important_fact_citation_coverage >= 0.95
    assert report.metrics.groundedness >= 0.90
    assert report.gate_passed
    assert output.exists()
