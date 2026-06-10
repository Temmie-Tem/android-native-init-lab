"""Workspace script bootstrap helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def add_legacy_revalidation_path(root: Path | None = None, *, include_archive: bool | None = None) -> Path:
    resolved_root = root or repo_root()
    harness_path = resolved_root / "workspace" / "public" / "src" / "harness"
    harness_text = str(harness_path)
    if harness_text not in sys.path:
        sys.path.append(harness_text)
    legacy_path = (
        resolved_root
        / "workspace"
        / "public"
        / "archive"
        / "scripts"
        / "revalidation"
    )
    archive_enabled = _env_flag("A90_INCLUDE_ARCHIVE_REVALIDATION") if include_archive is None else include_archive
    if archive_enabled:
        legacy_text = str(legacy_path)
        if legacy_text not in sys.path:
            sys.path.append(legacy_text)
    return legacy_path
