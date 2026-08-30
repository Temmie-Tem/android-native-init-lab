#!/usr/bin/env python3
"""Build H39 with explicit firmware mounts before tracked boot chime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root


REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_h38_badapple_boot_chime_serialized as h38


CYCLE = "H39"
INIT_VERSION = "0.12.003"
INIT_BUILD = "h39-badapple-audio-prereq-v1"
OUT_DIR = workspace_private_build_path("native-init", INIT_BUILD + "-v2")
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_h39_badapple_audio_prereq_v2.img", legacy_fallback=False
)
REPORT_PATH = REPO_ROOT / "docs/reports/A90_H39_BADAPPLE_AUDIO_PREREQ_H0_2026-08-30.md"
HAZARD_ID = "A90_H39_EXPLICIT_AUDIO_FIRMWARE_MOUNTS_TEMPORARY_EVIDENCE_CANDIDATE"
HAZARD_STATEMENT = (
    "H39 preserves the H38 tracked-worker repair and exact V3402 non-init boot components, "
    "but explicitly prepares the reviewed read-only APNHLOS/modem firmware mounts before boot "
    "chime without relying on the consumed cache flag; cold-boot audio initialization, physical "
    "Bad Apple playback, rollback, and final health remain unproved until one attended boot-only F1 run."
)
HAZARD_STATEMENT_SHA256 = "bf4d74b62aa484caf0f69f4e395ceb8505b03a6ecc6efbfb9b0b97b05fa52104"
EXTRA_FLAG = "-DA90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS=1"


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# A90 H39 Bad Apple Audio Prerequisite H0",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{manifest.get('boot_image', h38.base.rel(BOOT_IMAGE))}`",
        f"- Boot SHA256: `{manifest.get('boot_sha256', '')}`",
        f"- Base boot: `{h38.base.rel(h38.BASE_BOOT)}`",
        "- Device action: `none`",
        "- Runtime result: `unproved`",
        "",
        "## Change",
        "",
        "- Preserves H38's PID1-tracked asynchronous boot-chime worker.",
        "- Calls the existing read-only APNHLOS/modem firmware mount preparation before boot chime.",
        "- Removes dependence on the consumed `/cache/native-init-sibling-fwssctl-v641` flag for audio prerequisites.",
        "- Emits `audio.boot_prereq.firmware_mounts.*` receipts before the chime launch.",
        "",
        "## Boundary",
        "",
        "- The mount call is designed and host-built, not runtime-proved for H39.",
        "- This build does not prove `/dev/snd`, ADSP readiness, boot chime, Bad Apple playback, rollback, or final health.",
        "- H38's failed playback is evidence for its own run only and is not promoted into H39 success.",
        "",
        "## Candidate hazard binding",
        "",
        f"- Hazard ID: `{HAZARD_ID}`",
        f"- Statement: `{HAZARD_STATEMENT}`",
        f"- Statement SHA256: `{HAZARD_STATEMENT_SHA256}`",
        "- Acceptance at H0 would qualify only an explicit temporary-candidate risk; it grants no live authority.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags include: `{EXTRA_FLAG}`",
        f"- Init extra flag count: `{len(init_extra_flags)}`",
    ]) + "\n"


def configure() -> None:
    h38.CYCLE = CYCLE
    h38.INIT_VERSION = INIT_VERSION
    h38.INIT_BUILD = INIT_BUILD
    h38.BUILD_TAG = INIT_BUILD
    h38.OUT_DIR = OUT_DIR
    h38.OBJ_DIR = OUT_DIR / "obj"
    h38.REPORT_PATH = REPORT_PATH
    h38.BOOT_IMAGE = BOOT_IMAGE
    h38.INIT_BINARY = OUT_DIR / "init_h39_badapple_audio_prereq"
    h38.RAMDISK_CPIO = OUT_DIR / "ramdisk_h39_badapple_audio_prereq.cpio"
    h38.ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3402"
    h38.ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_h39.c"
    h38.ENGINE_ADAPTER_OBJECT = h38.OBJ_DIR / "a90_doomgeneric_native_bridge_h39.o"
    h38.SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_h39.c"
    h38.SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
    h38.FALLBACK_EXPECTED_INIT_FLAG_COUNT = 60
    h38.FALLBACK_CYCLE_LABEL = "h39"
    h38.FALLBACK_REQUIRED_INIT_FLAGS = (
        "-DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1",
        EXTRA_FLAG,
    )
    h38.FALLBACK_REQUIRED_MARKERS = (
        b"audio.boot_prereq.firmware_mounts.explicit=1",
        b"audio.boot_prereq.firmware_mounts.cache_flag_required=0",
    )
    h38.BUILD_MANIFEST_SCHEMA = "a90-h39-badapple-audio-prereq-build-v1"
    h38.CLAIM_BOUNDARY = (
        "H0 build does not prove firmware mounts, sound nodes, ADSP, chime, playback, rollback, or final health"
    )
    h38.CONSTRUCTION_EXTRAS = {
        "explicitAudioFirmwareMounts": True,
        "cacheFlagRequired": False,
        "runtimeState": "unproved",
    }
    h38.render_report = render_report


def main() -> int:
    configure()
    original_fallback = h38._fallback_build_from_exact_v3402

    def h39_fallback(base_module: Any) -> int:
        original_flags = base_module.EXTRA_INIT_FLAGS
        base_module.EXTRA_INIT_FLAGS = tuple(original_flags) + (EXTRA_FLAG,)
        try:
            return original_fallback(base_module)
        finally:
            base_module.EXTRA_INIT_FLAGS = original_flags

    h38._fallback_build_from_exact_v3402 = h39_fallback
    try:
        return h38.main()
    finally:
        h38._fallback_build_from_exact_v3402 = original_fallback


if __name__ == "__main__":
    raise SystemExit(main())
