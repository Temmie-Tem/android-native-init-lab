#!/usr/bin/env python3
"""Build V2849 native-init audio status productization candidate.

V2849 keeps the V2847 boot-chime + bounded stop-execute feature set and adds
read-only productization markers to `audio status` and the screen-app audio
status page. This is a source/build unit; live marker validation remains a
separate V-iteration.
"""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2847_audio_stop_execute as v2847
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2849"
INIT_VERSION = "0.10.15"
INIT_BUILD = "v2849-audio-status-productization"
BUILD_TAG = INIT_BUILD
DECISION = "v2849-audio-status-productization-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2849_AUDIO_STATUS_PRODUCTIZATION_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2849_audio_status_productization.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2849_audio_status_productization"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2849_audio_status_productization.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v454_audio_status_productization"


def configure_base_for_v2849() -> None:
    v2847.CYCLE = CYCLE
    v2847.INIT_VERSION = INIT_VERSION
    v2847.INIT_BUILD = INIT_BUILD
    v2847.BUILD_TAG = BUILD_TAG
    v2847.DECISION = DECISION
    v2847.OUT_DIR = OUT_DIR
    v2847.REPORT_PATH = REPORT_PATH
    v2847.BOOT_IMAGE = BOOT_IMAGE
    v2847.INIT_BINARY = INIT_BINARY
    v2847.RAMDISK_CPIO = RAMDISK_CPIO
    v2847.HELPER_BINARY = HELPER_BINARY


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    boot_chime = manifest.get("audio_boot_chime", {}) if isinstance(manifest.get("audio_boot_chime"), dict) else {}
    stop_execute = manifest.get("audio_stop_execute", {}) if isinstance(manifest.get("audio_stop_execute"), dict) else {}
    status = manifest.get("audio_status_productization", {}) if isinstance(manifest.get("audio_status_productization"), dict) else {}
    return "\n".join([
        "# Native Init V2849 Audio Status Productization Source Build",
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
        "- Parent candidate: `v2847-audio-stop-execute`",
        "",
        "## Included Delta",
        "",
        "- Keeps the bundled SET-cal manifest/payload package, best-effort boot chime, and bounded `audio stop --execute` from V2847.",
        "- Adds read-only `audio.status.productization.*` markers so host automation can identify the latest proven audio feature set without parsing long reports.",
        "- Adds explicit `audio.status.feature.boot_chime.*` and `audio.status.feature.stop_execute.*` markers.",
        "- Updates `screenapp audio-status` to show the latest productization run/version plus boot-chime and stop-execute state.",
        "",
        "## Productization Markers",
        "",
        f"- Marker version: `{status.get('version')}`",
        f"- Latest proven run: `{status.get('latest_run')}`",
        f"- Latest proven version: `{status.get('latest_version')}`",
        f"- Latest proven tag: `{status.get('latest_tag')}`",
        f"- Boot-chime validation: `{status.get('boot_chime_validation_run')}`",
        f"- Stop-execute validation: `{status.get('stop_execute_validation_run')}`",
        f"- Stop-execute scope: `{status.get('stop_execute_scope')}`",
        f"- Live validation state: `{status.get('live_validation')}`",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        f"- Boot chime enabled: `{int(bool(boot_chime.get('enabled')))}`",
        f"- Stop execute supported: `{int(bool(stop_execute.get('execute_supported')))}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: source markers, screen status markers, and build wrapper contract tests.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Next live unit should flash this exact image, read `audio status` / `screenapp audio-status`, verify the productization markers, and rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds read-only status and display labels only; it does not add new mixer, PCM, route, SET-cal, or smart-amp writes.",
        "- Private raw payloads are not committed; they are only copied into the private generated boot image.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-productization-status-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2849()
    v2847.render_report = render_report
    rc = v2847.main()

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-status-candidate",
        "parent_test_artifact": "v2847-audio-stop-execute",
        "audio_status_productization": {
            "version": 1,
            "latest_run": "V2848",
            "latest_version": "0.10.14",
            "latest_tag": "v2847-audio-stop-execute",
            "boot_chime_validation_run": "V2846",
            "stop_execute_validation_run": "V2848",
            "stop_execute_scope": "core-route-reset",
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
    (OUT_DIR / "audio-status-productization-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-productization-status-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "latest_audio_run": "V2848",
        "latest_audio_version": "0.10.14",
        "latest_audio_tag": "v2847-audio-stop-execute",
        "boot_chime_validation_run": "V2846",
        "stop_execute_validation_run": "V2848",
        "stop_execute_scope": "core-route-reset",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2849 adds read-only productization markers to audio status and screen status; live validation is a separate unit.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
