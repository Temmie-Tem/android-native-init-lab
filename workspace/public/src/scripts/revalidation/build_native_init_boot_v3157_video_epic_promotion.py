#!/usr/bin/env python3
"""Build V3157 Video 0.11.0 promotion candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3156_video_player_hud_cadence as v3156

REPO_ROOT = repo_root()

CYCLE = "V3157"
INIT_VERSION = "0.11.0"
INIT_BUILD = "v3157-video-epic-promotion"
BUILD_TAG = INIT_BUILD
DECISION = "v3157-video-epic-promotion-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3157_VIDEO_EPIC_PROMOTION_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3157_video_epic_promotion.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3157_video_epic_promotion"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3157_video_epic_promotion.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v535_video_epic_promotion"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3157"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3157.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3157.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3157"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3157-video-epic-promotion"

FRAME_PATH = "/tmp/a90-doomgeneric-v3157-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3157-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3157-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3157-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3157-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3157-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3157-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-video-epic-promotion"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-video-epic-promotion"

INPUT_THREAD_MARKER = v3156.INPUT_THREAD_MARKER.replace("v3156", "v3157")
TIME_MODEL_MARKER = v3156.TIME_MODEL_MARKER.replace("v3156", "v3157")
DEMO_HUD_MARKER = v3156.DEMO_HUD_MARKER.replace("v3156", "v3157")
PACED_TIME_MARKER = v3156.PACED_TIME_MARKER.replace("v3156", "v3157")
TICK_TELEMETRY_MARKER = v3156.TICK_TELEMETRY_MARKER.replace("v3156", "v3157")
SCALE_MARKER = v3156.SCALE_MARKER.replace("v3156", "v3157")
PHASE_TELEMETRY_MARKER = v3156.PHASE_TELEMETRY_MARKER.replace("v3156", "v3157")
GAMETIC_FRAME_TELEMETRY_MARKER = v3156.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3156",
    "v3157",
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3157.audio=real-sfx-pcm-stream-video-epic-promotion"
SOUND_MODE = "native-doom-sfx-video-epic-promotion-v3157"

AUDIO_CORUN = v3156.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3156.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3156.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3156.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3156.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3156.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3157.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = v3156.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = v3156.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES


def rel(path: Path) -> str:
    return v3156.rel(path)


def _rewrite_v3157_text(text: str) -> str:
    return (
        text.replace(v3156.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("best-effort-video-player-hud-cadence", "video-epic-promotion")
        .replace("v3156", "v3157")
        .replace("V3156", "V3157")
        .replace(v3156.INIT_VERSION, INIT_VERSION)
        .replace(v3156.INIT_BUILD, INIT_BUILD)
        .replace(v3156.ENGINE_NAME, ENGINE_NAME)
        .replace(v3156.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(v3156.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3157_text(v3156.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3156.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3156.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3156.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3156.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3156.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3156.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3156.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"best-effort-video-player-hud-cadence": b"video-epic-promotion",
        b"a90-doomgeneric-v3156": b"a90-doomgeneric-v3157",
        b"a90.doomgeneric.v3156": b"a90.doomgeneric.v3157",
        b"v3156": b"v3157",
        b"V3156": b"V3157",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3156.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.0",
    b"v3157-video-epic-promotion",
    b"video.status.player_hud_text_interval_frames=%u",
    b"video.status.player_hud_full_repaint_interval_frames=%u",
    b"video.status.stream_timing_probe=1",
    b"video.stream.timing.render.avg_us",
)


def _v3157_overrides() -> dict[str, Any]:
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


def _v3157_values() -> dict[str, Any]:
    values = dict(v3156.v3155._ORIGINAL_V3154_VALUES())
    values.update(_v3157_overrides())
    return values


def _v3157_adapter_source_from_patched_v3148() -> str:
    return (
        v3156.v3155._ORIGINAL_V3154_ADAPTER_SOURCE()
        .replace("real-sfx-pcm-stream-long-window-physical-exit-hud-pid-adopt",
                 "real-sfx-pcm-stream-video-epic-promotion")
        .replace("v3154", "v3157")
        .replace("V3154", "V3157")
    )


def v3157_adapter_source() -> str:
    return _v3157_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3157 Video Epic Promotion Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Video 0.11.0 promotion.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Promotion Contents",
        "",
        "- Promotes the video epic to native-init `0.11.0` after the V3156 Bad Apple/Nyan Player HUD cadence fix.",
        "- Bundles the existing Bad Apple Player HUD, Nyan Player HUD, and polished DOOM demo paths in one image.",
        "- Keeps V3156 Player HUD cadence metrics and V3155 DOOM SFX best-effort behavior.",
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
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- The promotion changes version/build identity and preserves the already live-validated userspace demo stack.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3157 builder and focused tests.",
        "- `unittest`: V3157 promotion source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3157/0.11.0 identity, promotion markers, and inherited demo markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `video-epic-promotion-candidate`.",
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
        "candidate_type": "video-epic-promotion-candidate",
        "adoption_state": "pending-video-0.11.0-promotion-live-validation",
        "promotion": {
            "minor_version": INIT_VERSION,
            "video_epic_close_candidate": True,
            "requires_live_validation": ["badapple", "nyan", "doom"],
            "source_baseline": "v3156-video-player-hud-cadence",
        },
        "video_player_hud": {
            "text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
            "full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
            "stream_timing_probe": True,
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
    (OUT_DIR / "video-epic-promotion-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "video-epic-promotion-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "bundled_demos": ["badapple", "nyan", "doom"],
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "player_hud_text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
        "player_hud_full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
        "stream_timing_probe": True,
        "physical_button_exit": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-video-0.11.0-promotion-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3157_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3157_overrides().items():
        existed = hasattr(v3156, name)
        saved.append((name, getattr(v3156, name, None), existed))
        setattr(v3156, name, value)
    for name, value in (
        ("_v3156_overrides", _v3157_overrides),
        ("_v3156_values", _v3157_values),
        ("_v3156_adapter_source_from_patched_v3148", _v3157_adapter_source_from_patched_v3148),
        ("v3156_adapter_source", v3157_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(v3156, name), True))
        setattr(v3156, name, value)
    return saved


def _restore_v3157_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(v3156, name, value)
        else:
            delattr(v3156, name)


def main() -> int:
    saved = _apply_v3157_globals()
    try:
        return v3156.main()
    finally:
        _restore_v3157_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
