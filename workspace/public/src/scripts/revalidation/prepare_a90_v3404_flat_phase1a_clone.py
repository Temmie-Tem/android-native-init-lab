#!/usr/bin/env python3
"""Prepare the minimal disposable V3404 flat-builder clone."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from _workspace_bootstrap import repo_root

REPO_ROOT = repo_root()
PRIVATE_OUTPUTS = REPO_ROOT / "workspace/private/outputs"
BOOT_NAMES = (
    "boot_linux_v3403_d3_immutable_handoff.img",
    "boot_linux_v3404_d3_resolved_owner_timeout.img",
)
EXPECTED_BOOT_SHA256 = {
    "boot_linux_v3403_d3_immutable_handoff.img":
        "2b2b458b4f021825e0567c239ef86996d482a7b55baccc4e4a8cd9e670a2e2b9",
    "boot_linux_v3404_d3_resolved_owner_timeout.img":
        "0a8827aeb46e2fb2cdf1e7cf7320626b4b3a43fcdbbff2024d92dcbc088e83d3",
}
DOOM_REL = Path("workspace/private/demo-assets/doom/doomgeneric-v3403")
V535_REL = Path(
    "workspace/private/runs/server-distro/"
    "a90-debian-reactivation-prep-20260730/rebuild-audit/"
    "source-v2321-commit/tmp/wifi/v535-rmt-storage-private-property-runtime"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_output(path: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(PRIVATE_OUTPUTS.resolve())
    if not resolved.name.startswith("a90-v3404-flat-phase1a-"):
        raise RuntimeError("unexpected disposable clone name")
    if resolved.exists():
        raise RuntimeError(f"clone output already exists: {resolved}")
    return resolved


def export_head(output: Path) -> None:
    output.mkdir(parents=True, mode=0o700)
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
    )
    assert archive.stdout is not None
    extract = subprocess.run(
        ["tar", "-xf", "-", "-C", str(output)],
        stdin=archive.stdout,
        check=False,
    )
    archive.stdout.close()
    archive_rc = archive.wait()
    if archive_rc or extract.returncode:
        raise RuntimeError(
            f"tracked export failed: git={archive_rc} tar={extract.returncode}"
        )


def copy_inputs(output: Path) -> dict[str, str]:
    copied: dict[str, str] = {}
    boot_root = output / "workspace/private/inputs/boot_images"
    boot_root.mkdir(parents=True, mode=0o700)
    for name in BOOT_NAMES:
        source = REPO_ROOT / "workspace/private/inputs/boot_images" / name
        target = boot_root / name
        if not source.is_file() or source.is_symlink():
            raise RuntimeError(f"invalid boot input: {source}")
        digest = sha256(source)
        expected = EXPECTED_BOOT_SHA256.get(name)
        if expected and digest != expected:
            raise RuntimeError(f"boot input changed: {name} {digest}")
        shutil.copy2(source, target)
        copied[str(target.relative_to(output))] = digest
    for relative in (DOOM_REL, V535_REL):
        source = REPO_ROOT / relative
        target = output / relative
        if not source.is_dir() or source.is_symlink():
            raise RuntimeError(f"invalid private input directory: {source}")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        shutil.copytree(source, target, copy_function=shutil.copy2)
    return copied


def sandbox_fault_test(output: Path) -> None:
    probe = (
        "from pathlib import Path; "
        f"assert not Path({str(REPO_ROOT)!r}).exists(); "
        "p=Path('/work/workspace/private/outputs/sandbox-write-ok'); "
        "p.parent.mkdir(parents=True,exist_ok=True); p.write_text('ok'); "
        "assert p.read_text()=='ok'"
    )
    command = [
        "bwrap", "--unshare-all", "--die-with-parent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--ro-bind", "/etc", "/etc",
        "--proc", "/proc", "--dev", "/dev",
        "--tmpfs", "/tmp", "--dir", "/tmp/home",
        "--bind", str(output), "/work",
        "--chdir", "/work", "--setenv", "HOME", "/tmp/home",
        "--setenv", "LC_ALL", "C", "--setenv", "LANG", "C",
        "--setenv", "TZ", "UTC",
        "/usr/bin/python3", "-c", probe,
    ]
    subprocess.run(command, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = require_output(args.output)
    export_head(output)
    copied = copy_inputs(output)
    canonical = str(REPO_ROOT.resolve())
    for path in (output / "workspace/public").rglob("*"):
        if path.is_file() and not path.is_symlink():
            try:
                if canonical in path.read_text(encoding="utf-8"):
                    raise RuntimeError(f"canonical path embedded in tracked source: {path}")
            except UnicodeDecodeError:
                continue
    sandbox_fault_test(output)
    receipt = {
        "schema": "a90-v3404-flat-phase1a-clone-v1",
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip(),
        "inputs": copied,
        "canonical_repo_hidden": True,
        "sandbox_fault_test": "pass",
    }
    receipt_path = output / "workspace/private/outputs/clone-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    receipt_path.chmod(0o600)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
