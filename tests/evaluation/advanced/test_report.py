import json
from pathlib import Path

from ragflow_agent.knowledge.advanced.evaluation import deterministic_phase09_report


def test_each_advanced_capability_has_an_independent_no_go_decision() -> None:
    manifest = json.loads(Path("datasets/phase09/v1/manifest.json").read_text(encoding="utf-8"))
    report = deterministic_phase09_report(manifest)
    results = report["capabilities"]
    assert len(results) == 9
    assert {item["capability"] for item in results} == set(manifest["capabilities"])
    assert all(item["security_violations"] == 0 for item in results)
    assert all(item["decision"] == "no-go" for item in results)
    assert report["production_model_validated"] is False
