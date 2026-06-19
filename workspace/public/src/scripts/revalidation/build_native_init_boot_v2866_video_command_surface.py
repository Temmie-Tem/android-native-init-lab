#!/usr/bin/env python3
"""Build V2866 native-init video command surface candidate.

V2866 keeps the latest V2859 audio/productization baseline and adds the first
native `video` command surface: read-only `video status` plus bounded KMS
single-frame `video frame` rendering. Live validation is a separate V-iteration.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2866"
INIT_VERSION = "0.10.20"
INIT_BUILD = "v2866-video-command-surface"
BUILD_TAG = INIT_BUILD
DECISION = "v2866-video-command-surface-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2866_VIDEO_COMMAND_SURFACE_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2866_video_command_surface.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2866_video_command_surface"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2866_video_command_surface.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v454_video_command_surface"


def configure_base_for_v2866() -> None:
    v2859.CYCLE = CYCLE
    v2859.INIT_VERSION = INIT_VERSION
    v2859.INIT_BUILD = INIT_BUILD
    v2859.BUILD_TAG = BUILD_TAG
    v2859.DECISION = DECISION
    v2859.OUT_DIR = OUT_DIR
    v2859.REPORT_PATH = REPORT_PATH
    v2859.BOOT_IMAGE = BOOT_IMAGE
    v2859.INIT_BINARY = INIT_BINARY
    v2859.RAMDISK_CPIO = RAMDISK_CPIO
    v2859.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    video = manifest.get("video_command_surface", {}) if isinstance(manifest.get("video_command_surface"), dict) else {}
    return "\n".join([
        "# Native Init V2866 Video Command Surface Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video display/framebuffer feasibility recon.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent candidate: `v2859-audio-changelog-latest-refresh`",
        "",
        "## Included Delta",
        "",
        "- Keeps the latest audio/core/productization baseline from V2859.",
        "- Adds the top-level `video` command under the display command group.",
        "- Adds read-only `video status` markers for the KMS dumb-buffer path and blocked Venus/KGSL/raw-DSI/power-write scope.",
        "- Adds bounded `video frame [bars|checker|mono|0xRRGGBB]` and `video demo` single-frame KMS rendering.",
        "- Leaves Bad Apple / Nyan Cat / DOOM as downstream demos until the single-frame command is live-proven.",
        "",
        "## Video Metadata",
        "",
        f"- Version: `{video.get('version')}`",
        f"- Source unit: `{video.get('source_unit')}`",
        f"- Live validation state: `{video.get('live_validation')}`",
        f"- Commands: `{', '.join(video.get('commands', [])) if isinstance(video.get('commands'), list) else video.get('commands')}`",
        f"- Safety boundary: `{video.get('safety_boundary')}`",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled audio artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V2866 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains `video.status.*`, `video.frame.*`, and `A90 VIDEO FRAME` strings.",
        "- Next live unit should flash this exact image, run `video status`, then `hide` + `video frame bars`, and rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- Private raw payloads are not committed; they are only copied into the private generated boot image.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-command-surface-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2866()
    v2859.render_report = render_report
    rc = v2859.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-command-surface-candidate",
        "parent_test_artifact": "v2859-audio-changelog-latest-refresh",
        "video_command_surface": {
            "version": 1,
            "source_unit": "V2865",
            "inventory_unit": "V2864",
            "commands": ["video", "video status", "video frame", "video demo"],
            "frame_patterns": ["bars", "checker", "mono", "0xRRGGBB"],
            "render_path": "kms-dumb-buffer",
            "safety_boundary": "no-venus-no-kgsl-no-raw-dsi-no-power-writes",
            "live_validation": "pending",
        },
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "video-command-surface-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-command-surface-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2865",
        "inventory_unit": "V2864",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2866 packages the first native video command surface for rollbackable live validation.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
