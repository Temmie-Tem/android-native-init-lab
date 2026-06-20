#!/usr/bin/env python3
"""Build V2952 native-init candidate with Bad Apple Player HUD fastpath."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v2859_audio_changelog_latest_refresh as v2859
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V2952"
INIT_VERSION = "0.10.52"
INIT_BUILD = "v2952-badapple-player-hud-fastpath"
BUILD_TAG = INIT_BUILD
DECISION = "v2952-badapple-player-hud-fastpath-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
REPORT_PATH = REPO_ROOT / "docs/reports/NATIVE_INIT_V2952_BADAPPLE_PLAYER_HUD_FASTPATH_SOURCE_BUILD_2026-06-20.md"
BOOT_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2952_badapple_player_hud_fastpath.img", legacy_fallback=False)
INIT_BINARY = OUT_DIR / "init_v2952_badapple_player_hud_fastpath"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v2952_badapple_player_hud_fastpath.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v477_badapple_player_hud_fastpath"

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.52 (v2952-badapple-player-hud-fastpath)",
    b"video.status.next_cache=video cache [status|verify|play] SHA256 [--trust-cache] [--present pageflip] [--layout full|player-hud] | video cache preset [badapple|badapple-scale] play [--trust-cache]",
    b"video.status.next_demo=video demo [badapple|badapple-scale] [status|verify|play] [--trust-cache]",
    b"DEMO >",
    b"BAD APPLE HUD",
    b"FULL A/V PLAYER HUD",
    b"menu.demo.badapple.frames=6962",
    b"menu.demo.badapple.restore=menu",
    b"menu.demo.badapple.action=play-av-fullsong",
    b"menu.demo.badapple.audio_duration_ms=232090",
    b"menu.demo.badapple.audio_amplitude_milli=150",
    b"menu.demo.badapple.audio_pcm_gain_milli=840",
    b"menu.demo.badapple.audio_pcm=/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
    b"menu.demo.badapple.audio_sync_status=/cache/a90-audio-play/status.txt",
    b"menu.demo.badapple.audio_sync_start_offset_ms=450",
    b"video.status.display_owner=1",
    b"video.status.player_hud_fastpath=1",
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
    b"BEAT FLASH %s  audio-clock onsets=%u nearest=%ums",
    b"video.stream.beat_flash.enabled=1",
    b"video.stream.beat_flash.source=%s",
    b"badapple-v2903-energy-onsets-v2941",
    b"video.stream.beat_flash.active_frames=%u",
    b"audio.play.cap.effective_duration_ms=%d",
    b"audio.play.cap.duration_policy=%s",
    b"audio.play.cap.badapple_fullsong_ms=%d",
    b"audio.play.cap.badapple_fullsong_sha256=%s",
    b"audio.play.execute.total_frames=%lld",
    b"audio.play.worker.total_frames=%lld",
    b"--pcm-gain-milli",
    b"audio.play.pcm_gain_milli=%d",
    b"audio.play.pcm_gain.attenuation_only=1",
    b"audio.play.execute.plan.pcm_gain_milli=%d",
    b"audio.play.pcm_file.scaled_peak_abs=%d",
    b"audio.play.execute.pcm_gain_milli=%d",
    b"audio.play.worker.pcm_gain_milli=%d",
    b"badapple-fullsong-pcm",
    b"/cache/a90-runtime/pkg/av/v2903/audio/audio.s16le",
    b"/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
    b"b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75",
    b"READONLY TELEMETRY /proc+/sys",
    b"/mnt/sdext/a90/runtime/video/cache",
    b"video.cache.version=1",
    b"video.cache.play.trust_cache=1",
    b"video.cache.verify.actual_sha256=trust-cache-not-checked",
    b"kms-dumb-buffer-pageflip",
    b"mono1",
    b"audio.play.execute.sequence=adsp,snd,app_type,setcal_hold,route_playback,pcm,route_playback_reset,setcal_deallocate",
    b"audio.play.integrated.sequence=adsp,snd,app_type,manifest_wait,setcal_hold,route_playback,pcm,route_playback_reset,setcal_deallocate",
    b"audio.stop.requires.route_reset_playback=1",
    b"audio route %s --reset --layer playback",
    b"audio route %s --apply --layer playback",
    b"route [profile] [--dry-run|--apply|--reset] [--layer all|core|feedback|endpoint|playback|blocked]",
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
        raise RuntimeError(f"missing V2952 boot-image markers: {missing}")
    return [marker.decode("ascii") for marker in REQUIRED_STRINGS]


def render_report(manifest: dict[str, Any], helper_flags: tuple[str, ...], init_extra_flags: tuple[str, ...]) -> str:
    bundled = manifest.get("audio_bundled_setcal", {}) if isinstance(manifest.get("audio_bundled_setcal"), dict) else {}
    markers = manifest.get("v2921_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V2952 Bad Apple Player HUD Fastpath Source Build",
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
        "- Parent live unit: V2951 showed V2950 solved display ownership but exposed a Player HUD throughput ceiling: full-song sync presented 2291/6962 frames, dropped 4671, and ran at about 9.8 fps while audio completed. V2952 keeps display ownership and reduces per-frame Player HUD framebuffer writes.",
        "",
        "## Included Delta",
        "",
        "- Marks the `video` command `CMD_DISPLAY`, causing the shell dispatcher to stop `autohud` before video playback and preventing intermittent status-HUD overwrites during the Player HUD demo.",
        "- Promotes `DEMO > BAD APPLE HUD` from the old short preview to the current full-song low-volume A/V path and adds a Player HUD render fastpath; live validation must prove whether this reaches the 30 fps Bad Apple DoD.",
        "- Keeps attenuation-only `--pcm-gain-milli` support for PCM-file playback, preserving the path-scoped `badapple-fullsong-pcm` duration policy and 64-bit long PCM frame geometry.",
        "- Keeps the full Bad Apple stream and PCM outside the boot image; boot carries only player/HUD/audio policy code.",
        "- Keeps `--sync-start-offset-ms` and the late-frame skip policy; this unit targets render throughput rather than sync semantics.",
        "- Keeps `badapple-scale` as the prior full-frame synthetic/cache preset for regression comparison.",
        "- Does not add Venus, GPU, raw DSI, backlight, PMIC, PWM, regulator, GPIO, GDSC, or telemetry write paths.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V2952 builder.",
        "- Build: AArch64 static native-init compile, helper compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V2952 identity, real Bad Apple preset SHA, full-song DEMO menu markers, `video.status.player_hud_fastpath=1` marker, Player HUD sync-offset/drop-threshold strings, BEAT FLASH table/source markers, full-song audio cap, PCM64 geometry, attenuation-only PCM gain markers, read-only telemetry HUD strings, and retained pageflip/mono1 markers.",
        "- Device validation is deferred to V2953: flash this exact image, run short throughput probes and a full-length Bad Apple Player HUD A/V pass, and confirm presented/total, dropped frames, audio completion, beat-flash activity, and `selftest fail=0`.",
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
        "- Candidate type: `badapple-player-hud-fastpath-candidate`.",
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
        "candidate_type": "badapple-player-hud-fastpath-candidate",
        "parent_test_artifact": "v2949-badapple-pcm-gain-fullsong-live-pass",
        "badapple_player_hud": {
            "version": 1,
            "source_unit": "V2952",
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
                "DEMO > BAD APPLE HUD A/V fullsong: audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 150 --pcm-gain-milli 840 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute; video demo badapple play --trust-cache --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450",
                "Full-length direct validation: audio play internal-speaker-safe --mode listen --duration-ms 232090 --amplitude-milli 150 --pcm-gain-milli 840 --pcm-file /cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le --execute; video demo badapple play --trust-cache --present pageflip --layout player-hud --sync-audio-status /cache/a90-audio-play/status.txt --sync-wait-ms 60000 --sync-start-offset-ms 450",
            ],
            "fullsong_audio": {
                "policy": "badapple-fullsong-pcm",
                "duration_cap_ms": 240000,
                "recommended_duration_ms": 232090,
                "recommended_pcm_gain_milli": 840,
                "amplitude_milli": 150,
                "primary_remote_pcm": "/cache/a90-runtime/pkg/av/v2920/audio/badapple.s16le",
                "host_source_pcm": "workspace/private/demo-assets/video/v2903-badapple-480x360-full/audio/audio.s16le",
                "sha256": "b96d2e0bc4bb6b0ada0da6e63e40168115e3818d72c386dd8764162e85238a75",
            },
            "large_asset_policy": "pre-rendered streams stay in the SHA-addressed SD-card cache, not inside the boot image",
            "live_validation": "pending-v2951",
        },
        "v2921_marker_strings": marker_strings,
        "adoption_state": "pending-live-validation",
    })
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest, tuple(manifest.get("helper_flags", ())), tuple(manifest.get("init_extra_flags", ()))), encoding="utf-8")
    (OUT_DIR / "badapple-player-hud-fastpath-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-player-hud-fastpath-candidate",
        "boot_image": str(BOOT_IMAGE.relative_to(REPO_ROOT)),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "source_unit": "V2952",
        "source_report": str(REPORT_PATH.relative_to(REPO_ROOT)),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
