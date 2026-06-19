#!/usr/bin/env python3
"""Build V2871 native-init video blitbench candidate.

V2871 keeps the V2868 video animation scaffold and adds the first full-frame
KMS copy benchmark primitive: `video blitbench [frames]`.
Live validation is a separate V-iteration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2871"
INIT_VERSION = "0.10.22"
INIT_BUILD = "v2871-video-blitbench"
BUILD_TAG = INIT_BUILD
DECISION = "v2871-video-blitbench-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2871_VIDEO_BLITBENCH_SOURCE_BUILD_2026-06-19.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2871_video_blitbench.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v2871_video_blitbench"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2871_video_blitbench.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v455_video_blitbench"

REQUIRED_STRINGS = (
    b"video.status.kms.stride=",
    b"video.status.kms.map_size=",
    b"video.status.kms.pixel_format=xbgr8888",
    b"video.status.next_blitbench=video blitbench [frames<=240]",
    b"video.blitbench.presented=",
    b"video.blitbench.fps_milli=",
    b"video.blitbench.mbps_milli=",
    b"videoblitbench",
)


def configure_base_for_v2871() -> None:
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
        raise RuntimeError(f"missing V2871 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any],
                  helper_flags: tuple[str, ...],
                  init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    video = manifest.get("video_command_surface", {}) if isinstance(manifest.get("video_command_surface"), dict) else {}
    marker_strings = manifest.get("v2871_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in marker_strings] if isinstance(marker_strings, list) else []
    return "\n".join([
        "# Native Init V2871 Video Blitbench Source Build",
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
        "- Parent candidate: `v2859-audio-changelog-latest-refresh` plus the V2868 video command surface already in source.",
        "",
        "## Included Delta",
        "",
        "- Keeps the latest audio/core/productization baseline and the V2868 `video frame` / `video anim` KMS command surface.",
        "- Extends `a90_kms_info` with `stride`, `map_size`, and `pixel_format` so host preprocessors can target the exact active framebuffer surface.",
        "- Adds `a90_kms_begin_frame_no_clear()` for full-frame stream paths that overwrite every pixel without measuring an extra clear pass.",
        "- Adds bounded, cancelable `video blitbench [frames<=240]` that copies a synthetic full-frame source row-by-row into the mapped KMS dumb buffer and presents each frame.",
        "- Reports `video.blitbench.*` metrics: frames, bytes, elapsed ns, fps_milli, mbps_milli, geometry, stride, frame_bytes, and `pixel_format=xbgr8888`.",
        "- Leaves frame-file streaming, arbitrary PCM-file playback, and A/V sync for later units after the live blit ceiling is measured.",
        "",
        "## Video Metadata",
        "",
        f"- Version: `{video.get('version')}`",
        f"- Source unit: `{video.get('source_unit')}`",
        f"- Commands: `{', '.join(video.get('commands', [])) if isinstance(video.get('commands'), list) else video.get('commands')}`",
        f"- Benchmark bound: `{video.get('blitbench_bound')}`",
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
        "- `py_compile`: V2871 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack with bundled private files, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains the V2871 `video.status.kms.*` and `video.blitbench.*` command markers.",
        *marker_lines,
        "- `file`: native-init and helper are AArch64 statically linked executables.",
        "- Next live unit should flash this exact image, run `video status`, `hide`, and bounded `video blitbench`, then rollback to `v2321`.",
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- This unit adds no Venus, GPU/KGSL, raw DSI, panel init, backlight, PMIC, PWM, regulator, GPIO, or GDSC path.",
        "- The benchmark uses synthetic frame data only; no copyrighted media, generated frame payloads, PCM payloads, boot images, or binaries are committed.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-blitbench-candidate`.",
        "",
    ])


def main() -> int:
    configure_base_for_v2871()
    v2859.render_report = render_report
    rc = v2859.main()

    marker_strings = require_strings(BOOT_IMAGE)
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-blitbench-candidate",
        "parent_test_artifact": "v2859-audio-changelog-latest-refresh",
        "video_command_surface": {
            "version": 2,
            "source_unit": "V2871",
            "inventory_unit": "V2864",
            "commands": [
                "video",
                "video status",
                "video frame",
                "video demo",
                "video anim",
                "video blitbench",
            ],
            "frame_patterns": ["bars", "checker", "mono", "0xRRGGBB"],
            "animation_patterns": ["bars", "checker", "pulse"],
            "animation_bounds": {"frames_max": 240, "delay_ms_max": 1000},
            "blitbench_bound": "frames<=240",
            "render_path": "kms-dumb-buffer",
            "pixel_format": "xbgr8888",
            "safety_boundary": "no-venus-no-kgsl-no-raw-dsi-no-power-writes",
            "live_validation": "pending",
        },
        "v2871_marker_strings": marker_strings,
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
    (OUT_DIR / "video-blitbench-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-blitbench-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2871",
        "plan_unit": "V2870",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
        "note": "V2871 packages bounded KMS full-frame blit throughput measurement for rollbackable live validation.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
