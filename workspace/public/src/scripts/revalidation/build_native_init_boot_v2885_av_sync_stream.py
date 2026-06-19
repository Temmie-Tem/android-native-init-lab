#!/usr/bin/env python3
"""Build V2885 native-init candidate with audio-anchored video stream scheduling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2885"
INIT_VERSION = "0.10.28"
INIT_BUILD = "v2885-av-sync-stream"
BUILD_TAG = INIT_BUILD
DECISION = "v2885-av-sync-stream-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2885_AV_SYNC_STREAM_SOURCE_BUILD_2026-06-19.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2885_av_sync_stream.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2885_av_sync_stream"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2885_av_sync_stream.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v458_av_sync_stream"

REQUIRED_STRINGS = (
    b"video.stream.audio_sync.enabled=",
    b"video.stream.audio_sync.ready=",
    b"video.stream.audio_sync.listen_begin_ns=",
    b"video.stream.audio_sync.anchor_age_ns=",
    b"video.stream.requested_audio_sync=",
    b"--sync-audio-status",
    b"/cache/a90-audio-play/status.txt",
    b"audio.play.worker.listen_begin_ns=",
    b"audio.play.worker.listen_end_ns=",
    b"kms-dumb-buffer-pageflip",
)


def configure_base() -> None:
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


def require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS if marker not in data]
    if missing:
        raise RuntimeError(f"missing V2885 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2885_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2885 A/V Sync Stream Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline on existing KMS display.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent validated state: V2884 proved audio timeline markers and video page-flip telemetry in one run.",
        "",
        "## Included Delta",
        "",
        "- Adds opt-in `video stream ... --sync-audio-status /cache/a90-audio-play/status.txt`.",
        "- Waits for `audio.play.worker.listen_begin_ns` and sample/frame geometry before presenting frames.",
        "- Anchors video frame deadlines to the audio PCM begin timestamp instead of video command start.",
        "- Keeps the default non-sync `video stream` behavior unchanged.",
        "- Restricts the sync status path to `/cache/a90-audio-play/status.txt` and bounds the wait with `--sync-wait-ms`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V2885 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2885 audio-sync stream markers plus retained audio timeline/page-flip markers.",
        *marker_lines,
        "- Device validation is deferred to V2886: flash this exact image, run PCM audio + sync video stream, then rollback to `v2321`.",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled audio artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds scheduling/observability only; it does not add Venus, KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- Audio amplitude and route behavior remain governed by existing bounded `audio play` caps.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `av-sync-stream-candidate`.",
        "",
    ])


def main() -> int:
    configure_base()
    v2859.render_report = render_report
    rc = v2859.main()
    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "av-sync-stream-candidate",
        "parent_test_artifact": "v2884-av-sync-telemetry",
        "av_sync_stream": {
            "version": 1,
            "source_unit": "V2885",
            "command": "video stream --manifest PATH --video-only --present pageflip --sync-audio-status /cache/a90-audio-play/status.txt",
            "status_path_policy": "exact-cache-a90-audio-play-status-only",
            "deadline_anchor": "audio.play.worker.listen_begin_ns",
            "wait_default_ms": 90000,
            "live_validation": "pending",
        },
        "v2885_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "av-sync-stream-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "av-sync-stream-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2885",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
