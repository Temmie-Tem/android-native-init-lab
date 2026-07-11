#!/usr/bin/env python3
"""Create the private transfer manifest for the FYG8 Full-LTO build host."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


SCHEMA = "s22plus_fyg8_kernel_transfer_manifest_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_DATE_EPOCH = 1754027756
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/transfer-manifest.json"
)
FILE_SPECS = (
    (
        Path("AGENTS.md"),
        "transfer-workspace-root-marker-and-safety-contract",
        "public",
        None,
    ),
    (
        Path("GOAL.md"),
        "transfer-workspace-root-marker-and-active-roadmap",
        "public",
        None,
    ),
    (
        Path("workspace/private/inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/Kernel.tar.gz"),
        "fyd9-base-kernel-source",
        "private-proprietary",
        "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
    ),
    (
        Path("workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz"),
        "fyg8-kernel-source-delta",
        "private-proprietary",
        "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a",
    ),
    (
        Path("workspace/private/inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/README_Kernel.txt"),
        "samsung-base-build-instructions",
        "private-proprietary",
        "8071d5a5c99374f28b5ead1a14cecf1237cef26682bf4eabb31d73eb6a7fa696",
    ),
    (
        Path("workspace/private/inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.txt"),
        "samsung-fyg8-overlay-instructions",
        "private-proprietary",
        "eda4809f02b548a2b2a3d5266dbf03714defba1bf1d11b1ed5113ffc372c7564",
    ),
    (
        Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_overlay_audit.py"),
        "overlay-audit-tool",
        "public",
        None,
    ),
    (
        Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_kernel_build.py"),
        "build-wrapper",
        "public",
        None,
    ),
    (
        Path("workspace/public/src/scripts/revalidation/s22plus_fyg8_stock_kernel_baseline.py"),
        "stock-baseline-tool",
        "public",
        None,
    ),
)
REPO_SPECS = (
    (
        "clang",
        Path("workspace/private/inputs/toolchains/aosp-clang-android12-release"),
        "6e3223f76384455acde43affde3df0ea9df66c0d",
        "toolchains/aosp-clang-android12-release",
    ),
    (
        "build-tools",
        Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/prebuilts/build-tools"),
        "cfedc16ec3deb680fca6fe2aff44a1837a97b50d",
        "source/kernel_platform/prebuilts/build-tools",
    ),
    (
        "glibc-sysroot",
        Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8"),
        "4e6f66acf138d40d9a80be24b275abb9c6eed729",
        "source/kernel_platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8",
    ),
    (
        "kernel-build-tools",
        Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/prebuilts/kernel-build-tools"),
        "ca5b087f88c0302ff66f59a6f26be663e92baf15",
        "source/kernel_platform/prebuilts/kernel-build-tools",
    ),
)


class ManifestError(ValueError):
    pass


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise ManifestError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(path: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ManifestError(f"git {' '.join(args)} failed for {path}: {result.stderr.strip()}")
    return result.stdout.strip()


def build_manifest(root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    for relative, role, sensitivity, expected in FILE_SPECS:
        path = resolve(root, relative)
        if not path.is_file():
            raise ManifestError(f"transfer input missing: {path}")
        actual = sha256_file(path)
        if expected is not None and actual != expected:
            raise ManifestError(f"transfer input SHA256 mismatch for {path}: {actual}")
        files.append(
            {
                "path": display_path(root, path),
                "role": role,
                "sensitivity": sensitivity,
                "size": path.stat().st_size,
                "sha256": actual,
            }
        )

    repositories: list[dict[str, Any]] = []
    for name, relative, expected, destination in REPO_SPECS:
        path = resolve(root, relative)
        actual = git_value(path, "rev-parse", "HEAD")
        dirty = bool(git_value(path, "status", "--porcelain"))
        if actual != expected or dirty:
            raise ManifestError(f"tool repository is not exact and clean: {name} actual={actual} dirty={dirty}")
        repositories.append(
            {
                "name": name,
                "source_path": display_path(root, path),
                "destination": destination,
                "commit": actual,
                "clean": True,
                "sensitivity": "public",
            }
        )

    return {
        "schema": SCHEMA,
        "target": TARGET,
        "generated_epoch": SOURCE_DATE_EPOCH,
        "host_only": True,
        "files": files,
        "toolchain_repositories": repositories,
        "required_symlinks": [
            {
                "link": "source/kernel_platform/prebuilts-master/clang/host/linux-x86/clang-r416183b",
                "target": "toolchains/aosp-clang-android12-release/clang-r416183b",
            }
        ],
        "destination_path_base": "all destination and symlink paths are relative to one transfer workspace root",
        "host_requirements": {
            "distribution": "Debian 12 x86_64",
            "min_physical_memory_bytes": 30 * 1024**3,
            "min_swap_bytes": 8 * 1024**3,
            "min_free_disk_bytes": 30 * 1024**3,
            "recommended_jobs_fx8300": 8,
            "recommended_session": "tmux",
            "required_debian_packages": ["git", "time"],
            "swap_policy": "8 GiB recommended headroom; not a hard gate with nominal 32 GiB physical RAM",
        },
        "reproduction_recipe": [
            "extract the pinned FYD9 Kernel.tar.gz into a fresh non-Git directory named source",
            "preserve AGENTS.md, GOAL.md, and workspace/public tool paths below the transfer workspace root",
            "validate and overlay every FYG8 member after exactly one Kernel/ prefix strip",
            "clone or copy all four toolchain repositories with .git metadata preserved at their recorded checkout destinations",
            "create the recorded clang-r416183b symlink from the source tree to the separate pinned clang checkout",
            "run s22plus_fyg8_kernel_overlay_audit.py --resident-tree source and require PASS",
            "run s22plus_fyg8_kernel_build.py --work-tree source --clang-repo toolchains/aosp-clang-android12-release --mode preflight --lto full --jobs 8",
            "only after preflight PASS run the same wrapper with --mode build",
        ],
        "claims": {
            "source_transfer_reproducible": True,
            "kernel_build_completed": False,
            "stock_equivalence_proved": False,
            "bootability_proved": False,
            "flash_authorized": False,
        },
        "safety": {
            "device_contact": False,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
            "private_files_publishable": False,
        },
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    out = resolve(root, args.out)
    manifest = build_manifest(root)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="ascii")
    print(json.dumps({"result": "pass", "out": display_path(root, out), "file_count": len(manifest["files"]), "repository_count": len(manifest["toolchain_repositories"]), "private_file_count": sum(item["sensitivity"] != "public" for item in manifest["files"])}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ManifestError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
