"""Fail when repository files contain common credential material."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

TOKEN_PATTERN = re.compile(
    r"\b(?:"
    r"AKIA[0-9A-Z]{16}|"
    r"github_pat_[A-Za-z0-9_]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|"
    r"sk-[A-Za-z0-9_-]{20,}"
    r")\b"
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:password|secret|token|api[_-]?key|access[_-]?key)"
    r"\s*[:=]\s*(?:"
    r"SecretStr\(\s*[\"'](?P<wrapped>[^\"']+)[\"']|"
    r"[\"'](?P<quoted>[^\"']+)[\"']|"
    r"(?P<bare>[^\s,\)]+)"
    r")"
)
ALLOWED_VALUES = {
    "change-me",
    "check",
    "example",
    "none",
    "placeholder",
    "secretstr",
    "str",
    "test",
    "unset",
}
ALLOWED_PREFIXES = ("${", "bootstrap-", "phase01-", "test-", "dummy-")
REFERENCE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
SKIPPED_FILES = {"uv.lock"}
SKIPPED_PATHS: set[Path] = set()


def scan_text(text: str, *, include_assignments: bool = True) -> list[str]:
    """Return credential categories found in text."""
    findings: list[str] = []
    if PRIVATE_KEY_PATTERN.search(text):
        findings.append("private-key")
    if TOKEN_PATTERN.search(text):
        findings.append("provider-token")
    if include_assignments:
        for match in ASSIGNMENT_PATTERN.finditer(text):
            value = next(
                group
                for group in (
                    match.group("wrapped"),
                    match.group("quoted"),
                    match.group("bare"),
                )
                if group is not None
            ).strip()
            normalized = value.lower()
            if match.group("bare") is not None and REFERENCE_PATTERN.fullmatch(value):
                continue
            if normalized in ALLOWED_VALUES or normalized.startswith(ALLOWED_PREFIXES):
                continue
            findings.append("credential-assignment")
    return sorted(set(findings))


def repository_files(root: Path) -> list[Path]:
    """Return tracked and untracked non-ignored files."""
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [
        root / relative
        for relative in result.stdout.decode("utf-8").split("\0")
        if relative
    ]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings: list[str] = []
    for path in repository_files(root):
        relative_path = path.relative_to(root)
        if (
            path.name in SKIPPED_FILES
            or relative_path in SKIPPED_PATHS
            or not path.is_file()
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        categories = scan_text(
            text,
            include_assignments="tests" not in relative_path.parts,
        )
        if categories:
            findings.append(f"{path.relative_to(root)}: {', '.join(categories)}")

    if findings:
        print("Potential credential material found:")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print("Secret hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
