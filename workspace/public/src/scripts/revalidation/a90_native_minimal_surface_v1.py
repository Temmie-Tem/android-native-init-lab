#!/usr/bin/env python3
"""Inventory the first H0-only A90 native-init minimization slice.

The tool reads and hashes the current flat-builder profile.  It does not build
an image, write an artifact, contact a device, or grant candidate authority.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from a90_flat_builder import buildlib  # noqa: E402


SCHEMA = "a90-native-init-minimal-surface-v1"
DECISION = "H0_FIRST_REMOVAL_SLICE_READY_NO_CANDIDATE_AUTHORITY"
DEFAULT_MANIFEST = (
    HERE / "a90_flat_builder/versions/phase2-display-v1/manifest.toml"
)
EXPECTED_PROFILE = "phase2-display-v1-native-handoff"
EXPECTED_COUNTS = {
    "native_init_sources": 60,
    "native_init_cflags": 84,
    "helper_sources": 1,
    "helper_cflags": 29,
    "doom_sources": 80,
    "materialized_engine_sources": 3,
    "obsolete_ramdisk_engines": 25,
}


class InventoryError(RuntimeError):
    """Raised when the selected H0 inventory is not the exact known surface."""


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL_A90.md").is_file():
            return parent
    raise InventoryError("repository root is absent")


def _public_key(repo: Path, path: Path) -> dict[str, object]:
    resolved = path.resolve(strict=True)
    try:
        relative = resolved.relative_to(repo.resolve())
    except ValueError as exc:
        raise InventoryError("public source key escapes repository") from exc
    if not resolved.is_file() or resolved.is_symlink():
        raise InventoryError("public source key is not one regular file")
    return {
        "path": relative.as_posix(),
        "size": resolved.stat().st_size,
        "sha256": buildlib.sha256_file(resolved),
    }


def _surface_counts(manifest: dict[str, Any]) -> dict[str, int]:
    return {
        "native_init_sources": len(manifest["init"]["sources"]),
        "native_init_cflags": len(manifest["init"]["cflags"]),
        "helper_sources": 1,
        "helper_cflags": len(manifest["helper"]["cflags"]),
        "doom_sources": len(manifest["engine"]["doom_sources"]),
        "materialized_engine_sources": len(
            manifest["engine"]["materialized_sources"]
        ),
        "obsolete_ramdisk_engines": len(
            manifest["ramdisk"]["obsolete_engines"]
        ),
    }


def build_inventory(
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    validate_private_pins: bool = True,
) -> dict[str, Any]:
    repo = repo_root()
    selected = manifest_path.resolve(strict=True)
    versions = (HERE / "a90_flat_builder/versions").resolve()
    try:
        relative = selected.relative_to(versions)
    except ValueError as exc:
        raise InventoryError("manifest is outside flat-builder versions") from exc
    if len(relative.parts) != 2 or relative.name != "manifest.toml":
        raise InventoryError("manifest must be one versions/<profile>/manifest.toml")

    resolution = buildlib.resolve_manifest(selected)
    manifest = resolution.data
    if (
        manifest.get("profile") != EXPECTED_PROFILE
        or manifest.get("candidate_authority") is not False
    ):
        raise InventoryError("selected profile identity or authority changed")
    counts = _surface_counts(manifest)
    if counts != EXPECTED_COUNTS:
        raise InventoryError(f"resolved surface counts changed: {counts}")

    input_pins: dict[str, str] = {
        "native_init_closure": str(manifest["init"]["closure_sha256"]),
        "helper_source": str(manifest["helper"]["source_sha256"]),
        "doom_closure": str(manifest["engine"]["doom_closure_sha256"]),
    }
    if validate_private_pins:
        inputs = buildlib.validate_inputs(repo, resolution, manifest)
        for key in (
            "base_boot_sha256",
            "accepted_boot_sha256",
            "init_closure_sha256",
            "helper_source_sha256",
            "doom_closure_sha256",
        ):
            input_pins[key] = str(inputs[key])
    buildlib.revalidate_manifest_lineage(resolution)

    source_keys = {
        "inventory": _public_key(repo, Path(__file__)),
        "flat_builder": _public_key(
            repo,
            HERE / "a90_flat_builder/build.py",
        ),
        "flat_builder_library": _public_key(
            repo,
            HERE / "a90_flat_builder/buildlib.py",
        ),
    }
    for index, path in enumerate(resolution.lineage):
        source_keys[f"manifest_{index}"] = _public_key(repo, path)

    return {
        "schema": SCHEMA,
        "decision": DECISION,
        "profile": EXPECTED_PROFILE,
        "candidate_authority": False,
        "device_contact": False,
        "device_effect": False,
        "artifact_write": False,
        "manifest_effective_sha256": resolution.effective_sha256,
        "surface_counts": counts,
        "input_pins": input_pins,
        "source_keys": source_keys,
        "first_removal_slice": {
            "name": "separate-doom-engine-and-obsolete-ramdisk-engines",
            "native_init_sources_changed": False,
            "native_init_cflags_changed": True,
            "native_init_cflags_to_remove": 47,
            "native_init_cflags_after_removal": 37,
            "helper_changed": False,
            "active_engine_ramdisk_path": manifest["engine"]["ramdisk_path"],
            "doom_sources_to_leave_product_closure": counts["doom_sources"],
            "materialized_engine_sources_to_leave_product_closure": counts[
                "materialized_engine_sources"
            ],
            "obsolete_ramdisk_engines_to_remove": counts[
                "obsolete_ramdisk_engines"
            ],
            "current_profile_requires_helper_and_engine": True,
            "builder_change_requires_focused_tests": True,
        },
        "next_gate": (
            "H0 builder support and deterministic A/B only; any boot transfer "
            "remains attended F1"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    value = build_inventory(args.manifest)
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InventoryError, buildlib.ManifestError) as exc:
        print(f"a90-native-minimal-surface-v1: {exc}", file=sys.stderr)
        raise SystemExit(1)
