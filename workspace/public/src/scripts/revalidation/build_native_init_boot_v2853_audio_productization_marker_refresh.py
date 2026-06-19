#!/usr/bin/env python3
"""Build V2853 native-init audio productization marker refresh candidate.

V2853 keeps the V2851 changelog/about productization surface and refreshes the
read-only `audio status` productization markers so the device reports the
latest live-validated post-promotion candidate evidence from V2852.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2851_audio_changelog_productization as v2851
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2853"
INIT_VERSION = "0.10.17"
INIT_BUILD = "v2853-audio-productization-marker-refresh"
BUILD_TAG = INIT_BUILD
DECISION = "v2853-audio-productization-marker-refresh-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2853_AUDIO_PRODUCTIZATION_MARKER_REFRESH_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2853_audio_productization_marker_refresh.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2853_audio_productization_marker_refresh"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2853_audio_productization_marker_refresh.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v454_audio_productization_marker_refresh"


def configure_base_for_v2853() -> None:
    v2851.CYCLE = CYCLE
    v2851.INIT_VERSION = INIT_VERSION
    v2851.INIT_BUILD = INIT_BUILD
    v2851.BUILD_TAG = BUILD_TAG
    v2851.DECISION = DECISION
    v2851.OUT_DIR = OUT_DIR
    v2851.REPORT_PATH = REPORT_PATH
    v2851.BOOT_IMAGE = BOOT_IMAGE
    v2851.INIT_BINARY = INIT_BINARY
    v2851.RAMDISK_CPIO = RAMDISK_CPIO
    v2851.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    marker = manifest.get("audio_productization_marker_refresh", {}) if isinstance(manifest.get("audio_productization_marker_refresh"), dict) else {}
    return "\n".join([
        "# Native Init V2853 Audio Productization Marker Refresh Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: post-promotion audio productization / readable operation.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent candidate: `v2851-audio-changelog-productization`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V2851 changelog entries and direct ABOUT screenapp dispatch.",
        "- Refreshes `AUDIO_PRODUCTIZATION_LATEST_*` to the V2852 live-validated `0.10.16` candidate.",
        "- Adds read-only `audio.status.feature.changelog.*` markers for the ABOUT/changelog validation surface.",
        "- Updates `screenapp audio-status` to show the ABOUT/changelog validation run without adding any audio writes.",
        "",
        "## Productization Marker Refresh",
        "",
        f"- Latest run: `{marker.get('latest_run')}`",
        f"- Latest version: `{marker.get('latest_version')}`",
        f"- Latest tag: `{marker.get('latest_tag')}`",
        f"- Changelog validation run: `{marker.get('changelog_validation_run')}`",
        f"- Changelog screenapp count: `{marker.get('changelog_screenapp_count')}`",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: productization marker source test and build wrapper contract test.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Next live unit should flash this exact image, verify the refreshed `audio status` markers, and rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds read-only status/display labels only; it does not add new mixer, PCM, route, SET-cal, or smart-amp writes.",
        "- Private raw payloads are not committed; they are only copied into the private generated boot image.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-productization-marker-refresh-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2853()
    v2851.render_report = render_report
    rc = v2851.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-marker-refresh-candidate",
        "parent_test_artifact": "v2851-audio-changelog-productization",
        "audio_productization_marker_refresh": {
            "version": 1,
            "latest_run": "V2852",
            "latest_version": "0.10.16",
            "latest_tag": "v2851-audio-changelog-productization",
            "changelog_validation_run": "V2852",
            "changelog_screenapp_count": 2,
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
    (OUT_DIR / "audio-productization-marker-refresh-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-marker-refresh-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "latest_audio_run": "V2852",
        "latest_audio_version": "0.10.16",
        "latest_audio_tag": "v2851-audio-changelog-productization",
        "changelog_validation_run": "V2852",
        "changelog_screenapp_count": 2,
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2853 refreshes read-only audio productization markers to the V2852 live-validated changelog/about candidate.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
