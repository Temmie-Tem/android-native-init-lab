#!/usr/bin/env python3
"""Build V2833 native-init audio stage screen candidate."""

from __future__ import annotations

import json

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2807_audio_late_manifest_wait as v2807
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2833"
INIT_VERSION = "0.10.8"
INIT_BUILD = "v2833-audio-stage-screen"
BUILD_TAG = INIT_BUILD
DECISION = "v2833-audio-stage-screen-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2833_AUDIO_STAGE_SCREEN_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2833_audio_stage_screen.img", legacy_fallback=False
)
BASE_BOOT = v2807.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v2833_audio_stage_screen"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2833_audio_stage_screen.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v449_audio_stage_screen"


def configure_v2807_for_v2833() -> None:
    v2807.CYCLE = CYCLE
    v2807.INIT_VERSION = INIT_VERSION
    v2807.INIT_BUILD = INIT_BUILD
    v2807.BUILD_TAG = BUILD_TAG
    v2807.DECISION = DECISION
    v2807.OUT_DIR = OUT_DIR
    v2807.REPORT_PATH = REPORT_PATH
    v2807.BOOT_IMAGE = BOOT_IMAGE
    v2807.BASE_BOOT = BASE_BOOT
    v2807.INIT_BINARY = INIT_BINARY
    v2807.RAMDISK_CPIO = RAMDISK_CPIO
    v2807.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, object],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    return "\n".join([
        "# Native Init V2833 Audio Stage Screen Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio Tier C stage observability.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Base boot: `{str(BASE_BOOT.relative_to(REPO_ROOT))}`",
        "",
        "## Included Delta",
        "",
        "- Keeps the promoted audio core and rolls PATCH to `0.10.8` for stage-screen observability.",
        "- Adds display-only `screenapp audio-stages` / `screenapp stages` to show stage contract counts, stage write boundaries, and the known boot-to-cleanup sequence.",
        "- Adds the same display-only stage surface to the APPS/AUDIO menu as `STAGES`.",
        "- The stage screen reads compiled metadata only; it does not open audio devices, issue audio ioctls, write mixer controls, apply routes, or start playback.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`; this artifact needs a follow-up live validation before any adoption decision.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-observability-candidate`.",
        "",
    ])


def rewrite_candidate_metadata() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-observability-candidate",
        "parent_test_artifact": "v2831-audio-profile-screen",
        "promoted_audio_core": "0.10.0",
        "observability_delta": [
            "audio-stage-screen",
            "audio-menu-stage-screen",
            "audio-screenapp-stages",
            "audio-profile-screen",
            "audio-menu-profile-screen",
            "audio-screenapp-profile",
            "audio-route-map-safety-labels",
            "audio-screenapp-route-map",
            "audio-screenapp-status",
            "audio-status-core-promotion-summary",
            "audio-selftest-status-entry",
        ],
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "audio-observability-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-observability-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2833 carries V2832 audio observability plus a display-only audio stage screen; live validation is required before adoption.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    configure_v2807_for_v2833()
    v2807.render_report = render_report
    rc = v2807.main()
    rewrite_candidate_metadata()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
