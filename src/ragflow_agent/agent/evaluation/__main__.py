"""Build a report from captured deterministic or real-model scenario results."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from ragflow_agent.agent.evaluation.agentic import (
    AgenticScenarioResult,
    build_agentic_evaluation_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Phase 08 Agentic RAG report")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    results = TypeAdapter(tuple[AgenticScenarioResult, ...]).validate_json(
        args.input.read_text(encoding="utf-8")
    )
    report = build_agentic_evaluation_report(
        generated_at=datetime.now(UTC),
        results=results,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    if not report.gate_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
