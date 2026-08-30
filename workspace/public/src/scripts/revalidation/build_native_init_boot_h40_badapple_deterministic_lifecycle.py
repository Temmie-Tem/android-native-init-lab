#!/usr/bin/env python3
"""Build H40 with cold-boot sibling readiness and deterministic demo lifecycle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root


REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_h38_badapple_boot_chime_serialized as h38


CYCLE = "H40"
INIT_VERSION = "0.12.006"
INIT_BUILD = "h40-badapple-deterministic-lifecycle-v3"
OUT_DIR = workspace_private_build_path("native-init", INIT_BUILD)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_h40_badapple_deterministic_lifecycle_v3.img", legacy_fallback=False
)
REPORT_PATH = REPO_ROOT / "docs/reports/A90_H40_BADAPPLE_DETERMINISTIC_LIFECYCLE_H0_2026-08-30.md"
HAZARD_ID = "A90_H40_EXPLICIT_SIBLING_SSCTL_DETERMINISTIC_DEMO_TEMPORARY_CANDIDATE"
HAZARD_STATEMENT = (
    "H40 preserves the exact V3402 non-init boot components and private Bad Apple engine, "
    "replays the H37 firmware-backed ADSP/CDSP/SLPI cold-boot prerequisite sequence without "
    "the consumed cache flag, starts the tracked boot chime before the interactive HUD fork, "
    "and adds a deterministic physical demo lifecycle with immediate acknowledgement, "
    "worker-bound audio sync, bounded fail-fast/cancel, single input ownership, and a single "
    "cleanup path with fresh input reopen before menu return; all H40 runtime behavior remains "
    "unproved until one attended run."
)
HAZARD_STATEMENT_SHA256 = "6c88727473c0a00bc2b41481ccc08a643ffb678aa724d47eb623180c6f1a1f44"
MOUNT_FLAG = "-DA90_BADAPPLE_BOOT_AUDIO_FIRMWARE_MOUNTS=1"
SIBLING_FLAG = "-DA90_BADAPPLE_BOOT_EXPLICIT_SIBLING_SSCTL=1"


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# A90 H40 Bad Apple Deterministic Lifecycle H0",
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
        "- Replays the H37 firmware mount plus ADSP/CDSP/SLPI one-shot cold-boot sequence explicitly.",
        "- Starts the tracked boot-chime worker before forking the interactive HUD.",
        "- Shows a visible STARTING frame before menu work blocks.",
        "- Releases HUD input ownership while the video player owns physical cancellation.",
        "- Binds video sync to the exact spawned audio worker PID and limits readiness to 10 seconds.",
        "- Treats worker completion-before-ready as failure and accepts physical cancel during sync.",
        "- Stops audio on every demo return, reports failure visibly, reopens fresh HUD input, and restores the menu.",
        "",
        "## Boundary",
        "",
        "- Independent review rejected v2's HUD-before-chime fork order; v3 reverses that order.",
        "- H37 playback and H39 timeout are evidence for their own runs only.",
        "- H40 cold-boot subsystem readiness, boot chime, physical input lifecycle, audio/video playback, cleanup, and final health remain unproved.",
        "- The 10-second budget is a user-facing failure bound, not proof that audio will become ready.",
        "",
        "## Candidate hazard binding",
        "",
        f"- Hazard ID: `{HAZARD_ID}`",
        f"- Statement: `{HAZARD_STATEMENT}`",
        f"- Statement SHA256: `{HAZARD_STATEMENT_SHA256}`",
        "- Acceptance qualifies only these exact temporary-candidate bytes; it grants no live authority.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Required init flags: `{MOUNT_FLAG}, {SIBLING_FLAG}`",
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
    h38.INIT_BINARY = OUT_DIR / "init_h40_badapple_deterministic_lifecycle_v3"
    h38.RAMDISK_CPIO = OUT_DIR / "ramdisk_h40_badapple_deterministic_lifecycle_v3.cpio"
    h38.ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3402"
    h38.ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_h40_v3.c"
    h38.ENGINE_ADAPTER_OBJECT = h38.OBJ_DIR / "a90_doomgeneric_native_bridge_h40_v3.o"
    h38.SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_h40_v3.c"
    h38.SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
    h38.FALLBACK_EXPECTED_INIT_FLAG_COUNT = 61
    h38.FALLBACK_CYCLE_LABEL = "h40v3"
    h38.FALLBACK_REQUIRED_INIT_FLAGS = (
        "-DAUDIO_CHIME_BOOT_AUTOPLAY_DEFAULT=1",
        MOUNT_FLAG,
        SIBLING_FLAG,
    )
    h38.FALLBACK_REQUIRED_MARKERS = (
        b"audio.boot_prereq.firmware_mounts.cache_flag_required=0",
        b"audio.boot_prereq.sibling_ssctl.cache_flag_required=0",
        b"video.stream.audio_sync.worker_done_before_ready=1",
        b"video.stream.audio_sync.cancelled_by_physical_input=1",
        b"video.stream.physical_exit.required=1 open_rc=%d",
        b"menu.demo.badapple.input_reopened=1",
    )
    h38.BUILD_MANIFEST_SCHEMA = "a90-h40-badapple-deterministic-lifecycle-build-v3"
    h38.CLAIM_BOUNDARY = (
        "H0 build does not prove cold-boot subsystem readiness, chime, physical demo playback, cleanup, rollback, or final health"
    )
    h38.CONSTRUCTION_EXTRAS = {
        "explicitAudioFirmwareMounts": True,
        "explicitSiblingSsctl": ["adsp", "cdsp", "slpi"],
        "bootChimeBeforeInteractiveHudFork": True,
        "audioSyncWorkerPidBound": True,
        "audioSyncWaitMs": 10000,
        "physicalCancelDuringSync": True,
        "freshInputReopen": True,
        "runtimeState": "unproved",
    }
    h38.render_report = render_report


def main() -> int:
    configure()
    original_fallback = h38._fallback_build_from_exact_v3402

    def h40_fallback(base_module: Any) -> int:
        original_flags = base_module.EXTRA_INIT_FLAGS
        base_module.EXTRA_INIT_FLAGS = tuple(original_flags) + (MOUNT_FLAG, SIBLING_FLAG)
        try:
            return original_fallback(base_module)
        finally:
            base_module.EXTRA_INIT_FLAGS = original_flags

    h38._fallback_build_from_exact_v3402 = h40_fallback
    try:
        return h38.main()
    finally:
        h38._fallback_build_from_exact_v3402 = original_fallback


if __name__ == "__main__":
    raise SystemExit(main())
