#!/usr/bin/env python3
"""Build V2905 native-init candidate with the video SD-cache command surface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2905"
INIT_VERSION = "0.10.34"
INIT_BUILD = "v2905-video-cache-command"
BUILD_TAG = INIT_BUILD
DECISION = "v2905-video-cache-command-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2905_VIDEO_CACHE_COMMAND_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2905_video_cache_command.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2905_video_cache_command"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2905_video_cache_command.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v463_video_cache_command"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.34 (v2905-video-cache-command)",
    b"video.status.next_cache=video cache [status|verify|play] SHA256 [--present pageflip]",
    b"video.cache.version=1",
    b"/mnt/sdext/a90/runtime/video/cache",
    b"sha256-",
    b"video.cache.stream_size_match=",
    b"video.cache.verify.sha256_match=",
    b"video.cache.play.requested_present=",
    b"video cache [status|verify|play] SHA256",
    b"kms-dumb-buffer-pageflip",
    b"mono1",
    b"video.stream.frames_total=",
    b"video.stream.dropped_frames=",
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
        raise RuntimeError(f"missing V2905 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2905_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2905 Video SD Cache Command Source Build",
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
        "- Parent code unit: V2904 added `video cache status|verify|play SHA256` over the existing `A90VSTR1` stream player.",
        "",
        "## Included Delta",
        "",
        "- Builds the V2904 SD-cache command surface into a flashable test image.",
        "- Keeps large video assets on the SD SHA-addressed cache; the boot image carries only player and verification code.",
        "- `video cache status` reports manifest and stream-size state without hashing the multi-GB stream.",
        "- `video cache verify` and `video cache play` require a full SHA-256 stream match before playback.",
        "- Playback still reuses the existing KMS dumb-buffer stream path; no Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, or GDSC path is added.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V2905 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2905 init identity, video cache command markers, SD cache path, and retained video stream/pageflip markers.",
        "- Device validation is deferred to V2906: flash this exact image, run `video cache status|verify|play` against the V2900 SD cache SHA, then rollback to `v2321`.",
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
        "- This unit changes the command surface only; generated frames, raw streams, and boot images remain private/untracked.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-cache-command-candidate`.",
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
        "candidate_type": "video-cache-command-candidate",
        "parent_test_artifact": "v2904-video-cache-command-host-only",
        "video_cache_command": {
            "version": 1,
            "source_unit": "V2905",
            "parent_unit": "V2904",
            "cache_root": "/mnt/sdext/a90/runtime/video/cache",
            "commands": [
                "video cache status SHA256",
                "video cache verify SHA256",
                "video cache play SHA256 [--frames N] [--present setcrtc|pageflip]",
            ],
            "stream_format": "A90VSTR1",
            "large_asset_policy": "pre-rendered streams stay in the SHA-addressed SD-card cache, not inside the boot image",
            "live_validation": "pending",
        },
        "v2905_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "video-cache-command-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-cache-command-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2905",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
