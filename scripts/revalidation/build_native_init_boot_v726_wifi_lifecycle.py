#!/usr/bin/env python3
"""Compatibility wrapper for the workspace current V726 Wi-Fi lifecycle builder."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


CANONICAL_RELATIVE_PATH = "workspace/public/src/scripts/revalidation/build_native_init_boot_v726_wifi_lifecycle.py"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_canonical(run_name: str) -> dict[str, object]:
    root = repo_root()
    canonical = root / CANONICAL_RELATIVE_PATH
    canonical_dir = str(canonical.parent)
    legacy_dir = str(root / "scripts" / "revalidation")
    if canonical_dir not in sys.path:
        sys.path.insert(0, canonical_dir)
    if legacy_dir not in sys.path:
        sys.path.append(legacy_dir)
    return runpy.run_path(str(canonical), run_name=run_name)


if __name__ == "__main__":
    run_canonical("__main__")
else:
    globals().update(run_canonical(__name__))
