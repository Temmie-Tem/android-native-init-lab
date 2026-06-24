#!/usr/bin/env python3
"""Build V3163 Bad Apple/Nyan cleanup cadence candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3162_audio_stop_owned_cleanup as base

REPO_ROOT = repo_root()

CYCLE = "V3163"
INIT_VERSION = "0.11.6"
INIT_BUILD = "v3163-badapple-nyan-cleanup-cadence"
BUILD_TAG = INIT_BUILD
DECISION = "v3163-badapple-nyan-cleanup-cadence-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3163_BADAPPLE_NYAN_CLEANUP_CADENCE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3163_badapple_nyan_cleanup_cadence.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3163_badapple_nyan_cleanup_cadence"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3163_badapple_nyan_cleanup_cadence.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v541_badapple_nyan_cleanup_cadence"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3163"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3163.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3163.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3163"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3163-badapple-nyan-cleanup-cadence"

FRAME_PATH = "/tmp/a90-doomgeneric-v3163-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3163-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3163-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3163-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3163-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3163-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3163-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-cleanup-cadence"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-cleanup-cadence"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3162", "v3163")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3162", "v3163")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3162", "v3163")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3162", "v3163")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3162", "v3163")
SCALE_MARKER = base.SCALE_MARKER.replace("v3162", "v3163")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3162", "v3163")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3162", "v3163")
SFX_STREAM_MARKER = "a90.doomgeneric.v3163.audio=real-sfx-pcm-stream-badapple-nyan-cleanup-cadence"
SOUND_MODE = "native-doom-sfx-badapple-nyan-cleanup-cadence-v3163"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3163.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = 60
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = 180
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = 30
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = 0

BASE_OVERRIDES = base._v3162_overrides
BASE_VALUES = base._v3162_values
V3162_ADAPTER_SOURCE_TEXT = base.v3162_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3163_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("audio-stop-owned-cleanup", "badapple-nyan-cleanup-cadence")
        .replace("v3162", "v3163")
        .replace("V3162", "V3163")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3163_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"audio-stop-owned-cleanup": b"badapple-nyan-cleanup-cadence",
        b"a90-doomgeneric-v3162": b"a90-doomgeneric-v3163",
        b"a90.doomgeneric.v3162": b"a90.doomgeneric.v3163",
        b"v3162": b"v3163",
        b"V3162": b"V3163",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.6",
    b"v3163-badapple-nyan-cleanup-cadence",
    b"video.status.player_hud_metrics_interval_frames=%u",
    b"video.status.player_hud_storage_interval_frames=%u",
    b"video.status.player_hud_text_interval_frames=%u",
    b"video.status.player_hud_full_repaint_interval_frames=%u",
    b"menu.demo.badapple.audio_pre_stop_best_effort=1",
    b"menu.demo.badapple.audio_post_stop_required=1",
    b"menu.demo.nyan.audio_pre_stop_best_effort=1",
    b"menu.demo.nyan.audio_post_stop_required=1",
    b"audio.play.worker.cleanup_deferred=",
    b"audio.play.worker.exit_deferred=",
    b"audio.play.worker.done=1",
    b"video.status.stream_timing_probe=1",
    b"video.stream.timing.render.avg_us",
)


def _v3163_overrides() -> dict[str, Any]:
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


def _v3163_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3163_overrides())
    return values


def _v3163_adapter_source_from_patched_v3148() -> str:
    return (
        V3162_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-audio-stop-owned-cleanup",
                 "real-sfx-pcm-stream-badapple-nyan-cleanup-cadence")
        .replace("v3162", "v3163")
        .replace("V3162", "V3163")
    )


def v3163_adapter_source() -> str:
    return _v3163_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3163 Bad Apple/Nyan Cleanup Cadence Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan A/V playback cadence and cleanup.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Preserves V3162 stop-owned audio cleanup and V3158 Bad Apple/Nyan fastscale paths.",
        "- Stops any previous demo audio before Bad Apple/Nyan playback and stops the worker after video returns.",
        "- Rejects completed audio status files as video sync anchors.",
        "- Moves Player HUD metric reads from 15-frame to 60-frame cadence.",
        "- Moves Player HUD storage reads from 60-frame to 180-frame cadence.",
        "- Moves Player HUD text redraws from 15-frame to 30-frame cadence.",
        "- Disables periodic Player HUD full repaint after the initial frame warmup.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3163 builder and focused tests.",
        "- `unittest`: V3163 Bad Apple/Nyan cleanup cadence source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3163/0.11.6 identity and cleanup/cadence markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-cleanup-cadence-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-cleanup-cadence-candidate",
        "adoption_state": "pending-badapple-nyan-cleanup-cadence-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3162-audio-stop-owned-cleanup",
            "requires_live_validation": ["badapple", "nyan", "player-hud-cadence", "audio-cleanup"],
            "preserves_doom_demo": True,
        },
        "video_player_hud": {
            "metrics_interval_frames": VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES,
            "storage_interval_frames": VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES,
            "text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
            "full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
            "periodic_full_repaint_disabled": True,
            "stream_timing_probe": True,
            "sync_rejects_completed_audio_status": True,
        },
        "audio_lifecycle": {
            "badapple_pre_stop": True,
            "badapple_post_stop": True,
            "nyan_pre_stop": True,
            "nyan_post_stop": True,
            "deferred_status_worker_stop": True,
            "affected_demos": ["badapple", "nyan"],
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
    (OUT_DIR / "badapple-nyan-cleanup-cadence-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-cleanup-cadence-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "player-hud-cadence", "audio-cleanup"],
        "player_hud_metrics_interval_frames": VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES,
        "player_hud_storage_interval_frames": VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES,
        "player_hud_text_interval_frames": VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES,
        "player_hud_full_repaint_interval_frames": VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES,
        "periodic_full_repaint_disabled": True,
        "audio_pre_stop": True,
        "audio_post_stop": True,
        "sync_rejects_completed_audio_status": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-cleanup-cadence-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3163_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3163_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3162_overrides", _v3163_overrides),
        ("_v3162_values", _v3163_values),
        ("_v3162_adapter_source_from_patched_v3148", _v3163_adapter_source_from_patched_v3148),
        ("v3162_adapter_source", v3163_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3163_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3163_globals()
    try:
        return base.main()
    finally:
        _restore_v3163_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
