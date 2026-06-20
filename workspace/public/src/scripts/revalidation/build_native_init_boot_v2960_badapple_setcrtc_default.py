#!/usr/bin/env python3
"""Build V2960 native-init candidate with Bad Apple setcrtc default."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2960"
INIT_VERSION = "0.10.56"
INIT_BUILD = "v2960-badapple-setcrtc-default"
BUILD_TAG = INIT_BUILD
DECISION = "v2960-badapple-setcrtc-default-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2960_BADAPPLE_SETCRTC_DEFAULT_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2960_badapple_setcrtc_default.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2960_badapple_setcrtc_default"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2960_badapple_setcrtc_default.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v477_badapple_setcrtc_default"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.56 (v2960-badapple-setcrtc-default)",
    b"video.status.version=6",
    b"video.status.display_owner=1",
    b"video.status.player_hud_fastpath=1",
    b"menu.demo.badapple.action=play-av-fullsong",
    b"menu.demo.badapple.frames=6962",
    b"menu.demo.badapple.audio_pcm_gain_milli=780",
    b"menu.demo.badapple.video_present=setcrtc",
    b"menu.demo.badapple.audio_sync_start_offset_ms=450",
    b"badapple-480x360-full-v2903",
    b"9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0",
    b"b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75",
    b"video.stream.flip_delta_min_us=%llu",
    b"video.stream.flip_delta_max_us=%llu",
    b"video.stream.flip_delta_avg_us=%llu",
    b"video.stream.flip_delta_target_us=%llu",
    b"video.stream.beat_flash.active_frames=%u",
    b"audio.play.worker.pcm_gain_milli=%d",
    b"audio.play.cap.duration_policy=%s",
    b"badapple-fullsong-pcm",
    b"kms-dumb-buffer",
    b"player-hud",
    b"mono1",
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
        raise RuntimeError(f"missing V2960 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2960_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2960 Bad Apple Setcrtc Default Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback pipeline / Bad Apple Player HUD.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Why This Unit Exists",
        "",
        "- V2955 confirmed the V2954 volume-only image still presented the full Bad Apple stream with `dropped_frames=0`, but the operator observed visible frame stutter.",
        "- V2955/V2957/V2959 confirmed the pageflip path can present every frame, but it still reports alternating 16 ms / 50 ms flip-event cadence (`flip_delta_min_us≈166xx`, `flip_delta_max_us≈498xx`).",
        "- V2960 keeps the trimmed gain default (`pcm_gain_milli=780`) and changes the DEMO menu default from `pageflip` to `setcrtc`, based on the V2960 comparison probe that produced 30 fps with `present_mode=setcrtc` and no pageflip event-cadence jitter surface.",
        "",
        "## Included Delta",
        "",
        "- Changes only the APPS/DEMO Bad Apple launcher default to `--present setcrtc` and adds `menu.demo.badapple.video_present=setcrtc` as a device-visible marker.",
        "- Keeps the direct `video demo badapple play --present pageflip` path available for manual comparison; this unit does not remove pageflip support.",
        "- Keeps the V2952 Player HUD render fastpath, the full-song SD-cache asset, audio sync, late-frame skip policy, beat flash, and the reduced Bad Apple menu PCM gain of `780`.",
        "- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Static Validation",
        "",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2960 identity, setcrtc menu marker, Player HUD markers, trimmed gain marker, full-song asset hashes, and cadence counters.",
        "- Device validation is deferred to V2961: flash this exact image and run the Bad Apple Player HUD A/V path with the setcrtc present mode.",
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
        "- Generated frames, raw streams, boot images, and private caches remain private/untracked.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata`.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-setcrtc-default-candidate`.",
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
        "candidate_type": "badapple-setcrtc-default-candidate",
        "parent_test_artifact": "v2955-badapple-volume-trim-live-cadence-jitter-observed",
        "badapple_player_hud": {
            "version": 2,
            "source_unit": "V2960",
            "parent_unit": "V2952",
            "cache_root": "/mnt/sdext/a90/runtime/video/cache",
            "real_stream_sha256": "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0",
            "asset_id": "badapple-480x360-full-v2903",
            "default_present_mode": "setcrtc",
            "fullsong_audio": {
                "policy": "badapple-fullsong-pcm",
                "duration_cap_ms": 240000,
                "recommended_duration_ms": 232090,
                "recommended_pcm_gain_milli": 780,
                "amplitude_milli": 150,
                "primary_remote_pcm": "/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
                "sha256": "b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75",
            },
            "live_validation": "pending-v2961",
        },
        "v2960_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "badapple-setcrtc-default-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-setcrtc-default-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2960",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
