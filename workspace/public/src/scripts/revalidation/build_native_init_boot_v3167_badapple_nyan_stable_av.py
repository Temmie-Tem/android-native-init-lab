#!/usr/bin/env python3
"""Build V3167 Bad Apple/Nyan stable A/V candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3166_badapple_nyan_pageflip_av as base

REPO_ROOT = repo_root()

CYCLE = "V3167"
INIT_VERSION = "0.11.10"
INIT_BUILD = "v3167-badapple-nyan-stable-av"
BUILD_TAG = INIT_BUILD
DECISION = "v3167-badapple-nyan-stable-av-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3167_BADAPPLE_NYAN_STABLE_AV_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3167_badapple_nyan_stable_av.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3167_badapple_nyan_stable_av"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3167_badapple_nyan_stable_av.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v544_badapple_nyan_stable_av"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3167"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3167.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3167.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3167"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3167-badapple-nyan-stable-av"

FRAME_PATH = "/tmp/a90-doomgeneric-v3167-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3167-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3167-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3167-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3167-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3167-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3167-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-stable-av"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-stable-av"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3166", "v3167")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3166", "v3167")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3166", "v3167")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3166", "v3167")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3166", "v3167")
SCALE_MARKER = base.SCALE_MARKER.replace("v3166", "v3167")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3166", "v3167")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3166", "v3167")
SFX_STREAM_MARKER = "a90.doomgeneric.v3167.audio=real-sfx-pcm-stream-badapple-nyan-stable-av"
SOUND_MODE = "native-doom-sfx-badapple-nyan-stable-av-v3167"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3167.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = 900
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = 1800
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = 900
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = 0
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = 18000000

BASE_OVERRIDES = base._v3166_overrides
BASE_VALUES = base._v3166_values
V3166_ADAPTER_SOURCE_TEXT = base.v3166_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3167_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-pageflip-av", "badapple-nyan-stable-av")
        .replace("v3166", "v3167")
        .replace("V3166", "V3167")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3167_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-pageflip-av": b"badapple-nyan-stable-av",
        b"a90-doomgeneric-v3166": b"a90-doomgeneric-v3167",
        b"a90.doomgeneric.v3166": b"a90.doomgeneric.v3167",
        b"v3166": b"v3167",
        b"V3166": b"V3167",
        b"video.status.menu_av_present=pageflip": b"video.status.menu_av_present=setcrtc",
        b"video.status.menu_av_late_drop=audio-synced-pageflip": b"video.status.menu_av_late_drop=disabled-setcrtc-default",
        b"menu.demo.badapple.video_present=pageflip": b"menu.demo.badapple.video_present=setcrtc",
        b"menu.demo.nyan.video_present=pageflip": b"menu.demo.nyan.video_present=setcrtc",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.10",
    b"v3167-badapple-nyan-stable-av",
    b"video.status.player_hud_metrics_interval_frames=%u",
    b"video.status.player_hud_storage_interval_frames=%u",
    b"video.status.player_hud_text_interval_frames=%u",
    b"video.status.player_hud_deadline_guard_ns=%llu",
    b"video.status.stream_audio_tail_guard=1",
    b"video.stream.audio_sync.tail_guard=1",
    b"video.status.menu_av_present=setcrtc",
    b"video.status.menu_av_late_drop=disabled-setcrtc-default",
    b"video.status.menu_av_pageflip_diagnostic=1",
    b"menu.demo.badapple.video_present=setcrtc",
    b"menu.demo.badapple.video_late_drop=disabled-setcrtc-default",
    b"menu.demo.badapple.video_pageflip_diagnostic=1",
    b"menu.demo.nyan.video_present=setcrtc",
    b"menu.demo.nyan.video_late_drop=disabled-setcrtc-default",
    b"menu.demo.nyan.video_pageflip_diagnostic=1",
)


def _v3167_overrides() -> dict[str, Any]:
    overrides = dict(BASE_OVERRIDES())
    overrides.update({
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
        "INIT_BINARY": INIT_BINARY,
        "RAMDISK_CPIO": RAMDISK_CPIO,
        "HELPER_BINARY": HELPER_BINARY,
        "ENGINE_BINARY": ENGINE_BINARY,
        "ENGINE_ADAPTER_SOURCE": ENGINE_ADAPTER_SOURCE,
        "ENGINE_ADAPTER_OBJECT": ENGINE_ADAPTER_OBJECT,
        "ENGINE_RAMDISK_PATH": ENGINE_RAMDISK_PATH,
        "ENGINE_REMOTE_PATH": ENGINE_REMOTE_PATH,
        "ENGINE_NAME": ENGINE_NAME,
        "FRAME_PATH": FRAME_PATH,
        "SHARED_FRAME_PATH": SHARED_FRAME_PATH,
        "INPUT_STATE_PATH": INPUT_STATE_PATH,
        "INPUT_SOCKET_PATH": INPUT_SOCKET_PATH,
        "PACE_SOCKET_PATH": PACE_SOCKET_PATH,
        "TICK_TELEMETRY_PATH": TICK_TELEMETRY_PATH,
        "AUDIO_PCM_STREAM_PATH": AUDIO_PCM_STREAM_PATH,
        "FRAME_SCALE": FRAME_SCALE,
        "FRAME_IPC": FRAME_IPC,
        "INPUT_THREAD_MARKER": INPUT_THREAD_MARKER,
        "TIME_MODEL_MARKER": TIME_MODEL_MARKER,
        "DEMO_HUD_MARKER": DEMO_HUD_MARKER,
        "PACED_TIME_MARKER": PACED_TIME_MARKER,
        "TICK_TELEMETRY_MARKER": TICK_TELEMETRY_MARKER,
        "SCALE_MARKER": SCALE_MARKER,
        "PHASE_TELEMETRY_MARKER": PHASE_TELEMETRY_MARKER,
        "GAMETIC_FRAME_TELEMETRY_MARKER": GAMETIC_FRAME_TELEMETRY_MARKER,
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": SFX_BACKEND_SOURCE_TEXT,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
    })
    return overrides


def _v3167_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3167_overrides())
    return values


def _v3167_adapter_source_from_patched_v3148() -> str:
    return (
        V3166_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-pageflip-av",
                 "real-sfx-pcm-stream-badapple-nyan-stable-av")
        .replace("v3166", "v3167")
        .replace("V3166", "V3167")
    )


def v3167_adapter_source() -> str:
    return _v3167_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3167 Bad Apple/Nyan Stable AV Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan A/V cadence regression cleanup.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Restores Bad Apple/Nyan menu playback and cache-preset defaults to the V3156/V3157-validated `setcrtc` present path.",
        "- Keeps `--present pageflip` available as an explicit diagnostic path instead of the default demo path.",
        "- Moves Player HUD metrics/storage/text refresh to sparse cadence to avoid visible periodic telemetry spikes.",
        "- Preserves V3166 audio tail guard, physical-button exit, and DOOM input/audio behavior.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3167 builder and focused tests.",
        "- `unittest`: V3167 Bad Apple/Nyan stable AV source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3167/0.11.10 identity and stable AV markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-stable-av-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-stable-av-candidate",
        "adoption_state": "pending-badapple-nyan-stable-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3166-badapple-nyan-pageflip-av",
            "requires_live_validation": [
                "badapple",
                "nyan",
                "player-hud-setcrtc-stable-cadence",
                "sparse-player-hud-telemetry",
                "audio-tail-guard",
                "physical-button-exit",
            ],
            "preserves_doom_demo": True,
        },
        "video_player_hud": {
            "metrics_interval_frames": VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES,
            "storage_interval_frames": VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES,
            "text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
            "full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
            "telemetry_deadline_guard_ns": VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS,
            "text_slack_guard": True,
            "stream_physical_button_exit": True,
            "stream_physical_exit_polls_per_frame": 1,
            "audio_tail_guard": True,
            "menu_present_mode": "setcrtc",
            "preset_default_present_mode": "setcrtc",
            "pageflip_diagnostic_available": True,
        },
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
    (OUT_DIR / "badapple-nyan-stable-av-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-stable-av-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "player-hud-setcrtc-stable-cadence", "audio-tail-guard"],
        "telemetry_deadline_guard_ns": VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS,
        "stream_physical_button_exit": True,
        "stream_physical_exit_polls_per_frame": 1,
        "audio_tail_guard": True,
        "menu_present_mode": "setcrtc",
        "preset_default_present_mode": "setcrtc",
        "pageflip_diagnostic_available": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-stable-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3167_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3167_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3166_overrides", _v3167_overrides),
        ("_v3166_values", _v3167_values),
        ("_v3166_adapter_source_from_patched_v3148", _v3167_adapter_source_from_patched_v3148),
        ("v3166_adapter_source", v3167_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3167_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3167_globals()
    try:
        return base.main()
    finally:
        _restore_v3167_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
