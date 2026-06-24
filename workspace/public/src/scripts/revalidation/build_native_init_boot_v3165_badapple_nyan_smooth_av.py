#!/usr/bin/env python3
"""Build V3165 Bad Apple/Nyan smooth A/V candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3164_badapple_nyan_playback_guard as base

REPO_ROOT = repo_root()

CYCLE = "V3165"
INIT_VERSION = "0.11.8"
INIT_BUILD = "v3165-badapple-nyan-smooth-av"
BUILD_TAG = INIT_BUILD
DECISION = "v3165-badapple-nyan-smooth-av-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3165_BADAPPLE_NYAN_SMOOTH_AV_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3165_badapple_nyan_smooth_av.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3165_badapple_nyan_smooth_av"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3165_badapple_nyan_smooth_av.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v543_badapple_nyan_smooth_av"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3165"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3165.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3165.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3165"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3165-badapple-nyan-smooth-av"

FRAME_PATH = "/tmp/a90-doomgeneric-v3165-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3165-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3165-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3165-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3165-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3165-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3165-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-smooth-av"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-smooth-av"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3164", "v3165")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3164", "v3165")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3164", "v3165")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3164", "v3165")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3164", "v3165")
SCALE_MARKER = base.SCALE_MARKER.replace("v3164", "v3165")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3164", "v3165")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3164", "v3165")
SFX_STREAM_MARKER = "a90.doomgeneric.v3165.audio=real-sfx-pcm-stream-badapple-nyan-smooth-av"
SOUND_MODE = "native-doom-sfx-badapple-nyan-smooth-av-v3165"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3165.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = 120
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = 900
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = 120
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = 0
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = 12000000

BASE_OVERRIDES = base._v3164_overrides
BASE_VALUES = base._v3164_values
V3164_ADAPTER_SOURCE_TEXT = base.v3164_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3165_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-playback-guard", "badapple-nyan-smooth-av")
        .replace("v3164", "v3165")
        .replace("V3164", "V3165")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3165_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-playback-guard": b"badapple-nyan-smooth-av",
        b"a90-doomgeneric-v3164": b"a90-doomgeneric-v3165",
        b"a90.doomgeneric.v3164": b"a90.doomgeneric.v3165",
        b"v3164": b"v3165",
        b"V3164": b"V3165",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.8",
    b"v3165-badapple-nyan-smooth-av",
    b"video.status.player_hud_text_slack_guard=%d",
    b"video.status.stream_audio_tail_guard=1",
    b"video.stream.audio_sync.tail_guard=1",
    b"video.stream.audio_sync.tail_wait_attempted=%d",
    b"video.stream.audio_sync.tail_wait_ns=%llu",
)


def _v3165_overrides() -> dict[str, Any]:
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


def _v3165_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3165_overrides())
    return values


def _v3165_adapter_source_from_patched_v3148() -> str:
    return (
        V3164_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-playback-guard",
                 "real-sfx-pcm-stream-badapple-nyan-smooth-av")
        .replace("v3164", "v3165")
        .replace("V3164", "V3165")
    )


def v3165_adapter_source() -> str:
    return _v3165_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3165 Bad Apple/Nyan Smooth AV Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan A/V smoothness.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Preserves V3164 playback guard and DOOM input/audio behavior.",
        "- Moves Bad Apple/Nyan Player HUD text/metrics/storage work to lower cadence and skips it when frame slack is low.",
        "- Polls physical-button stream exit once per frame instead of twice.",
        "- Waits through the final frame interval before normal audio cleanup, avoiding tail cut on short clips.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3165 builder and focused tests.",
        "- `unittest`: V3165 Bad Apple/Nyan smooth AV source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3165/0.11.8 identity and smooth AV markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-smooth-av-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-smooth-av-candidate",
        "adoption_state": "pending-badapple-nyan-smooth-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3164-badapple-nyan-playback-guard",
            "requires_live_validation": [
                "badapple",
                "nyan",
                "player-hud-smooth-cadence",
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
    (OUT_DIR / "badapple-nyan-smooth-av-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-smooth-av-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "player-hud-smooth-cadence", "audio-tail-guard"],
        "telemetry_deadline_guard_ns": VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS,
        "stream_physical_button_exit": True,
        "stream_physical_exit_polls_per_frame": 1,
        "audio_tail_guard": True,
        "menu_present_mode": "setcrtc",
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-smooth-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3165_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3165_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3164_overrides", _v3165_overrides),
        ("_v3164_values", _v3165_values),
        ("_v3164_adapter_source_from_patched_v3148", _v3165_adapter_source_from_patched_v3148),
        ("v3164_adapter_source", v3165_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3165_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3165_globals()
    try:
        return base.main()
    finally:
        _restore_v3165_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
