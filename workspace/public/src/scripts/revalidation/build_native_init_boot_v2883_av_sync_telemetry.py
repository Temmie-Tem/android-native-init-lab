#!/usr/bin/env python3
"""Build V2883 native-init candidate with audio timeline telemetry for A/V sync.

V2883 keeps the V2880 PCM-file audio source and V2878/V2879 page-flip video
stream path, then adds monotonic audio playback timeline markers. The markers
are the next A/V-sync anchor: video flip-complete timestamps can be correlated
with audio listen_begin_ns + sample/frame geometry without changing playback
behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2883"
INIT_VERSION = "0.10.27"
INIT_BUILD = "v2883-av-sync-telemetry"
BUILD_TAG = INIT_BUILD
DECISION = "v2883-av-sync-telemetry-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2883_AV_SYNC_TELEMETRY_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2883_av_sync_telemetry.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2883_av_sync_telemetry"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2883_av_sync_telemetry.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v457_av_sync_telemetry"

REQUIRED_STRINGS = (
    b"audio.play.execute.timeline.version=1",
    b"audio.play.execute.listen_begin_ns=",
    b"audio.play.execute.listen_end_ns=",
    b"audio.play.execute.expected_duration_ns=",
    b"audio.play.worker.timeline.version=1",
    b"audio.play.worker.listen_begin_ns=",
    b"audio.play.worker.listen_end_ns=",
    b"audio.play.worker.frames_done=",
    b"audio.play.worker.expected_duration_ns=",
    b"audio.play.pcm_file_supported=1",
    b"--pcm-file PATH",
    b"kms-dumb-buffer-pageflip",
)


def configure_base_for_v2883() -> None:
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
        raise RuntimeError(f"missing V2883 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    telemetry = manifest.get("av_sync_telemetry", {}) if isinstance(manifest.get("av_sync_telemetry"), dict) else {}
    marker_strings = manifest.get("v2883_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in marker_strings] if isinstance(marker_strings, list) else []
    return "\n".join([
        "# Native Init V2883 A/V Sync Telemetry Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline; this unit adds the audio timeline anchor needed for exact A/V sync.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent validated state: V2882 live-proved PCM-file audio and page-flip video can co-run in one boot.",
        "",
        "## Included Delta",
        "",
        "- Keeps the bounded `audio play --pcm-file` source and the KMS page-flip `video stream` path unchanged.",
        "- Adds monotonic `listen_begin_ns` immediately before the first PCM write and `listen_end_ns` after drain/abort.",
        "- Records sample rate, channels, bit width, frame bytes, total frames/bytes, expected duration, frames done, and bytes done.",
        "- Emits the same timeline markers to the async worker status file so the video runner can read them while/after playback.",
        "- Makes no mixer, route, SET-cal, audio amplitude, video KMS, or flash-policy change.",
        "",
        "## Telemetry Contract",
        "",
        f"- Version: `{telemetry.get('version')}`",
        f"- Audio begin anchor: `{telemetry.get('begin_marker')}`",
        f"- Audio end anchor: `{telemetry.get('end_marker')}`",
        f"- Status mirror: `{telemetry.get('status_path')}`",
        "- Sync formula for the next unit: audio frame position = `(now_ns - listen_begin_ns) * sample_rate / 1e9`, bounded by `total_frames`.",
        "- Video clock input: retained DRM page-flip `video.stream.last_timestamp_us` plus per-run elapsed/flip counters.",
        "",
        "## Bundled Runtime Metadata",
        "",
        f"- Bundled audio artifact count: `{bundled.get('artifact_count')}`",
        f"- Replay entry count: `{bundled.get('replay_entry_count')}`",
        f"- Native manifest SHA256: `{bundled.get('native_manifest_sha256')}`",
        "- Raw SET-cal bytes remain private; this report records only counts and hashes.",
        "",
        "## Static Validation",
        "",
        "- `py_compile`: V2883 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2883 timeline, retained PCM-file, and retained page-flip markers.",
        *marker_lines,
        "- `file`: native-init and helper are AArch64 statically linked executables.",
        "- Device validation is deferred to V2884: flash this exact image, run the V2882-style A/V co-run, require timeline markers, then rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds observability only; it does not add new Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- PCM execution remains bounded by existing audio caps and pre-write amplitude scanning.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `av-sync-telemetry-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2883()
    v2859.render_report = render_report
    rc = v2859.main()

    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "av-sync-telemetry-candidate",
        "parent_test_artifact": "v2882-av-pcm-video-corun",
        "audio_pcm_file_source": {
            "version": 2,
            "source_unit": "V2883",
            "allowed_prefix": "/cache/a90-runtime",
            "format": "s16le-stereo-48000",
            "path_policy": "absolute-no-dotdot-runtime-prefix-open-nofollow",
            "safety": "regular-file-size-check-peak-amplitude-scan-before-alsa-write",
            "live_validation": "pending",
        },
        "av_sync_telemetry": {
            "version": 1,
            "source_unit": "V2883",
            "begin_marker": "audio.play.worker.listen_begin_ns",
            "end_marker": "audio.play.worker.listen_end_ns",
            "status_path": "/cache/a90-audio-play/status.txt",
            "sample_rate_marker": "audio.play.worker.sample_rate",
            "frame_bytes_marker": "audio.play.worker.frame_bytes",
            "total_frames_marker": "audio.play.worker.total_frames",
            "frames_done_marker": "audio.play.worker.frames_done",
            "next_unit": "V2884 live co-run telemetry validation",
        },
        "video_command_surface": {
            "version": 7,
            "source_unit": "V2883",
            "commands": ["video", "video status", "video frame", "video anim", "video blitbench", "video flipprobe", "video stream"],
            "stream_format": "A90VSTR1 xbgr8888-raw-stride",
            "stream_present_modes": ["setcrtc", "pageflip"],
            "pageflip_stream_status": "live-validated-v2879-v2882",
            "flip_clock_marker": "video.stream.last_timestamp_us",
            "safety_boundary": "no-venus-no-kgsl-no-raw-dsi-no-power-writes",
        },
        "v2883_marker_strings": marker_strings,
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
    (OUT_DIR / "av-sync-telemetry-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "av-sync-telemetry-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2883",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2883 adds audio timeline markers for the next exact A/V sync unit while retaining the proven PCM-file and page-flip paths.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
