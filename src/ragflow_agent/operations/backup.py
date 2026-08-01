"""Content-addressed isolated backup/restore primitives for authority data."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BackupEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1)
    size: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class BackupManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    created_at: datetime
    rpo_hours: int = Field(default=24, ge=1)
    rto_hours: int = Field(default=4, ge=1)
    entries: tuple[BackupEntry, ...]
    search_indexes_rebuildable: bool = True

    @field_validator("created_at")
    @classmethod
    def created_at_is_aware(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("backup timestamp must be timezone-aware")
        return value


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def create_backup(source: Path, target: Path, *, created_at: datetime) -> BackupManifest:
    """Copy an authority snapshot into a new target and write a hash manifest."""
    if not source.is_dir() or target.exists():
        raise ValueError("backup source must exist and target must be new")
    payload = target / "payload"
    payload.mkdir(parents=True)
    entries = []
    for item in sorted(path for path in source.rglob("*") if path.is_file()):
        relative = item.relative_to(source)
        destination = payload / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)
        entries.append(
            BackupEntry(path=relative.as_posix(), size=item.stat().st_size, sha256=_digest(item))
        )
    manifest = BackupManifest(created_at=created_at, entries=tuple(entries))
    (target / "manifest.json").write_text(
        manifest.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def restore_backup(backup: Path, target: Path) -> BackupManifest:
    """Restore only into an empty location after validating every hash."""
    if target.exists() and any(target.iterdir()):
        raise ValueError("restore target must be empty")
    manifest = BackupManifest.model_validate_json(
        (backup / "manifest.json").read_text(encoding="utf-8")
    )
    target.mkdir(parents=True, exist_ok=True)
    payload = backup / "payload"
    for entry in manifest.entries:
        source = (payload / entry.path).resolve()
        if payload.resolve() not in source.parents or _digest(source) != entry.sha256:
            raise ValueError(f"backup entry failed validation: {entry.path}")
        destination = target / entry.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return manifest


def write_restore_evidence(path: Path, manifest: BackupManifest, *, elapsed_seconds: float) -> None:
    evidence = {
        "schema_version": 1,
        "entry_count": len(manifest.entries),
        "hashes_validated": True,
        "elapsed_seconds": elapsed_seconds,
        "rto_seconds": manifest.rto_hours * 3600,
        "rto_met": elapsed_seconds <= manifest.rto_hours * 3600,
        "search_index_rebuild_required": manifest.search_indexes_rebuildable,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
