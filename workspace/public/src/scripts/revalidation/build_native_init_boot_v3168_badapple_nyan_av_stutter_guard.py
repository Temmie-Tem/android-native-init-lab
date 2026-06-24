#!/usr/bin/env python3
"""Build V3168 Bad Apple/Nyan A/V stutter guard candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3167_badapple_nyan_stable_av as base

REPO_ROOT = repo_root()

CYCLE = "V3168"
INIT_VERSION = "0.11.11"
INIT_BUILD = "v3168-badapple-nyan-av-stutter-guard"
BUILD_TAG = INIT_BUILD
DECISION = "v3168-badapple-nyan-av-stutter-guard-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3168_BADAPPLE_NYAN_AV_STUTTER_GUARD_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3168_badapple_nyan_av_stutter_guard.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3168_badapple_nyan_av_stutter_guard"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3168_badapple_nyan_av_stutter_guard.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v545_badapple_nyan_av_stutter_guard"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3168"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3168.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3168.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3168"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3168-badapple-nyan-av-stutter-guard"

FRAME_PATH = "/tmp/a90-doomgeneric-v3168-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3168-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3168-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3168-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3168-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3168-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3168-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-av-stutter-guard"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-av-stutter-guard"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3167", "v3168")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3167", "v3168")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3167", "v3168")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3167", "v3168")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3167", "v3168")
SCALE_MARKER = base.SCALE_MARKER.replace("v3167", "v3168")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3167", "v3168")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3167", "v3168")
SFX_STREAM_MARKER = "a90.doomgeneric.v3168.audio=real-sfx-pcm-stream-badapple-nyan-av-stutter-guard"
SOUND_MODE = "native-doom-sfx-badapple-nyan-av-stutter-guard-v3168"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3168.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = base.VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS
VIDEO_PLAYER_HUD_LIVE_TELEMETRY = 0
VIDEO_PLAYER_HUD_DYNAMIC_TEXT = 0

BASE_OVERRIDES = base._v3167_overrides
BASE_VALUES = base._v3167_values
V3167_ADAPTER_SOURCE_TEXT = base.v3167_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3168_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-stable-av", "badapple-nyan-av-stutter-guard")
        .replace("v3167", "v3168")
        .replace("V3167", "V3168")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3168_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-stable-av": b"badapple-nyan-av-stutter-guard",
        b"a90-doomgeneric-v3167": b"a90-doomgeneric-v3168",
        b"a90.doomgeneric.v3167": b"a90.doomgeneric.v3168",
        b"v3167": b"v3168",
        b"V3167": b"V3168",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.11",
    b"v3168-badapple-nyan-av-stutter-guard",
    b"video.status.player_hud_live_telemetry=%d",
    b"video.status.player_hud_dynamic_text=%d",
    b"LIVE TELEMETRY OFF DURING PLAYBACK",
    b"video.status.menu_av_present=setcrtc",
    b"video.status.menu_av_late_drop=disabled-setcrtc-default",
    b"menu.demo.badapple.video_present=setcrtc",
    b"menu.demo.nyan.video_present=setcrtc",
)


def _v3168_overrides() -> dict[str, Any]:
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


def _v3168_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3168_overrides())
    return values


def _v3168_adapter_source_from_patched_v3148() -> str:
    return (
        V3167_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-stable-av",
                 "real-sfx-pcm-stream-badapple-nyan-av-stutter-guard")
        .replace("v3167", "v3168")
        .replace("V3167", "V3168")
    )


def v3168_adapter_source() -> str:
    return _v3168_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3168 Bad Apple/Nyan AV Stutter Guard Source Build",
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
        "- Keeps the V3167 `setcrtc` stable present path for Bad Apple/Nyan.",
        "- Disables live Player HUD telemetry during playback; no `/proc` or storage snapshot reads run inside the frame loop.",
        "- Freezes dynamic Player HUD text after the initial paint so progress/lamp updates remain cheap and predictable.",
        "- Preserves V3167 audio tail guard, physical-button exit, and DOOM input/audio behavior.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3168 builder and focused tests.",
        "- `unittest`: V3168 Bad Apple/Nyan A/V stutter guard source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3168/0.11.11 identity and stutter-guard markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-av-stutter-guard-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-av-stutter-guard-candidate",
        "adoption_state": "pending-badapple-nyan-av-stutter-guard-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3167-badapple-nyan-stable-av",
            "requires_live_validation": [
                "badapple",
                "nyan",
                "player-hud-static-telemetry",
                "player-hud-static-text",
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
            "live_telemetry": bool(VIDEO_PLAYER_HUD_LIVE_TELEMETRY),
            "dynamic_text": bool(VIDEO_PLAYER_HUD_DYNAMIC_TEXT),
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
    (OUT_DIR / "badapple-nyan-av-stutter-guard-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-av-stutter-guard-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "badapple",
            "nyan",
            "player-hud-static-telemetry",
            "player-hud-static-text",
            "audio-tail-guard",
        ],
        "telemetry_deadline_guard_ns": VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS,
        "live_telemetry": bool(VIDEO_PLAYER_HUD_LIVE_TELEMETRY),
        "dynamic_text": bool(VIDEO_PLAYER_HUD_DYNAMIC_TEXT),
        "stream_physical_button_exit": True,
        "stream_physical_exit_polls_per_frame": 1,
        "audio_tail_guard": True,
        "menu_present_mode": "setcrtc",
        "preset_default_present_mode": "setcrtc",
        "pageflip_diagnostic_available": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-stutter-guard-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3168_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3168_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3167_overrides", _v3168_overrides),
        ("_v3167_values", _v3168_values),
        ("_v3167_adapter_source_from_patched_v3148", _v3168_adapter_source_from_patched_v3148),
        ("v3167_adapter_source", v3168_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3168_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3168_globals()
    try:
        return base.main()
    finally:
        _restore_v3168_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
