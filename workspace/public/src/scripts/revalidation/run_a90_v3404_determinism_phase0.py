#!/usr/bin/env python3
"""Run the V3404 builder twice without touching its accepted output paths."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
SCRIPT_DIR = Path(__file__).resolve().parent
ENTRYPOINT = SCRIPT_DIR / "build_native_init_boot_v3404_d3_resolved_owner_timeout.py"
ACCEPTED_BOOT = (
    REPO_ROOT
    / "workspace/private/inputs/boot_images/"
    "boot_linux_v3404_d3_resolved_owner_timeout.img"
)
EXPECTED_ACCEPTED_SHA256 = (
    "0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def builder_chain() -> list[Path]:
    chain: list[Path] = []
    current = ENTRYPOINT
    while current.exists() and current not in chain:
        chain.append(current)
        tree = ast.parse(current.read_text(encoding="utf-8"), filename=str(current))
        following = None
        for node in tree.body:
            if not isinstance(node, ast.Import):
                continue
            for alias in node.names:
                if alias.name.startswith("build_native_init_boot_"):
                    following = current.with_name(alias.name + ".py")
        if following is None:
            break
        current = following
    return chain


def audit() -> dict[str, object]:
    if not ACCEPTED_BOOT.is_file():
        raise RuntimeError(f"accepted boot missing: {ACCEPTED_BOOT}")
    accepted_sha = sha256(ACCEPTED_BOOT)
    if accepted_sha != EXPECTED_ACCEPTED_SHA256:
        raise RuntimeError(f"accepted boot changed: {accepted_sha}")
    chain = builder_chain()
    return {
        "schema": "a90-v3404-determinism-phase0-audit-v1",
        "entrypoint": str(ENTRYPOINT.relative_to(REPO_ROOT)),
        "builder_chain_count": len(chain),
        "builder_chain": [
            {"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)}
            for path in chain
        ],
        "accepted_boot": str(ACCEPTED_BOOT.relative_to(REPO_ROOT)),
        "accepted_boot_sha256": accepted_sha,
    }


def isolated_build(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"isolated output already exists: {output}")
    output.mkdir(parents=True, mode=0o700)
    sys.path.insert(0, str(SCRIPT_DIR))
    sys.argv = [str(ENTRYPOINT)]
    import build_native_init_boot_v3404_d3_resolved_owner_timeout as builder

    builder.OUT_DIR = output / "build"
    builder.OBJ_DIR = builder.OUT_DIR / "obj"
    builder.BOOT_IMAGE = output / "boot.img"
    builder.INIT_BINARY = builder.OUT_DIR / "init"
    builder.RAMDISK_CPIO = builder.OUT_DIR / "ramdisk.cpio"
    builder.HELPER_BINARY = builder.OUT_DIR / "helper"
    builder.ENGINE_BINARY = builder.OUT_DIR / "engine"
    builder.ENGINE_ADAPTER_SOURCE = builder.OUT_DIR / "engine-adapter.c"
    builder.ENGINE_ADAPTER_OBJECT = builder.OBJ_DIR / "engine-adapter.o"
    builder.SFX_BACKEND_SOURCE = builder.OUT_DIR / "sfx.c"
    builder.SDL_MIXER_STUB = builder.OUT_DIR / "SDL_mixer.h"
    builder.REPORT_PATH = output / "builder-report.md"
    return builder.main()


def artifacts(root: Path) -> dict[str, dict[str, object]]:
    names = {
        "boot": root / "boot.img",
        "ramdisk": root / "build/ramdisk.cpio",
        "init": root / "build/init",
        "helper": root / "build/helper",
        "engine": root / "build/engine",
    }
    result = {}
    for name, path in names.items():
        if not path.is_file():
            raise RuntimeError(f"missing {name}: {path}")
        result[name] = {"size": path.stat().st_size, "sha256": sha256(path)}
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--child-output", type=Path)
    args = parser.parse_args()
    os.environ.update({"LC_ALL": "C", "LANG": "C", "TZ": "UTC"})
    if args.child_output:
        return isolated_build(args.child_output.resolve())
    receipt = audit()
    if args.audit_only:
        print(json.dumps(receipt, indent=2, sort_keys=True))
        return 0
    if args.run_root is None:
        parser.error("--run-root is required")
    run_root = args.run_root.resolve()
    if run_root.exists():
        raise RuntimeError(f"run root must be absent: {run_root}")
    run_root.mkdir(parents=True, mode=0o700)
    for label in ("A", "B"):
        subprocess.run(
            [sys.executable, str(Path(__file__).resolve()),
             "--child-output", str(run_root / label)],
            check=True,
            env=os.environ,
        )
    a_artifacts = artifacts(run_root / "A")
    b_artifacts = artifacts(run_root / "B")
    receipt["artifacts"] = a_artifacts
    receipt["byte_identical"] = a_artifacts == b_artifacts
    receipt["accepted_boot_unchanged"] = sha256(ACCEPTED_BOOT)
    receipt_path = run_root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    os.chmod(receipt_path, 0o600)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["byte_identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
