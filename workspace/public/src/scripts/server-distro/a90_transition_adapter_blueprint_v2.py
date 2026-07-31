#!/usr/bin/env python3
"""Inventory the non-live A90 transition-v2 adapter route table."""

from __future__ import annotations

import argparse
import ast
import json
import stat
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
if str(REVAL_DIR) not in sys.path:
    sys.path.insert(0, str(REVAL_DIR))

from a90_transition_manifest_v2 import (  # noqa: E402
    AUDIT_SCHEMA,
    GLOBAL_BLOCKERS,
    ManifestError,
    expected_blueprint,
    validate_blueprint,
)


def _confined_source(repo_root: Path, relative: str) -> Path:
    """Reject source paths that leave the real non-symlink repository tree."""

    root = repo_root.absolute()
    try:
        root_info = root.lstat()
    except OSError as exc:
        raise ManifestError("repository root is unavailable") from exc
    if not stat.S_ISDIR(root_info.st_mode) or root.is_symlink():
        raise ManifestError("repository root is not a real directory")
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise ManifestError("repository root is unavailable") from exc
    if resolved_root != root:
        raise ManifestError("repository root hierarchy is symlinked")
    current = root
    parts = PurePosixPath(relative).parts
    if not parts or ".." in parts or PurePosixPath(relative).is_absolute():
        raise ManifestError("inventory path is not canonical")
    for index, part in enumerate(parts):
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ManifestError(f"inventory source is unavailable: {relative}") from exc
        if stat.S_ISLNK(info.st_mode):
            raise ManifestError(f"inventory source hierarchy is symlinked: {relative}")
        if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ManifestError(f"inventory source parent is not a directory: {relative}")
    if not stat.S_ISREG(info.st_mode):
        raise ManifestError(f"inventory source is not a regular file: {relative}")
    try:
        current.resolve(strict=True).relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ManifestError(f"inventory source escaped the repository: {relative}") from exc
    return current


def _top_level_definitions(path: Path) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise ManifestError(f"inventory source cannot be parsed: {path}") from exc
    names = [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    if duplicates:
        raise ManifestError(
            "inventory source has duplicate top-level definitions: "
            + ",".join(duplicates)
        )
    return set(names)


def audit_blueprint(value: Any, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Validate the route table and inventory named symbols without importing them."""

    blueprint = validate_blueprint(value)
    verified: list[dict[str, Any]] = []
    for name, item in blueprint["source_inventory"].items():
        path = _confined_source(repo_root, item["path"])
        available = _top_level_definitions(path)
        missing = sorted(set(item["callables"]) - available)
        if missing:
            raise ManifestError(
                f"inventory callables are missing: {name}: {','.join(missing)}"
            )
        verified.append(
            {
                "name": name,
                "path": item["path"],
                "callables": list(item["callables"]),
                "symbols_present": True,
            }
        )
    return {
        "schema": AUDIT_SCHEMA,
        "decision": "PASS_HOST_DESIGN_ONLY_LIVE_BLOCKED",
        "host_only": True,
        "live_ready": False,
        "device_authority": False,
        "approval_preparation": False,
        "device_contact": False,
        "device_write": False,
        "source_identity_bound": False,
        "symbol_inventory_semantic_proof": False,
        "source_inventory": verified,
        "blockers": list(GLOBAL_BLOCKERS),
        "blueprint": blueprint,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", action="store_true", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(
        json.dumps(
            audit_blueprint(expected_blueprint()),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
