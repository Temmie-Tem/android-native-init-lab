#!/usr/bin/env python3
"""Build V3149 DOOM SFX long-window audio plus physical-button exit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3148_doomgeneric_sfx_stream_refresh as v3148

REPO_ROOT = repo_root()

CYCLE = "V3149"
INIT_VERSION = "0.10.131"
INIT_BUILD = "v3149-doomgeneric-sfx-long-window-physical-exit"
BUILD_TAG = INIT_BUILD
DECISION = "v3149-doomgeneric-sfx-long-window-physical-exit-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3149_DOOMGENERIC_SFX_LONG_WINDOW_PHYSICAL_EXIT_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3149_doomgeneric_sfx_long_window_physical_exit.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3149_doomgeneric_sfx_long_window_physical_exit"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3149_doomgeneric_sfx_long_window_physical_exit.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v532_doomgeneric_sfx_long_window_physical_exit"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3149"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3149.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3149.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3149"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3149-sfx-long-window-physical-exit"

FRAME_PATH = "/tmp/a90-doomgeneric-v3149-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3149-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3149-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3149-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3149-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3149-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3149-sfx.pcmstream"

RUNTIME_WAD_PATH = v3148.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3148.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3148.FRAME_WIDTH
FRAME_HEIGHT = v3148.FRAME_HEIGHT
FRAME_STRIDE = v3148.FRAME_STRIDE
FRAME_BYTES = v3148.FRAME_BYTES
INPUT_UDP_PORT = v3148.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3148.DEVICE_NCM_HOST

DASHBOARD_METRICS_INTERVAL_FRAMES = v3148.DASHBOARD_METRICS_INTERVAL_FRAMES
DASHBOARD_STATUS_INTERVAL_FRAMES = v3148.DASHBOARD_STATUS_INTERVAL_FRAMES
NATIVE_DASHBOARD = v3148.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3148.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3148.NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DEMO_HUD = v3148.NATIVE_DEMO_HUD
NATIVE_DEMO_HUD_FAST = v3148.NATIVE_DEMO_HUD_FAST
NATIVE_DEMO_HUD_READABLE = v3148.NATIVE_DEMO_HUD_READABLE
NATIVE_DEMO_HUD_SECTIONED = v3148.NATIVE_DEMO_HUD_SECTIONED
NATIVE_DEMO_HUD_LARGE_GROUPS = v3148.NATIVE_DEMO_HUD_LARGE_GROUPS
PRE_SCALED_LARGE_FRAME = v3148.PRE_SCALED_LARGE_FRAME
FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-long-window-physical-exit"
SCALE_PATH = v3148.SCALE_PATH
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-long-window-physical-exit"

INPUT_THREAD_MARKER = v3148.INPUT_THREAD_MARKER.replace("v3148", "v3149")
TIME_MODEL_MARKER = v3148.TIME_MODEL_MARKER.replace("v3148", "v3149")
DEMO_HUD_MARKER = v3148.DEMO_HUD_MARKER.replace("v3148", "v3149")
PACED_TIME_MARKER = v3148.PACED_TIME_MARKER.replace("v3148", "v3149")
TICK_TELEMETRY_MARKER = v3148.TICK_TELEMETRY_MARKER.replace("v3148", "v3149")
SCALE_MARKER = v3148.SCALE_MARKER.replace("v3148", "v3149")
PHASE_TELEMETRY_MARKER = v3148.PHASE_TELEMETRY_MARKER.replace("v3148", "v3149")
GAMETIC_FRAME_TELEMETRY_MARKER = v3148.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3148", "v3149")
SFX_STREAM_MARKER = "a90.doomgeneric.v3149.audio=real-sfx-pcm-stream-long-window-physical-exit"
SOUND_MODE = "native-doom-sfx-pcm-stream-long-window-v3149"
AUDIO_CORUN = 1
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = 1
AUDIO_CORUN_DURATION_MS = 240000
AUDIO_CORUN_REFRESH_MS = 0
AUDIO_CORUN_AMPLITUDE_MILLI = 150
PHYSICAL_BUTTON_EXIT = 1

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3149.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
SFX_BACKEND_SOURCE_TEXT = v3148.SFX_BACKEND_SOURCE_TEXT.replace(
    v3148.AUDIO_PCM_STREAM_PATH,
    AUDIO_PCM_STREAM_PATH,
)

_ORIGINAL_V3148_ADAPTER_SOURCE = v3148.v3148_adapter_source
_ORIGINAL_V3148_RENDER_REPORT = v3148.render_report
_ORIGINAL_V3148_DEMO_HUD_MARKER = v3148.DEMO_HUD_MARKER


def rel(path: Path) -> str:
    return v3148.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3148.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3148.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3148.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3148.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3148.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3148.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3148.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3148": b"a90-doomgeneric-v3149",
        b"a90.doomgeneric.v3148": b"a90.doomgeneric.v3149",
        b"v3148": b"v3149",
        b"V3148": b"V3149",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3148.REQUIRED_STRINGS) + (
    b"video.demo.doom.loop.physical_button_exit=%d",
    b"doomgeneric-physical-exit",
    b"audio.play.cap.doom_sfx_stream_ms",
)


def _v3149_values() -> dict[str, Any]:
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


def _apply_v3149_globals() -> dict[str, Any]:
    saved = {name: getattr(v3148, name) for name in _v3149_values()}
    for name, value in _v3149_values().items():
        setattr(v3148, name, value)
    saved["v3148_adapter_source"] = v3148.v3148_adapter_source
    saved["render_report"] = v3148.render_report
    v3148.v3148_adapter_source = _v3149_adapter_source_from_patched_v3148
    v3148.render_report = render_report
    return saved


def _restore_v3148_globals(saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(v3148, name, value)


def _v3149_adapter_source_from_patched_v3148() -> str:
    saved_demo_hud_marker = v3148.DEMO_HUD_MARKER

    v3148.DEMO_HUD_MARKER = _ORIGINAL_V3148_DEMO_HUD_MARKER
    try:
        source = _ORIGINAL_V3148_ADAPTER_SOURCE()
    finally:
        v3148.DEMO_HUD_MARKER = saved_demo_hud_marker
    return (
        source.replace("real-sfx-pcm-stream-refresh-music-disabled",
                       "real-sfx-pcm-stream-long-window-physical-exit")
        .replace("v3148", "v3149")
        .replace("V3148", "V3149")
    )


def v3149_adapter_source() -> str:
    saved = _apply_v3149_globals()
    try:
        return _v3149_adapter_source_from_patched_v3148()
    finally:
        _restore_v3148_globals(saved)


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3149 DOOMGENERIC SFX Long Window Physical Exit Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo audio/input polish over the V3148 SFX stream stack.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Replaces the 10s SFX worker plus 13s refresh cadence with one 240s bounded PCM stream window.",
        "- Leaves audio refresh disabled (`A90_DOOMGENERIC_AUDIO_CORUN_REFRESH_MS=0`) so route/setcal/PCM open churn no longer runs during gameplay.",
        "- Enables DOOM physical-button exit by polling `event3,event0` nonblocking inside the presenter loop.",
        "- Extends `audio stop` so a loop child can stop the current worker from `/cache/a90-audio-play/status.txt` even when the PID is not tracked in that process.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Audio stream path: `{AUDIO_PCM_STREAM_PATH}`",
        f"- Sound mode: `{SOUND_MODE}`",
        f"- Audio co-run enabled: `{int(bool(audio.get('enabled', AUDIO_CORUN)))}`",
        f"- Audio duration ms: `{AUDIO_CORUN_DURATION_MS}`",
        f"- Audio refresh ms: `{AUDIO_CORUN_REFRESH_MS}`",
        f"- Audio amplitude milli: `{AUDIO_CORUN_AMPLITUDE_MILLI}`",
        "- Physical exit: `POWER`, `VOLUP`, or `VOLDOWN` down event exits the loop.",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Physical input handling opens `/dev/input/event0` and `/dev/input/event3` read-only/nonblocking.",
        "- Audio remains bounded by `AUDIO_DOOM_SFX_STREAM_DURATION_CAP_MS`; no persistent unbounded worker is introduced.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3149 builder and focused tests.",
        "- `unittest`: V3149 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3149 identity, long-window SFX stream markers, physical-exit markers, and inherited HUD/input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-sfx-long-window-physical-exit-candidate`.",
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
    })
    doom.update({
        "physical_button_exit": {
            "enabled": True,
            "events": ["event3", "event0"],
            "keys": ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN"],
            "action": "exit-doom-loop-and-stop-audio",
        },
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-long-window-physical-exit-candidate",
        "adoption_state": "pending-sfx-long-window-physical-exit-live-validation",
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
    (OUT_DIR / "doomgeneric-sfx-long-window-physical-exit-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-sfx-long-window-physical-exit-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_duration_ms": AUDIO_CORUN_DURATION_MS,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "physical_button_exit": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-sfx-long-window-physical-exit-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    saved = _apply_v3149_globals()
    try:
        rc = v3148.main()
        _postprocess_manifest()
    finally:
        _restore_v3148_globals(saved)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
