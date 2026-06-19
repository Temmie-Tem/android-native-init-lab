#!/usr/bin/env python3
"""Build V2851 native-init audio changelog productization candidate.

V2851 keeps the V2849 audio productization status feature set and adds
latest 0.10.x audio changelog entries plus direct about screenapp dispatch.
This is a source/build unit; live display validation remains a separate
V-iteration.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2849_audio_status_productization as v2849
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2851"
INIT_VERSION = "0.10.16"
INIT_BUILD = "v2851-audio-changelog-productization"
BUILD_TAG = INIT_BUILD
DECISION = "v2851-audio-changelog-productization-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2851_AUDIO_CHANGELOG_PRODUCTIZATION_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2851_audio_changelog_productization.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2851_audio_changelog_productization"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2851_audio_changelog_productization.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v454_audio_changelog_productization"


def configure_base_for_v2851() -> None:
    v2849.CYCLE = CYCLE
    v2849.INIT_VERSION = INIT_VERSION
    v2849.INIT_BUILD = INIT_BUILD
    v2849.BUILD_TAG = BUILD_TAG
    v2849.DECISION = DECISION
    v2849.OUT_DIR = OUT_DIR
    v2849.REPORT_PATH = REPORT_PATH
    v2849.BOOT_IMAGE = BOOT_IMAGE
    v2849.INIT_BINARY = INIT_BINARY
    v2849.RAMDISK_CPIO = RAMDISK_CPIO
    v2849.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    changelog = manifest.get("audio_changelog_productization", {}) if isinstance(manifest.get("audio_changelog_productization"), dict) else {}
    return "\n".join([
        "# Native Init V2851 Audio Changelog Productization Source Build",
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
        "- Parent candidate: `v2849-audio-status-productization`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V2849 read-only audio productization status markers.",
        "- Adds latest `0.10.x` audio-core and post-promotion productization entries to the native changelog.",
        "- Raises `A90_CHANGELOG_MAX_ENTRIES` to match the existing historical entry count and new audio entries.",
        "- Exposes `screenapp about-version` and `screenapp about-changelog` for direct serial validation of the ABOUT screens.",
        "",
        "## Changelog Markers",
        "",
        f"- Productization version: `{changelog.get('version')}`",
        f"- Latest changelog run: `{changelog.get('latest_run')}`",
        f"- Latest changelog version: `{changelog.get('latest_version')}`",
        f"- Direct screenapps: `{', '.join(changelog.get('direct_screenapps', [])) if isinstance(changelog.get('direct_screenapps'), list) else changelog.get('direct_screenapps')}`",
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
        "- `unittest`: changelog entries, direct about screenapp dispatch, and build wrapper contract tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Next live unit should flash this exact image, read `audio status` plus `screenapp about-changelog`, verify the display markers, and rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds read-only changelog/status/display labels only; it does not add new mixer, PCM, route, SET-cal, or smart-amp writes.",
        "- Private raw payloads are not committed; they are only copied into the private generated boot image.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-productization-changelog-candidate`.",
        "",
    ])

def main() -> int:
    configure_base_for_v2851()
    v2849.render_report = render_report
    rc = v2849.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-changelog-candidate",
        "parent_test_artifact": "v2849-audio-status-productization",
        "audio_changelog_productization": {
            "version": 1,
            "latest_run": "V2850",
            "latest_version": "0.10.15",
            "latest_tag": "v2849-audio-status-productization",
            "direct_screenapps": ["about-version", "about-changelog"],
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
    (OUT_DIR / "audio-changelog-productization-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-changelog-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "latest_audio_run": "V2850",
        "latest_audio_version": "0.10.15",
        "latest_audio_tag": "v2849-audio-status-productization",
        "direct_screenapps": ["about-version", "about-changelog"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2851 adds latest audio changelog entries and direct ABOUT screenapp dispatch; live validation is a separate unit.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
