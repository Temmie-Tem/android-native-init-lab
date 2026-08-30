#!/usr/bin/env python3
"""Build the fresh A90 H37 temporary Bad Apple evidence candidate.

The exact live-proven V3402 image is unpacked, and only the resident banner plus
its standalone version occurrence inside the existing ramdisk are replaced. No cpio
entry is added or removed, preserving the complete V3402 ramdisk closure and
metadata.  The resulting H37 combination remains unproved until live use.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from _workspace_bootstrap import repo_root


ROOT = repo_root()
CYCLE = "H37"
OLD_VERSION = "0.11.158"
OLD_BUILD = "v3402-dpublic-hud-presenter-restart-policy"
INIT_VERSION = "0.12.001"
INIT_BUILD = "h37-badapple-video-evidence-temporary-v001"

BASE_BOOT = ROOT / "workspace/private/inputs/boot_images/boot_linux_v3402_dpublic_hud_presenter_restart_policy.img"
BASE_BOOT_SIZE = 66_379_776
BASE_BOOT_SHA256 = "57821e94857cb58b397c737a73d5f85381329f5e9ec8a6b55dc7d5dbb6a7d3f1"
MAGISKBOOT = ROOT / "workspace/private/tools/magisk-v30.7/magiskboot"
MAGISKBOOT_SIZE = 943_848
MAGISKBOOT_SHA256 = "a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e"
STREAM = ROOT / "workspace/private/demo-assets/video/v2903-badapple-480x360-full/video-stream/frames.a90vstr"
STREAM_SIZE = 150_490_668
STREAM_SHA256 = "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0"

OUT_DIR = ROOT / "workspace/private/builds/native-init/h37-badapple-evidence-v1"
BASE_DIR = OUT_DIR / "base"
CANDIDATE_DIR = OUT_DIR / "candidate"
BASE_INIT = OUT_DIR / "init.v3402"
PATCHED_INIT = OUT_DIR / "init.h37"
BOOT_IMAGE = ROOT / "workspace/private/inputs/boot_images/boot_linux_h37_badapple_evidence.img"
MANIFEST = OUT_DIR / "manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, size: int, digest: str, label: str) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
        raise RuntimeError(f"{label} is not one direct regular file")
    if path.stat().st_size != size or sha256(path) != digest:
        raise RuntimeError(f"{label} identity mismatch")


def run(command: list[str], cwd: Path, label: str) -> bytes:
    completed = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} failed rc={completed.returncode}: {completed.stdout.decode(errors='replace')}")
    return completed.stdout


def component_receipts(directory: Path) -> dict[str, dict[str, object]]:
    return {
        path.name: {"size": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(directory.iterdir())
        if path.is_file()
        and path.name != "ramdisk.cpio"
        and not path.name.startswith("init.")
    }


def normalize_cpio_listing(raw: bytes) -> bytes:
    return b"\n".join(
        line for line in raw.splitlines() if not line.startswith(b"Loading cpio:")
    )


def main() -> int:
    require_file(BASE_BOOT, BASE_BOOT_SIZE, BASE_BOOT_SHA256, "V3402 base boot")
    require_file(MAGISKBOOT, MAGISKBOOT_SIZE, MAGISKBOOT_SHA256, "magiskboot")
    require_file(STREAM, STREAM_SIZE, STREAM_SHA256, "Bad Apple stream")
    if len(OLD_VERSION) != len(INIT_VERSION) or len(OLD_BUILD) != len(INIT_BUILD):
        raise RuntimeError("H37 identity replacements are not equal-length")
    if OUT_DIR.exists() or BOOT_IMAGE.exists():
        raise RuntimeError("H37 output exists; refusing to clobber")

    BASE_DIR.mkdir(parents=True)
    CANDIDATE_DIR.mkdir(parents=True)
    base_unpack = run([str(MAGISKBOOT), "unpack", "-h", str(BASE_BOOT)], BASE_DIR, "base unpack")
    base_ramdisk = BASE_DIR / "ramdisk.cpio"
    base_listing = run([str(MAGISKBOOT), "cpio", str(base_ramdisk), "ls -r /"], BASE_DIR, "base cpio listing")
    run([str(MAGISKBOOT), "cpio", str(base_ramdisk), f"extract init {BASE_INIT}"], BASE_DIR, "base init extract")
    source_init = BASE_INIT.read_bytes()
    old_banner = f"A90 Linux init {OLD_VERSION} ({OLD_BUILD})".encode()
    new_banner = f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})".encode()
    if (
        len(old_banner) != len(new_banner)
        or source_init.count(old_banner) != 1
        or source_init.count(OLD_VERSION.encode()) != 2
        or source_init.count(OLD_BUILD.encode()) != 2
    ):
        raise RuntimeError("V3402 init identity occurrence count changed")

    ramdisk = base_ramdisk.read_bytes()
    if ramdisk.count(old_banner) != 1 or ramdisk.count(OLD_VERSION.encode()) != 2:
        raise RuntimeError("resident identity strings are not exact in the ramdisk")
    patched_ramdisk = ramdisk.replace(old_banner, new_banner, 1)
    if patched_ramdisk.count(OLD_VERSION.encode()) != 1:
        raise RuntimeError("standalone V3402 version occurrence is not unique")
    patched_ramdisk = patched_ramdisk.replace(OLD_VERSION.encode(), INIT_VERSION.encode(), 1)
    if len(patched_ramdisk) != len(ramdisk):
        raise RuntimeError("ramdisk size changed during identity patch")
    base_ramdisk.write_bytes(patched_ramdisk)
    run([str(MAGISKBOOT), "cpio", str(base_ramdisk), f"extract init {PATCHED_INIT}"], BASE_DIR, "patched init extract")
    expected_init = source_init.replace(old_banner, new_banner, 1)
    expected_init = expected_init.replace(OLD_VERSION.encode(), INIT_VERSION.encode(), 1)
    if PATCHED_INIT.read_bytes() != expected_init:
        raise RuntimeError("patched cpio init differs from exact expected identity substitution")

    run([str(MAGISKBOOT), "repack", str(BASE_BOOT), str(BOOT_IMAGE)], BASE_DIR, "candidate repack")
    candidate_unpack = run([str(MAGISKBOOT), "unpack", "-h", str(BOOT_IMAGE)], CANDIDATE_DIR, "candidate unpack")
    candidate_ramdisk = CANDIDATE_DIR / "ramdisk.cpio"
    candidate_listing = run([str(MAGISKBOOT), "cpio", str(candidate_ramdisk), "ls -r /"], CANDIDATE_DIR, "candidate cpio listing")
    extracted = CANDIDATE_DIR / "init.h37.extracted"
    run([str(MAGISKBOOT), "cpio", str(candidate_ramdisk), f"extract init {extracted}"], CANDIDATE_DIR, "candidate init extract")
    if (
        extracted.read_bytes() != expected_init
        or normalize_cpio_listing(base_listing)
        != normalize_cpio_listing(candidate_listing)
    ):
        raise RuntimeError("candidate init or complete cpio metadata listing differs")
    if component_receipts(BASE_DIR) != component_receipts(CANDIDATE_DIR):
        raise RuntimeError("non-ramdisk boot components differ from V3402")

    candidate = BOOT_IMAGE.read_bytes()
    required = (
        f"A90 Linux init {INIT_VERSION} ({INIT_BUILD})".encode(),
        b"badapple-480x360-full-v2903",
        STREAM_SHA256.encode(),
        b"video.status.next_demo=video demo [badapple|badapple-scale|nyan|doom] [status|verify|play] [--trust-cache]",
        b"player-hud",
    )
    missing = [value.decode(errors="replace") for value in required if value not in candidate]
    preserved_engine_marker = b"doomgeneric-private-link-v3402-dpublic-hud-presenter-restart-policy"
    if missing or OLD_VERSION.encode() in candidate or preserved_engine_marker not in candidate:
        raise RuntimeError(f"candidate marker validation failed: {missing}")

    value = {
        "schema": "a90-h37-badapple-evidence-build-v1",
        "cycle": CYCLE,
        "candidateAuthority": False,
        "candidate": {"path": str(BOOT_IMAGE), "size": BOOT_IMAGE.stat().st_size, "sha256": sha256(BOOT_IMAGE), "version": INIT_VERSION, "build": INIT_BUILD},
        "construction": {
            "classification": "designed-unproved",
            "baseBoot": {"size": BASE_BOOT_SIZE, "sha256": BASE_BOOT_SHA256},
            "magiskboot": {"size": MAGISKBOOT_SIZE, "sha256": MAGISKBOOT_SHA256},
            "baseInit": {"size": BASE_INIT.stat().st_size, "sha256": sha256(BASE_INIT)},
            "patchedInit": {"size": PATCHED_INIT.stat().st_size, "sha256": sha256(PATCHED_INIT)},
            "identityOccurrences": {"version": 2, "residentBuild": 1},
            "preservedEngineMarker": preserved_engine_marker.decode(),
            "ramdiskSizeUnchanged": True,
            "completeCpioMetadataListingUnchanged": True,
            "nonRamdiskComponentsByteIdentical": True,
            "baseUnpackOutputSha256": hashlib.sha256(base_unpack).hexdigest(),
            "candidateUnpackOutputSha256": hashlib.sha256(candidate_unpack).hexdigest(),
        },
        "intendedPhysicalObservation": {
            "input": "operator-physical-button-menu-selection",
            "demo": "badapple",
            "menuAction": "play-av-fullsong",
            "frames": 6962,
            "layout": "player-hud",
            "present": "setcrtc",
            "audio": "menu-integrated-fullsong",
            "pcmPath": "/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
            "videoSkippedIfAudioStartFails": True,
            "stream": {"size": STREAM_SIZE, "sha256": STREAM_SHA256},
            "currentDeviceCachePcmAndPlayback": "unproved",
        },
        "rollback": {"version": "0.9.285", "build": "v2321-usb-clean-identity-rodata", "size": 60_882_944, "sha256": "ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb"},
        "claimBoundary": "H0 build PASS does not prove boot, device cache, playback, display, rollback, or final health",
    }
    MANIFEST.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
