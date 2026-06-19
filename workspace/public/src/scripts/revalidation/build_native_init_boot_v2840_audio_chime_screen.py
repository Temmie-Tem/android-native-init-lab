#!/usr/bin/env python3
"""Build V2840 native-init audio chime screen candidate."""

from __future__ import annotations

import json

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2807_audio_late_manifest_wait as v2807
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2840"
INIT_VERSION = "0.10.11"
INIT_BUILD = "v2840-audio-chime-screen"
BUILD_TAG = INIT_BUILD
DECISION = "v2840-audio-chime-screen-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2840_AUDIO_CHIME_SCREEN_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2840_audio_chime_screen.img", legacy_fallback=False
)
BASE_BOOT = v2807.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v2840_audio_chime_screen"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2840_audio_chime_screen.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v452_audio_chime_screen"


def configure_v2807_for_v2840() -> None:
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
        "# Native Init V2840 Audio Chime Screen Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio productization.",
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
        "- Keeps the promoted audio core and rolls PATCH to `0.10.11` for a manual `audio chime` screen/menu surface.",
        "- Adds display-only `screenapp audio-chime` and APPS/AUDIO `CHIME` entry for the V2838/V2839 manual chime preset.",
        "- The screen shows the manual command, default amplitude `80` milli, default duration `1200` ms, V2839 validation, and rollback status.",
        "- Boot autoplay remains disabled: the screen reports `BOOT AUTOPLAY DISABLED BLOCKS_BOOT=0` and does not run playback.",
        "",
        "## Scope Boundary",
        "",
        "- No device action was performed by this builder.",
        "- No audio ioctl, mixer write, route apply, PCM open, or playback occurs during build.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`; this artifact needs follow-up live validation before any adoption decision.",
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: V2840 chime screen, V2840 builder, and adjacent audio menu/screenapp/play-plan regression tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-productization-candidate`.",
        "",
    ])


def rewrite_candidate_metadata() -> None:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-candidate",
        "parent_test_artifact": "v2838-audio-chime-preset",
        "promoted_audio_core": "0.10.0",
        "productization_delta": [
            "audio-chime-screen",
            "audio-chime-menu-entry",
            "audio-chime-screenapp",
            "audio-chime-dry-run-default",
            "audio-chime-boot-autoplay-disabled",
            "audio-help-surface",
            "audio-stage-screen",
            "audio-profile-screen",
            "audio-route-map-safety-labels",
        ],
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "audio-productization-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2840 carries V2835/V2837 audio surfaces plus the V2838/V2839 manual chime preset and adds a display-only screen/menu surface; live validation is required before adoption.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    configure_v2807_for_v2840()
    v2807.render_report = render_report
    rc = v2807.main()
    rewrite_candidate_metadata()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
