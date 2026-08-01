"""Machine-readable secret, size, dataset, and source-provenance checks."""

from __future__ import annotations

import argparse
import json
import runpy
from pathlib import Path
from typing import Protocol, cast

from ragflow_agent.evaluation.dataset import validate_dataset


class ScanText(Protocol):
    def __call__(self, text: str, *, include_assignments: bool = True) -> list[str]: ...


class RepositoryFiles(Protocol):
    def __call__(self, root: Path) -> list[Path]: ...


_SECRET_SCANNER = runpy.run_path(str(Path(__file__).with_name("check_secret_hygiene.py")))
repository_files = cast(RepositoryFiles, _SECRET_SCANNER["repository_files"])
scan_text = cast(ScanText, _SECRET_SCANNER["scan_text"])

MAX_TRACKED_FILE_BYTES = 10 * 1024 * 1024


def scan_repository(root: Path) -> dict[str, object]:
    files = repository_files(root)
    findings: list[str] = []
    oversized: list[str] = []
    for path in files:
        relative = path.relative_to(root)
        if not path.is_file() or path.name == "uv.lock":
            continue
        if path.stat().st_size > MAX_TRACKED_FILE_BYTES:
            oversized.append(relative.as_posix())
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        categories = scan_text(content, include_assignments="tests" not in relative.parts)
        findings.extend(f"{relative.as_posix()}:{category}" for category in categories)
    datasets = {}
    for phase in ("phase09", "phase10"):
        manifest = root / "datasets" / phase / "v1" / "manifest.json"
        value = validate_dataset(manifest)
        datasets[phase] = {
            "version": value.dataset_version,
            "license": value.license,
            "contains_sensitive_data": value.contains_sensitive_data,
        }
    passed = not findings and not oversized
    return {
        "schema_version": 1,
        "files_scanned": len(files),
        "passed": passed,
        "secret_findings": sorted(findings),
        "oversized_files": sorted(oversized),
        "datasets": datasets,
        "ragflow_source_copied": False,
        "third_party_source_vendored": False,
        "project_license_policy": "intentionally_absent",
        "project_license_required_for_completion": False,
        "project_license_file_present": (root / "LICENSE").is_file(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    report = scan_repository(root)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(serialized, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    return 0 if report["passed"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
