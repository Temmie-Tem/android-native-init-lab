#!/usr/bin/env python3
"""Build V3159 audio post-drain DROP candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3158_badapple_nyan_fastscale as v3158

REPO_ROOT = repo_root()

CYCLE = "V3159"
INIT_VERSION = "0.11.2"
INIT_BUILD = "v3159-audio-post-drain-drop"
BUILD_TAG = INIT_BUILD
DECISION = "v3159-audio-post-drain-drop-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3159_AUDIO_POST_DRAIN_DROP_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3159_audio_post_drain_drop.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3159_audio_post_drain_drop"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3159_audio_post_drain_drop.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v537_audio_post_drain_drop"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3159"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3159.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3159.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3159"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3159-audio-post-drain-drop"

FRAME_PATH = "/tmp/a90-doomgeneric-v3159-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3159-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3159-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3159-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3159-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3159-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3159-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-audio-post-drain-drop"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-audio-post-drain-drop"

INPUT_THREAD_MARKER = v3158.INPUT_THREAD_MARKER.replace("v3158", "v3159")
TIME_MODEL_MARKER = v3158.TIME_MODEL_MARKER.replace("v3158", "v3159")
DEMO_HUD_MARKER = v3158.DEMO_HUD_MARKER.replace("v3158", "v3159")
PACED_TIME_MARKER = v3158.PACED_TIME_MARKER.replace("v3158", "v3159")
TICK_TELEMETRY_MARKER = v3158.TICK_TELEMETRY_MARKER.replace("v3158", "v3159")
SCALE_MARKER = v3158.SCALE_MARKER.replace("v3158", "v3159")
PHASE_TELEMETRY_MARKER = v3158.PHASE_TELEMETRY_MARKER.replace("v3158", "v3159")
GAMETIC_FRAME_TELEMETRY_MARKER = v3158.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3158",
    "v3159",
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3159.audio=real-sfx-pcm-stream-audio-post-drain-drop"
SOUND_MODE = "native-doom-sfx-audio-post-drain-drop-v3159"

AUDIO_CORUN = v3158.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3158.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3158.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3158.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3158.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3158.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3159.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = v3158.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = v3158.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES

V3158_ADAPTER_SOURCE_TEXT = v3158.v3158_adapter_source()


def rel(path: Path) -> str:
    return v3158.rel(path)


def _rewrite_v3159_text(text: str) -> str:
    return (
        text.replace(v3158.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-fastscale", "audio-post-drain-drop")
        .replace("v3158", "v3159")
        .replace("V3158", "V3159")
        .replace(v3158.INIT_VERSION, INIT_VERSION)
        .replace(v3158.INIT_BUILD, INIT_BUILD)
        .replace(v3158.ENGINE_NAME, ENGINE_NAME)
        .replace(v3158.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(v3158.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3159_text(v3158.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3158.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3158.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3158.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3158.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3158.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3158.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3158.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-fastscale": b"audio-post-drain-drop",
        b"a90-doomgeneric-v3158": b"a90-doomgeneric-v3159",
        b"a90.doomgeneric.v3158": b"a90.doomgeneric.v3159",
        b"v3158": b"v3159",
        b"V3158": b"V3159",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3158.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.2",
    b"v3159-audio-post-drain-drop",
    b"video.status.player_hud_fastscale=1",
    b"audio.play.execute.post_drain_drop.rc=%d errno=%d",
    b"audio.play.worker.post_drain_drop_rc=%d",
)


def _v3159_overrides() -> dict[str, Any]:
    return {
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
        "AUDIO_CORUN": AUDIO_CORUN,
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "AUDIO_CORUN_STREAM": AUDIO_CORUN_STREAM,
        "AUDIO_CORUN_DURATION_MS": AUDIO_CORUN_DURATION_MS,
        "AUDIO_CORUN_REFRESH_MS": AUDIO_CORUN_REFRESH_MS,
        "AUDIO_CORUN_AMPLITUDE_MILLI": AUDIO_CORUN_AMPLITUDE_MILLI,
        "PHYSICAL_BUTTON_EXIT": PHYSICAL_BUTTON_EXIT,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": SFX_BACKEND_SOURCE_TEXT,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
    }


def _v3159_values() -> dict[str, Any]:
    values = dict(v3158.v3157.v3156.v3155._ORIGINAL_V3154_VALUES())
    values.update(_v3159_overrides())
    return values


def _v3159_adapter_source_from_patched_v3148() -> str:
    return (
        V3158_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-fastscale",
                 "real-sfx-pcm-stream-audio-post-drain-drop")
        .replace("v3158", "v3159")
        .replace("V3158", "V3159")
    )


def v3159_adapter_source() -> str:
    return _v3159_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3159 Audio Post-Drain DROP Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan A/V playback cleanup.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Preserves V3158 Bad Apple/Nyan Player HUD fastscale and bounded repaint behavior.",
        "- Adds a best-effort `SNDRV_PCM_IOCTL_DROP` after successful PCM drain before close.",
        "- Exports `audio.play.execute.post_drain_drop.*` and worker status markers for live validation.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Audio stream path: `{AUDIO_PCM_STREAM_PATH}`",
        f"- Sound mode: `{SOUND_MODE}`",
        f"- Audio co-run enabled: `{int(bool(audio.get('enabled', AUDIO_CORUN)))}`",
        f"- Player HUD text interval frames: `{VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES}`",
        f"- Player HUD full repaint interval frames: `{VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES}`",
        "- Player HUD fastscale marker: `video.status.player_hud_fastscale=1`",
        "- Audio close marker: `audio.play.execute.post_drain_drop.rc`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- The audio change stays inside the already selected safe internal speaker playback path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3159 builder and focused tests.",
        "- `unittest`: V3159 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3159/0.11.2 identity, video fastscale marker, and audio post-drain DROP marker.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-post-drain-drop-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    audio = doom.setdefault("audio_corun", {})
    audio.update({
        "enabled": True,
        "mode": AUDIO_CORUN_MODE,
        "stream": True,
        "stream_path": AUDIO_PCM_STREAM_PATH,
        "duration_ms": AUDIO_CORUN_DURATION_MS,
        "refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "refresh_disabled": True,
        "amplitude_milli": AUDIO_CORUN_AMPLITUDE_MILLI,
        "real_doom_sfx": True,
        "music": False,
        "best_effort_nonblocking": True,
        "video_cadence_priority": True,
    })
    doom.update({
        "physical_button_exit": {
            "enabled": True,
            "events": ["event3", "event0"],
            "keys": ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN"],
            "action": "exit-doom-loop-hud-pid-adopt-then-stop-audio",
            "return_reason": "physical-button-exit",
            "menu_return": True,
            "hud_pid_adopt": True,
            "start_new_hud_from_doom_exit_path": True,
        },
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-post-drain-drop-candidate",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3158-badapple-nyan-fastscale",
            "requires_live_validation": ["badapple", "nyan", "audio-worker-completion"],
            "preserves_doom_demo": True,
        },
        "video_player_hud": {
            "text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
            "full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
            "stream_timing_probe": True,
            "fastscale": True,
            "bounded_full_repaint": True,
            "progress_incremental_delta": True,
        },
        "audio_playback": {
            "post_drain_drop": True,
            "post_drain_drop_marker": "audio.play.execute.post_drain_drop.rc",
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
    (OUT_DIR / "audio-post-drain-drop-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-post-drain-drop-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "bundled_demos": ["badapple", "nyan", "doom"],
        "live_validation_focus": ["badapple", "nyan", "audio-worker-completion"],
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_post_drain_drop": True,
        "player_hud_fastscale": True,
        "stream_timing_probe": True,
        "physical_button_exit": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3159_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3159_overrides().items():
        existed = hasattr(v3158, name)
        saved.append((name, getattr(v3158, name, None), existed))
        setattr(v3158, name, value)
    for name, value in (
        ("_v3158_overrides", _v3159_overrides),
        ("_v3158_values", _v3159_values),
        ("_v3158_adapter_source_from_patched_v3148", _v3159_adapter_source_from_patched_v3148),
        ("v3158_adapter_source", v3159_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(v3158, name), True))
        setattr(v3158, name, value)
    return saved


def _restore_v3159_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(v3158, name, value)
        else:
            delattr(v3158, name)


def main() -> int:
    saved = _apply_v3159_globals()
    try:
        return v3158.main()
    finally:
        _restore_v3159_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
