import json
from pathlib import Path

import pytest

from ragflow_agent.evaluation.dataset import validate_dataset
from ragflow_agent.evaluation.gate import evaluate_release_gate
from ragflow_agent.evaluation.runner import deterministic_report


def test_versioned_dataset_hash_license_redaction_and_splits_validate() -> None:
    manifest = validate_dataset(Path("datasets/phase10/v1/manifest.json"))
    assert manifest.dataset_version == "phase10-v1"
    assert not manifest.contains_sensitive_data


def test_deliberate_quality_degradation_fails_release_gate() -> None:
    degraded = {
        "retrieval_recall_at_10": 0.1,
        "answer_faithfulness": 0.2,
        "citation_recall": 0.1,
        "internal_error_rate": 0.2,
        "cross_tenant_violations": 1,
        "critical_security_violations": 1,
        "recovery_failures": 1,
    }
    result = evaluate_release_gate(degraded)
    assert not result.passed
    assert "cross_tenant_violations" in result.failures
    assert "citation_recall" in result.failures


def test_deterministic_runner_passes_but_discloses_real_provider_gap() -> None:
    report = deterministic_report(Path("datasets/phase10/v1/manifest.json"))
    assert report["release_gate"] == {"passed": True, "failures": ()}
    assert report["monthly_slo_proven"] is False
    assert report["real_provider_validation"] == {
        "deepseek": False,
        "bge_m3": False,
        "bge_reranker": False,
        "vision": False,
        "asr": False,
    }


def test_modified_dataset_is_rejected(tmp_path: Path) -> None:
    source = Path("datasets/phase10/v1/manifest.json")
    manifest = json.loads(source.read_text(encoding="utf-8"))
    manifest["files"] = [{"path": "sample.jsonl", "sha256": "0" * 64}]
    (tmp_path / "sample.jsonl").write_text(
        '{"id":"x","split":"development","license":"CC0"}\n', encoding="utf-8"
    )
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_dataset(path)
