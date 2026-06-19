#!/usr/bin/env python3
"""Build V2878 native-init video stream page-flip candidate.

V2878 keeps the V2876 page-flip probe and wires the already-proven page-flip
present path into `video stream` as an opt-in `--present pageflip` mode. The
existing SETCRTC stream mode remains the default for compatibility.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2878"
INIT_VERSION = "0.10.25"
INIT_BUILD = "v2878-video-stream-pageflip"
BUILD_TAG = INIT_BUILD
DECISION = "v2878-video-stream-pageflip-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2878_VIDEO_STREAM_PAGEFLIP_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2878_video_stream_pageflip.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2878_video_stream_pageflip"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2878_video_stream_pageflip.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v455_video_stream_pageflip"

REQUIRED_STRINGS = (
    b"video.status.next_stream_pageflip=video stream --manifest PATH --video-only [--frames N] --present pageflip",
    b"video.stream.requested_present=",
    b"video.stream.present_mode=",
    b"video.stream.flip_events=",
    b"video.stream.path=%s",
    b"kms-dumb-buffer-pageflip",
    b"--present setcrtc|pageflip",
    b"videostreamprime",
)


def configure_base_for_v2878() -> None:
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
        raise RuntimeError(f"missing V2878 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    video = manifest.get("video_command_surface", {}) if isinstance(manifest.get("video_command_surface"), dict) else {}
    marker_strings = manifest.get("v2878_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in marker_strings] if isinstance(marker_strings, list) else []
    return "\n".join([
        "# Native Init V2878 Video Stream Page-Flip Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline on the existing KMS display.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "- Parent candidate: V2877 proved page-flip events on the existing KMS dumb-buffer display path.",
        "",
        "## Included Delta",
        "",
        "- Keeps the V2874 raw-stride `video stream` reader and V2876/V2877 page-flip helper/probe.",
        "- Adds optional `--present setcrtc|pageflip` parsing to `video stream`; the default remains `setcrtc` for compatibility with the already-proven V2875 path.",
        "- In `pageflip` mode, primes the CRTC with the existing SETCRTC present once, then uses `a90_kms_present_pageflip()` for each streamed frame.",
        "- Reports `video.stream.present_mode`, `video.stream.flip_events`, last flip sequence/CRTC/timestamp, and uses `path=kms-dumb-buffer-pageflip` only when the opt-in mode is active.",
        "- Leaves A/V sync and PCM-file playback for later units after the page-flip stream mode is live-proven.",
        "",
        "## Video Metadata",
        "",
        f"- Version: `{video.get('version')}`",
        f"- Source unit: `{video.get('source_unit')}`",
        f"- Commands: `{', '.join(video.get('commands', [])) if isinstance(video.get('commands'), list) else video.get('commands')}`",
        f"- Stream present modes: `{', '.join(video.get('stream_present_modes', [])) if isinstance(video.get('stream_present_modes'), list) else video.get('stream_present_modes')}`",
        f"- Safety boundary: `{video.get('safety_boundary')}`",
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
        "- `py_compile`: V2878 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2878 stream page-flip option/report markers.",
        *marker_lines,
        "- `file`: native-init and helper are AArch64 statically linked executables.",
        "- Next live unit should flash this exact image, install a private A90VSTR1 fixture, run `video stream ... --present pageflip`, then rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- Page-flip mode remains opt-in and uses the same existing KMS card0 dumb buffers as V2877.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-stream-pageflip-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2878()
    v2859.render_report = render_report
    rc = v2859.main()

    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-stream-pageflip-candidate",
        "parent_test_artifact": "v2876-video-flipprobe",
        "video_command_surface": {
            "version": 5,
            "source_unit": "V2878",
            "inventory_unit": "V2864",
            "plan_unit": "V2870",
            "commands": [
                "video",
                "video status",
                "video frame",
                "video demo",
                "video anim",
                "video blitbench",
                "video flipprobe",
                "video stream",
            ],
            "blitbench_bound": "frames<=240",
            "flipprobe_bound": "frames<=120",
            "stream_format": "A90VSTR1 xbgr8888-raw-stride",
            "stream_frame_bound": "frames<=600",
            "stream_present_modes": ["setcrtc", "pageflip"],
            "default_stream_present_mode": "setcrtc",
            "pageflip_stream_status": "pending-live-validation",
            "render_path": "kms-dumb-buffer",
            "flip_path": "kms-dumb-buffer-pageflip",
            "pixel_format": "xbgr8888",
            "safety_boundary": "no-venus-no-kgsl-no-raw-dsi-no-power-writes",
            "live_validation": "pending",
        },
        "v2878_marker_strings": marker_strings,
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
    (OUT_DIR / "video-stream-pageflip-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-stream-pageflip-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2878",
        "plan_unit": "V2870",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2878 packages opt-in KMS page-flip presentation for the raw-stride video stream reader.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
