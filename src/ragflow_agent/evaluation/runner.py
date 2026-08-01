"""Deterministic Phase 10 runner and machine-readable report writer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ragflow_agent.evaluation.answers import score_answer
from ragflow_agent.evaluation.dataset import validate_dataset
from ragflow_agent.evaluation.gate import evaluate_release_gate
from ragflow_agent.evaluation.metrics import (
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def deterministic_report(manifest_path: Path) -> dict[str, object]:
    manifest = validate_dataset(manifest_path)
    relevant = frozenset({"chunk-brake-1"})
    retrieved = ("chunk-brake-1", "chunk-noise")
    answer = score_answer(
        expected_facts=frozenset({"inspect valve A"}),
        stated_facts=frozenset({"inspect valve A"}),
        supported_facts=frozenset({"inspect valve A"}),
        expected_citations=frozenset({"chunk-brake-1"}),
        predicted_citations=frozenset({"chunk-brake-1"}),
        should_refuse=False,
        refused=False,
    )
    metrics: dict[str, float | int] = {
        "retrieval_precision_at_2": precision_at_k(retrieved, relevant, 2),
        "retrieval_recall_at_10": recall_at_k(retrieved, relevant, 10),
        "mrr": mean_reciprocal_rank((retrieved,), (relevant,)),
        "ndcg_at_2": ndcg_at_k(retrieved, {"chunk-brake-1": 1}, 2),
        "answer_correctness": answer.correctness,
        "answer_faithfulness": answer.faithfulness,
        "citation_precision": answer.citation_precision,
        "citation_recall": answer.citation_recall,
        "cross_tenant_violations": 0,
        "critical_security_violations": 0,
        "recovery_failures": 0,
        "internal_error_rate": 0.0,
    }
    gate = evaluate_release_gate(metrics)
    return {
        "schema_version": 1,
        "phase": "10",
        "dataset_version": manifest.dataset_version,
        "test_mode": "deterministic_fake_and_isolated_local",
        "metrics": metrics,
        "release_gate": {"passed": gate.passed, "failures": gate.failures},
        "real_provider_validation": {
            "deepseek": False,
            "bge_m3": False,
            "bge_reranker": False,
            "vision": False,
            "asr": False,
        },
        "monthly_slo_proven": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = deterministic_report(args.dataset)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(serialized, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
