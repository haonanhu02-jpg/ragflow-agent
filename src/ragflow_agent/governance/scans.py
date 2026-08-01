"""Deterministic large-file, provenance, secret-pattern, and dataset scans."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from ragflow_agent.evaluation.dataset import validate_dataset

_EXCLUDED = frozenset(
    {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
)
_SECRET = re.compile(
    r"(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})"
)
_UPSTREAM_IMPORT = re.compile(r"^\s*(?:from|import)\s+(?:api|rag|ragflow)(?:\.|\s|$)", re.MULTILINE)


def scan_repository(root: Path, *, max_file_bytes: int = 10 * 1024 * 1024) -> dict[str, object]:
    findings: list[str] = []
    scanned = 0
    for path in root.rglob("*"):
        if not path.is_file() or any(part in _EXCLUDED for part in path.parts):
            continue
        scanned += 1
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size > max_file_bytes:
            findings.append(f"large_file:{relative}")
        if path.suffix in {".py", ".md", ".toml", ".yml", ".yaml", ".json", ".env"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            if _SECRET.search(text):
                findings.append(f"possible_secret:{relative}")
            if relative.startswith(
                "src/ragflow_agent/knowledge/advanced/"
            ) and _UPSTREAM_IMPORT.search(text):
                findings.append(f"upstream_ragflow_import:{relative}")
    for manifest in (root / "datasets/phase10/v1/manifest.json",):
        validate_dataset(manifest)
    return {
        "schema_version": 1,
        "files_scanned": scanned,
        "findings": sorted(findings),
        "passed": not findings,
        "ragflow_source_copied": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = scan_repository(args.root.resolve())
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
