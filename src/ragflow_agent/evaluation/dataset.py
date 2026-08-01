"""Fail-closed validation for versioned, licensed, split evaluation datasets."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DatasetFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class DatasetManifest(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: int = 1
    dataset_version: str = Field(min_length=1)
    license: str = Field(min_length=1)
    source: str = Field(min_length=1)
    contains_sensitive_data: bool = False
    redaction: str = Field(min_length=1)
    splits: tuple[str, ...] = Field(min_length=3)
    files: tuple[DatasetFile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def required_splits_and_safety(self) -> DatasetManifest:
        if set(self.splits) != {"development", "validation", "regression"}:
            raise ValueError("dataset splits must be development, validation, and regression")
        if self.contains_sensitive_data:
            raise ValueError("committed evaluation datasets cannot contain sensitive data")
        return self


def validate_dataset(manifest_path: Path) -> DatasetManifest:
    manifest = DatasetManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    root = manifest_path.parent.resolve()
    observed_splits: set[str] = set()
    identifiers: set[str] = set()
    for item in manifest.files:
        candidate = (root / item.path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise ValueError(f"dataset file escapes root or is missing: {item.path}")
        digest = sha256(candidate.read_bytes()).hexdigest()
        if digest != item.sha256:
            raise ValueError(f"dataset hash mismatch: {item.path}")
        if candidate.suffix == ".jsonl":
            for line_number, line in enumerate(
                candidate.read_text(encoding="utf-8").splitlines(), 1
            ):
                record: dict[str, Any] = json.loads(line)
                record_id = str(record.get("id", ""))
                split = str(record.get("split", ""))
                if not record_id or record_id in identifiers:
                    raise ValueError(f"missing or duplicate id in {item.path}:{line_number}")
                if split not in manifest.splits:
                    raise ValueError(f"invalid split in {item.path}:{line_number}")
                if not record.get("license"):
                    raise ValueError(f"record license missing in {item.path}:{line_number}")
                identifiers.add(record_id)
                observed_splits.add(split)
    if observed_splits != set(manifest.splits):
        raise ValueError("every declared split must contain at least one record")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = validate_dataset(args.manifest)
    print(
        json.dumps(
            {
                "status": "valid",
                "dataset_version": manifest.dataset_version,
                "file_count": len(manifest.files),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
