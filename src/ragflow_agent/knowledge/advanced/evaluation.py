"""Per-capability Phase 09 quality, cost, resource, and security decisions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import Field

from ragflow_agent.knowledge.advanced.domain import AdvancedCapability
from ragflow_agent.knowledge.domain.base import KnowledgeModel, NonEmptyStr


class AdvancedEvaluationResult(KnowledgeModel):
    capability: AdvancedCapability
    dataset_version: NonEmptyStr
    sample_count: int = Field(ge=1)
    quality_score: float = Field(ge=0, le=1)
    security_violations: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    generated_tokens: int = Field(ge=0)
    active_runtime_ms: float = Field(ge=0)
    decision: NonEmptyStr
    reason: NonEmptyStr


def deterministic_phase09_report(manifest: dict[str, Any]) -> dict[str, Any]:
    """Produce a reproducible Fake-provider report; it is not a real-model claim."""
    version = str(manifest["dataset_version"])
    capabilities = tuple(AdvancedCapability)
    results = [
        AdvancedEvaluationResult(
            capability=capability,
            dataset_version=version,
            sample_count=1,
            quality_score=1.0,
            security_violations=0,
            provider_calls=0,
            generated_tokens=0,
            active_runtime_ms=0,
            decision="no-go",
            reason=(
                "deterministic protocol validation only; keep default-off until real-provider gain"
            ),
        ).model_dump(mode="json")
        for capability in capabilities
    ]
    return {
        "schema_version": 1,
        "phase": "09",
        "test_mode": "deterministic_fake",
        "dataset_version": version,
        "capabilities": results,
        "overall_security_violations": 0,
        "production_model_validated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.dataset.read_text(encoding="utf-8"))
    report = deterministic_phase09_report(manifest)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(serialized, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
