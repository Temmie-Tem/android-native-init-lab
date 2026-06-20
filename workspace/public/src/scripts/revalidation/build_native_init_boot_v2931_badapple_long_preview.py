#!/usr/bin/env python3
"""Build V2931 native-init candidate with Bad Apple 10 second menu preview and pre-render drop skip."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2931"
INIT_VERSION = "0.10.44"
INIT_BUILD = "v2931-badapple-long-preview"
BUILD_TAG = INIT_BUILD
DECISION = "v2931-badapple-long-preview-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2931_BADAPPLE_LONG_PREVIEW_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2931_badapple_long_preview.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2931_badapple_long_preview"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2931_badapple_long_preview.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v474_badapple_long_preview"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.44 (v2931-badapple-long-preview)",
    b"video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale] play [--trust-cache]",
    b"video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]",
    b"DEMO >",
    b"BAD APPLE HUD",
    b"menu.demo.badapple.frames=300",
    b"menu.demo.badapple.restore=menu",
    b"menu.demo.badapple.action=play-av-preview",
    b"menu.demo.badapple.audio_duration_ms=10000",
    b"menu.demo.badapple.audio_amplitude_milli=200",
    b"menu.demo.badapple.audio_pcm=/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
    b"menu.demo.badapple.audio_sync_status=/cache/a90-audio-play/status.txt",
    b"menu.demo.badapple.audio_sync_start_offset_ms=450",
    b"--sync-start-offset-ms",
    b"video.stream.audio_sync.start_offset_ms=%u",
    b"video.stream.audio_sync.corrected_anchor_ns=%llu",
    b"video.stream.audio_sync.drop_threshold_ns=%llu",
    b"video.stream.requested_audio_sync_start_offset_ms=%u",
    b"video.cache.play.requested_audio_sync_start_offset_ms=%u",
    b"menu.demo.badapple.audio_rc=%d",
    b"badapple-480x360-full-v2903",
    b"9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0",
    b"badapple-scale",
    b"878dd867d63141eb6c9ce45a936d0454778ac91031e929b8da1c873c1c901890",
    b"video.cache.preset=%s",
    b"video.cache.preset.asset_id=%s",
    b"video.cache.preset.sha256=%s",
    b"video.cache.play.requested_layout=%s",
    b"video.stream.requested_layout=%s",
    b"video.stream.layout=%s",
    b"player-hud",
    b"DEMO / BAD APPLE",
    b"A90 PLAYER HUD",
    b"BEAT FLASH: audio-clock border pulse (host onset table pending)",
    b"READONLY TELEMETRY /proc+/sys",
    b"/mnt/sdext/a90/runtime/video/cache",
    b"video.cache.version=1",
    b"video.cache.play.trust_cache=1",
    b"video.cache.verify.actual_sha256=trust-cache-not-checked",
    b"kms-dumb-buffer-pageflip",
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
        raise RuntimeError(f"missing V2931 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2921_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2931 Bad Apple Long Preview Source Build",
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
        "- Parent live unit: V2930 proved pre-render drop skipping fixes the 10 second / 300 frame path; V2931 makes that validated window the menu preview default.",
        "",
        "## Included Delta",
        "",
        "- Packages the Bad Apple 10 second / 300 frame menu preview with the pre-render drop-skip scheduler into a flashable test image.",
        "- Keeps the full Bad Apple stream and PCM outside the boot image; boot carries only player/HUD code.",
        "- Keeps `--sync-start-offset-ms` and changes the sync drop policy to drop only when the frame is more than one frame interval late, instead of more than a half-frame late.",
        "- Keeps `badapple-scale` as the prior full-frame synthetic/cache preset for regression comparison.",
        "- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V2931 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2931 identity, real Bad Apple preset SHA, Player HUD sync-offset and drop-threshold strings, read-only telemetry HUD strings, and retained pageflip/mono1 markers.",
        "- Device validation is deferred to V2932: flash this exact image, run `version`/`status`/`selftest`, then prove the menu-equivalent 300-frame synced Player HUD run presents at least 95 percent of frames.",
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
        "- Candidate type: `badapple-long-preview-candidate`.",
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
        "candidate_type": "badapple-long-preview-candidate",
        "parent_test_artifact": "v2928-badapple-drop-threshold-live-flash-live-partial",
        "badapple_player_hud": {
            "version": 1,
            "source_unit": "V2931",
            "parent_unit": "V2925",
            "cache_root": "/mnt/sdext/a90/runtime/video/cache",
            "real_stream_sha256": "9e938aa83ef40aa692d0f42080821dc21a627f1dddd90cc9c2696aafe6ac6eb0",
            "asset_id": "badapple-480x360-full-v2903",
            "commands": [
                "video status",
                "video cache preset badapple status",
                "video cache preset badapple verify",
                "video cache preset badapple play --trust-cache [--frames N] [--present pageflip]",
                "video demo badapple play --trust-cache [--frames N] [--present pageflip]",
                "DEMO > BAD APPLE HUD A/V menu preview: audio play --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --duration-ms 4000 --execute; video demo badapple play --trust-cache --frames 120 --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-start-offset-ms 450",
            ],
            "large_asset_policy": "pre-rendered streams stay in the SHA-addressed SD-card cache, not inside the boot image",
            "live_validation": "pending-v2928",
        },
        "v2921_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "badapple-long-preview-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-long-preview-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2931",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
