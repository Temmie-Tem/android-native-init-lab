"""Workspace script bootstrap helpers."""

from __future__ import annotations

import sys
from pathlib import Path


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


def add_legacy_revalidation_path(root: Path | None = None) -> Path:
    resolved_root = root or repo_root()
    legacy_path = resolved_root / "scripts" / "revalidation"
    legacy_text = str(legacy_path)
    if legacy_text not in sys.path:
        sys.path.append(legacy_text)
    return legacy_path
