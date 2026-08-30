#!/usr/bin/env python3
"""Repackage a fresh A90 H36 Bad Apple evidence-video candidate.

The candidate combines a previously boot-proven stock-kernel carrier with a
retained, previously device-proven Bad Apple native-init binary. Only the
equal-length version/build identity strings are changed. The combination is
new and remains unproved until one fresh attended F1 run.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from _workspace_bootstrap import repo_root


ROOT = repo_root()
CYCLE = "H36"
INIT_VERSION = "0.12.0"
INIT_BUILD = "h36-badapple-video-evidence-demo-v1"
OLD_VERSION = "0.11.6"
OLD_BUILD = "v3163-badapple-nyan-cleanup-cadence"

BASE_BOOT = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img"
BASE_BOOT_SIZE = 66_379_776
BASE_BOOT_SHA256 = "57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1"
SOURCE_INIT = ROOT / "workspace/private/builds/native-init/v3163-badapple-nyan-cleanup-cadence/init_v3163_badapple_nyan_cleanup_cadence"
SOURCE_INIT_SIZE = 1_461_520
SOURCE_INIT_SHA256 = "758ca77ad1e496dd722d17f8b24b972c4e9fa69d3786be7c1b70e232ad911e90"
MAGISKBOOT = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
STREAM = ROOT / "workspace/private/demo-assets/video/v2903-badapple-480x360-full/video-stream/frames.a90vstr"
STREAM_SIZE = 150_490_668
STREAM_SHA256 = "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0"

OUT_DIR = ROOT / "workspace/private/builds/native-init/h36-badapple-evidence-repack-v1"
WORK_DIR = OUT_DIR / "unpack"
VERIFY_DIR = OUT_DIR / "verify"
PATCHED_INIT = OUT_DIR / "init_h36_badapple_evidence"
BOOT_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_h36_badapple_evidence_repack.img"
MANIFEST = OUT_DIR / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, size: int, digest: str, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise RuntimeError(f"{label} is not a direct regular file")
    if path.stat().st_size != size or sha256(path) != digest:
        raise RuntimeError(f"{label} identity mismatch")


def run(command: list[str], cwd: Path, label: str) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed rc={completed.returncode}: {completed.stdout}")
    return completed.stdout


def patch_identity() -> dict[str, object]:
    if len(OLD_VERSION) != len(INIT_VERSION) or len(OLD_BUILD) != len(INIT_BUILD):
        raise RuntimeError("identity replacements are not equal-length")
    source = SOURCE_INIT.read_bytes()
    old_version = OLD_VERSION.encode()
    old_build = OLD_BUILD.encode()
    if source.count(old_version) != 2 or source.count(old_build) != 2:
        raise RuntimeError("retained init identity occurrence count changed")
    patched = source.replace(old_version, INIT_VERSION.encode()).replace(old_build, INIT_BUILD.encode())
    if len(patched) != len(source) or old_version in patched or old_build in patched:
        raise RuntimeError("identity-only patch invariant failed")
    PATCHED_INIT.write_bytes(patched)
    PATCHED_INIT.chmod(0o750)
    return {
        "source_sha256": SOURCE_INIT_SHA256,
        "patched_sha256": sha256(PATCHED_INIT),
        "size": len(patched),
        "version_replacements": 2,
        "build_replacements": 2,
    }


def main() -> int:
    require_file(BASE_BOOT, BASE_BOOT_SIZE, BASE_BOOT_SHA256, "base boot")
    require_file(SOURCE_INIT, SOURCE_INIT_SIZE, SOURCE_INIT_SHA256, "retained V3163 init")
    require_file(STREAM, STREAM_SIZE, STREAM_SHA256, "retained Bad Apple stream")
    if not MAGISKBOOT.is_file() or MAGISKBOOT.is_symlink():
        raise RuntimeError("pinned magiskboot is unavailable")
    if OUT_DIR.exists() or BOOT_IMAGE.exists():
        raise RuntimeError("H36 output already exists; refusing to clobber")

    WORK_DIR.mkdir(parents=True)
    VERIFY_DIR.mkdir(parents=True)
    identity = patch_identity()
    unpack = run([str(MAGISKBOOT), "unpack", "-h", str(BASE_BOOT)], WORK_DIR, "base unpack")
    ramdisk = WORK_DIR / "ramdisk.cpio"
    if not ramdisk.is_file():
        raise RuntimeError("base ramdisk.cpio is absent")
    run([str(MAGISKBOOT), "cpio", str(ramdisk), f"add 750 init {PATCHED_INIT}"], WORK_DIR, "replace init")
    run([str(MAGISKBOOT), "repack", str(BASE_BOOT), str(BOOT_IMAGE)], WORK_DIR, "candidate repack")

    verify_unpack = run([str(MAGISKBOOT), "unpack", "-h", str(BOOT_IMAGE)], VERIFY_DIR, "candidate unpack")
    extracted = VERIFY_DIR / "init.extracted"
    run([str(MAGISKBOOT), "cpio", str(VERIFY_DIR / "ramdisk.cpio"), f"extract init {extracted}"], VERIFY_DIR, "candidate init extract")
    if sha256(extracted) != identity["patched_sha256"] or extracted.read_bytes() != PATCHED_INIT.read_bytes():
        raise RuntimeError("repacked init differs from the identity-patched input")
    candidate_bytes = BOOT_IMAGE.read_bytes()
    required = (
        f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})".encode(),
        b"badapple-480x360-full-v2903",
        STREAM_SHA256.encode(),
        b"player-hud",
        b"video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom] [status|verify|play] [--trust-cache]",
    )
    missing = [item.decode(errors="replace") for item in required if item not in candidate_bytes]
    if missing:
        raise RuntimeError(f"candidate markers missing: {missing}")

    manifest = {
        "schema": "a90-h36-badapple-evidence-repack-v1",
        "cycle": CYCLE,
        "candidateAuthority": False,
        "candidate": {"path": str(BOOT_IMAGE), "size": BOOT_IMAGE.stat().st_size, "sha256": sha256(BOOT_IMAGE), "version": INIT_VERSION, "build": INIT_BUILD},
        "construction": {
            "classification": "designed-unproved",
            "baseBoot": {"size": BASE_BOOT_SIZE, "sha256": BASE_BOOT_SHA256},
            "retainedInit": identity,
            "mutation": "equal-length version/build strings only; replace ramdisk /init only",
            "magiskboot": str(MAGISKBOOT),
            "unpackOutputSha256": hashlib.sha256(unpack.encode()).hexdigest(),
            "verifyUnpackOutputSha256": hashlib.sha256(verify_unpack.encode()).hexdigest(),
            "extractedInitMatches": True,
        },
        "intendedObservation": {"demo": "badapple", "frames": 300, "layout": "player-hud", "present": "pageflip", "audio": False, "stream": {"size": STREAM_SIZE, "sha256": STREAM_SHA256}},
        "rollback": {"version": "0.9.285", "build": "v2321-usb-clean-identity-rodata", "size": 60_882_944, "sha256": "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"},
        "claimBoundary": "build PASS does not prove boot, cache presence, playback, display, or final health",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
