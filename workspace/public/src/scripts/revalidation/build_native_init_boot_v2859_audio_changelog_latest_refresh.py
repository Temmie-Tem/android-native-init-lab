#!/usr/bin/env python3
"""Build V2859 native-init latest audio changelog refresh candidate.

V2859 keeps the V2857 productization marker surface, adds ABOUT changelog
entries through 0.10.19, and refreshes read-only audio productization markers
for the V2860 live validation unit.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2851_audio_changelog_productization as v2851
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2859"
INIT_VERSION = "0.10.19"
INIT_BUILD = "v2859-audio-changelog-latest-refresh"
BUILD_TAG = INIT_BUILD
DECISION = "v2859-audio-changelog-latest-refresh-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2859_AUDIO_CHANGELOG_LATEST_REFRESH_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2859_audio_changelog_latest_refresh.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2859_audio_changelog_latest_refresh"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2859_audio_changelog_latest_refresh.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v454_audio_changelog_latest_refresh"


def configure_base_for_v2859() -> None:
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
    refresh = manifest.get("audio_changelog_latest_refresh", {}) if isinstance(manifest.get("audio_changelog_latest_refresh"), dict) else {}
    return "\n".join([
        "# Native Init V2859 Audio Changelog Latest Refresh Source Build",
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
        "- Parent candidate: `v2857-audio-latest-marker-refresh`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V2857 productization status surface and bundled SET-cal package.",
        "- Adds ABOUT changelog entries for `0.10.16` through `0.10.19`.",
        "- Refreshes `AUDIO_PRODUCTIZATION_LATEST_*` and changelog validation markers for the V2860 live unit.",
        "- Adds no new audio writes; this is status/display provenance only.",
        "",
        "## Changelog Latest Refresh",
        "",
        f"- Latest run: `{refresh.get('latest_run')}`",
        f"- Latest version: `{refresh.get('latest_version')}`",
        f"- Latest tag: `{refresh.get('latest_tag')}`",
        f"- Changelog validation run: `{refresh.get('changelog_validation_run')}`",
        f"- Changelog entries added: `{', '.join(refresh.get('entries_added', [])) if isinstance(refresh.get('entries_added'), list) else refresh.get('entries_added')}`",
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
        "- `unittest`: changelog source entries, productization markers, and build wrapper contract tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Next live unit should flash this exact image, verify `audio status`, `screenapp about-changelog`, and rollback to `v2321`.",
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
        "- Candidate type: `audio-changelog-latest-refresh-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2859()
    v2851.render_report = render_report
    rc = v2851.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-changelog-latest-refresh-candidate",
        "parent_test_artifact": "v2857-audio-latest-marker-refresh",
        "audio_changelog_latest_refresh": {
            "version": 1,
            "latest_run": "V2860",
            "latest_version": INIT_VERSION,
            "latest_tag": INIT_BUILD,
            "chime_validation_run": "V2855",
            "boot_chime_validation_run": "V2846",
            "stop_execute_validation_run": "V2856",
            "stop_execute_scope": "core-route-reset",
            "changelog_validation_run": "V2860",
            "changelog_screenapp_count": 2,
            "entries_added": ["0.10.19 v2859", "0.10.18 v2857", "0.10.17 v2853", "0.10.16 v2851"],
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
    (OUT_DIR / "audio-changelog-latest-refresh-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-changelog-latest-refresh-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "latest_audio_run": "V2860",
        "latest_audio_version": INIT_VERSION,
        "latest_audio_tag": INIT_BUILD,
        "chime_validation_run": "V2855",
        "stop_execute_validation_run": "V2856",
        "changelog_validation_run": "V2860",
        "entries_added": ["0.10.19 v2859", "0.10.18 v2857", "0.10.17 v2853", "0.10.16 v2851"],
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2859 refreshes the ABOUT changelog and read-only audio productization markers to the V2860 live-validation contract.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
