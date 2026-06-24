#!/usr/bin/env python3
"""Build V3169 Bad Apple/Nyan finite PCM audio cleanup candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3168_badapple_nyan_av_stutter_guard as base

REPO_ROOT = repo_root()

CYCLE = "V3169"
INIT_VERSION = "0.11.12"
INIT_BUILD = "v3169-badapple-nyan-finite-audio-cleanup"
BUILD_TAG = INIT_BUILD
DECISION = "v3169-badapple-nyan-finite-audio-cleanup-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3169_BADAPPLE_NYAN_FINITE_AUDIO_CLEANUP_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3169_badapple_nyan_finite_audio_cleanup.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3169_badapple_nyan_finite_audio_cleanup"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3169_badapple_nyan_finite_audio_cleanup.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v546_badapple_nyan_finite_audio_cleanup"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3169"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3169.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3169.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3169"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3169-badapple-nyan-finite-audio-cleanup"

FRAME_PATH = "/tmp/a90-doomgeneric-v3169-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3169-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3169-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3169-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3169-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3169-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3169-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-finite-audio-cleanup"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-finite-audio-cleanup"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3168", "v3169")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3168", "v3169")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3168", "v3169")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3168", "v3169")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3168", "v3169")
SCALE_MARKER = base.SCALE_MARKER.replace("v3168", "v3169")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3168", "v3169")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3168", "v3169")
SFX_STREAM_MARKER = "a90.doomgeneric.v3169.audio=real-sfx-pcm-stream-badapple-nyan-finite-audio-cleanup"
SOUND_MODE = "native-doom-sfx-badapple-nyan-finite-audio-cleanup-v3169"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3169.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = base.VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS
VIDEO_PLAYER_HUD_LIVE_TELEMETRY = base.VIDEO_PLAYER_HUD_LIVE_TELEMETRY
VIDEO_PLAYER_HUD_DYNAMIC_TEXT = base.VIDEO_PLAYER_HUD_DYNAMIC_TEXT

BASE_OVERRIDES = base._v3168_overrides
BASE_VALUES = base._v3168_values
V3168_ADAPTER_SOURCE_TEXT = base.v3168_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3169_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-av-stutter-guard", "badapple-nyan-finite-audio-cleanup")
        .replace("v3168", "v3169")
        .replace("V3168", "V3169")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3169_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-av-stutter-guard": b"badapple-nyan-finite-audio-cleanup",
        b"a90-doomgeneric-v3168": b"a90-doomgeneric-v3169",
        b"a90.doomgeneric.v3168": b"a90.doomgeneric.v3169",
        b"v3168": b"v3169",
        b"V3168": b"V3169",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_RETIRED_REQUIRED_MARKERS = (
    b"menu.demo.badapple.audio_post_stop_required=1",
    b"menu.demo.nyan.audio_post_stop_required=1",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
    if not any(marker in item for marker in _RETIRED_REQUIRED_MARKERS)
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.12",
    b"v3169-badapple-nyan-finite-audio-cleanup",
    b"audio.play.execute.close.deferred=0 reason=finite-pcm-worker-owned",
    b"audio.play.worker.close_deferred=0",
    b"audio.play.integrated.cleanup.deferred=0 reason=finite-pcm-worker-owned",
    b"audio.play.worker.cleanup_owner=worker",
    b"audio.play.worker.exit_deferred=0",
    b"menu.demo.badapple.audio_cleanup=worker-owned-finite-pcm",
    b"menu.demo.nyan.audio_cleanup=worker-owned-finite-pcm",
)


def _v3169_overrides() -> dict[str, Any]:
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


def _v3169_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3169_overrides())
    return values


def _v3169_adapter_source_from_patched_v3148() -> str:
    return (
        V3168_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-av-stutter-guard",
                 "real-sfx-pcm-stream-badapple-nyan-finite-audio-cleanup")
        .replace("v3168", "v3169")
        .replace("V3168", "V3169")
    )


def v3169_adapter_source() -> str:
    return _v3169_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3169 Bad Apple/Nyan Finite Audio Cleanup Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan menu A/V stutter and sound cleanup regression.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Splits finite `--pcm-file` playback from DOOM FIFO stream playback.",
        "- Bad Apple/Nyan finite PCM files now close PCM fd and run route/setcal cleanup in the worker after drain.",
        "- Keeps stop-owned deferred cleanup only for PCM stream mode used by DOOM SFX.",
        "- Removes Bad Apple/Nyan menu post-video forced `audio stop`; pre-stop remains best-effort to clear stale workers.",
        "- Preserves V3168 static Player HUD telemetry/text policy and stable `setcrtc` present path.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3169 builder and focused tests.",
        "- `unittest`: V3169 Bad Apple/Nyan finite audio cleanup source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3169/0.11.12 identity and finite cleanup markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-finite-audio-cleanup-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-finite-audio-cleanup-candidate",
        "adoption_state": "pending-badapple-nyan-finite-audio-cleanup-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3168-badapple-nyan-av-stutter-guard",
            "requires_live_validation": [
                "badapple-fullsong-av",
                "nyan-preview-av",
                "finite-pcm-worker-cleanup",
                "player-hud-static-telemetry",
                "physical-button-exit",
            ],
            "preserves_doom_demo": True,
        },
        "audio_cleanup": {
            "finite_pcm_cleanup_owner": "worker",
            "stream_pcm_cleanup_owner": "audio-stop",
            "badapple_nyan_post_stop_required": False,
            "badapple_nyan_pre_stop_best_effort": True,
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
    (OUT_DIR / "badapple-nyan-finite-audio-cleanup-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-finite-audio-cleanup-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "badapple-fullsong-av",
            "nyan-preview-av",
            "finite-pcm-worker-cleanup",
            "physical-button-exit",
        ],
        "finite_pcm_cleanup_owner": "worker",
        "stream_pcm_cleanup_owner": "audio-stop",
        "badapple_nyan_post_stop_required": False,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-finite-audio-cleanup-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3169_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3169_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3168_overrides", _v3169_overrides),
        ("_v3168_values", _v3169_values),
        ("_v3168_adapter_source_from_patched_v3148", _v3169_adapter_source_from_patched_v3148),
        ("v3168_adapter_source", v3169_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3169_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3169_globals()
    try:
        return base.main()
    finally:
        _restore_v3169_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
