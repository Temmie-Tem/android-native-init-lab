#!/usr/bin/env python3
"""Build fresh H41 identity from the reviewed H40 deterministic demo source."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root


REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_h40_badapple_deterministic_lifecycle as h40


h38 = h40.h38
CYCLE = "H41"
INIT_VERSION = "0.12.008"
INIT_BUILD = "h41-badapple-video-demo-v2"
OUT_DIR = workspace_private_build_path("native-init", INIT_BUILD)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_h41_badapple_video_demo_v2.img", legacy_fallback=False
)
REPORT_PATH = REPO_ROOT / "docs/reports/A90_H41_BADAPPLE_VIDEO_DEMO_H0_2026-08-30.md"
HAZARD_ID = "A90_H41_DETERMINISTIC_BADAPPLE_VIDEO_EVIDENCE_TEMPORARY_CANDIDATE"
HAZARD_STATEMENT = (
    "H41 gives the reviewed H40 v3 deterministic Bad Apple lifecycle a fresh candidate "
    "identity without changing its runtime source: exact V3402 non-init boot components, "
    "explicit firmware mounts and ADSP/CDSP/SLPI prerequisites, tracked PID1 boot chime "
    "before the interactive HUD fork, immediate STARTING acknowledgement, worker-bound "
    "10-second audio sync, physical cancellation, single input ownership, and cleanup plus "
    "fresh input reopen remain required; H41 boot, playback, cleanup, and health are unproved "
    "until one attended run."
)
HAZARD_STATEMENT_SHA256 = hashlib.sha256(HAZARD_STATEMENT.encode("utf-8")).hexdigest()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# A90 H41 Bad Apple Video Demo H0",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{manifest.get('boot_image', h38.base.rel(BOOT_IMAGE))}`",
        f"- Boot SHA256: `{manifest.get('boot_sha256', '')}`",
        f"- Base boot: `{h38.base.rel(h38.BASE_BOOT)}`",
        "- Device action: `none`",
        "- Runtime result: `unproved`",
        "",
        "## Scope",
        "",
        "- Uses the current H40 v3 runtime source unchanged apart from the fresh version/build identity.",
        "- Keeps the reviewed firmware, sibling-SSCTL, boot-chime ordering, worker sync, input ownership, and cleanup lifecycle.",
        "- Exists only for one attended manual Bad Apple evidence attempt followed by the ordinary safety outcome.",
        "",
        "## Boundary",
        "",
        "- H37 audio/video observation, H39 timeouts, and H40's unproved runtime do not prove H41.",
        "- Build equality and source reuse do not prove boot, audio, video, physical input, cleanup, or final health.",
        "- H40 candidate and rollback attempts remain consumed and are never replayed.",
        "",
        "## Candidate hazard binding",
        "",
        f"- Hazard ID: `{HAZARD_ID}`",
        f"- Statement: `{HAZARD_STATEMENT}`",
        f"- Statement SHA256: `{HAZARD_STATEMENT_SHA256}`",
        "- Acceptance qualifies only the exact H41 bytes and grants no live authority.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Required init flags: `{h40.MOUNT_FLAG}, {h40.SIBLING_FLAG}`",
        f"- Init extra flag count: `{len(init_extra_flags)}`",
    ]) + "\n"


def configure() -> None:
    h40.configure()
    h38.CYCLE = CYCLE
    h38.INIT_VERSION = INIT_VERSION
    h38.INIT_BUILD = INIT_BUILD
    h38.BUILD_TAG = INIT_BUILD
    h38.OUT_DIR = OUT_DIR
    h38.OBJ_DIR = OUT_DIR / "obj"
    h38.REPORT_PATH = REPORT_PATH
    h38.BOOT_IMAGE = BOOT_IMAGE
    h38.INIT_BINARY = OUT_DIR / "init_h41_badapple_video_demo_v2"
    h38.RAMDISK_CPIO = OUT_DIR / "ramdisk_h41_badapple_video_demo_v2.cpio"
    h38.ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3402"
    h38.ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_h41_v2.c"
    h38.ENGINE_ADAPTER_OBJECT = h38.OBJ_DIR / "a90_doomgeneric_native_bridge_h41_v2.o"
    h38.SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_h41_v2.c"
    h38.SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
    h38.FALLBACK_CYCLE_LABEL = "h40v3"
    h38.BUILD_MANIFEST_SCHEMA = "a90-h41-badapple-video-demo-build-v2"
    h38.CLAIM_BOUNDARY = (
        "H0 build does not prove H41 boot, audio/video playback, physical input, cleanup, rollback, or final health"
    )
    h38.CONSTRUCTION_EXTRAS = {
        **h38.CONSTRUCTION_EXTRAS,
        "sourceRuntimeDeltaFromH40V3": "version-and-build-identity-only",
        "runtimeState": "unproved",
    }
    h38.render_report = render_report


def main() -> int:
    configure()
    original_fallback = h38._fallback_build_from_exact_v3402

    def h41_fallback(base_module: Any) -> int:
        original_flags = base_module.EXTRA_INIT_FLAGS
        base_module.EXTRA_INIT_FLAGS = tuple(original_flags) + (
            h40.MOUNT_FLAG,
            h40.SIBLING_FLAG,
        )
        try:
            return original_fallback(base_module)
        finally:
            base_module.EXTRA_INIT_FLAGS = original_flags

    h38._fallback_build_from_exact_v3402 = h41_fallback
    try:
        return h38.main()
    finally:
        h38._fallback_build_from_exact_v3402 = original_fallback


if __name__ == "__main__":
    raise SystemExit(main())
