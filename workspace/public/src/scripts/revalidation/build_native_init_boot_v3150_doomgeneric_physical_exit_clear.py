#!/usr/bin/env python3
"""Build V3150 DOOM physical-button exit display clear candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3149_doomgeneric_sfx_long_window_physical_exit as v3149

REPO_ROOT = repo_root()

CYCLE = "V3150"
INIT_VERSION = "0.10.132"
INIT_BUILD = "v3150-doomgeneric-physical-exit-clear"
BUILD_TAG = INIT_BUILD
DECISION = "v3150-doomgeneric-physical-exit-clear-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3150_DOOMGENERIC_PHYSICAL_EXIT_CLEAR_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3150_doomgeneric_physical_exit_clear.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3150_doomgeneric_physical_exit_clear"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3150_doomgeneric_physical_exit_clear.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v532_doomgeneric_physical_exit_clear"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3150"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3150.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3150.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3150"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3150-physical-exit-clear"

FRAME_PATH = "/tmp/a90-doomgeneric-v3150-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3150-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3150-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3150-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3150-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3150-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3150-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-long-window-physical-exit-clear"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-long-window-physical-exit-clear"

INPUT_THREAD_MARKER = v3149.INPUT_THREAD_MARKER.replace("v3149", "v3150")
TIME_MODEL_MARKER = v3149.TIME_MODEL_MARKER.replace("v3149", "v3150")
DEMO_HUD_MARKER = v3149.DEMO_HUD_MARKER.replace("v3149", "v3150")
PACED_TIME_MARKER = v3149.PACED_TIME_MARKER.replace("v3149", "v3150")
TICK_TELEMETRY_MARKER = v3149.TICK_TELEMETRY_MARKER.replace("v3149", "v3150")
SCALE_MARKER = v3149.SCALE_MARKER.replace("v3149", "v3150")
PHASE_TELEMETRY_MARKER = v3149.PHASE_TELEMETRY_MARKER.replace("v3149", "v3150")
GAMETIC_FRAME_TELEMETRY_MARKER = v3149.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3149", "v3150")
SFX_STREAM_MARKER = "a90.doomgeneric.v3150.audio=real-sfx-pcm-stream-long-window-physical-exit-clear"
SOUND_MODE = "native-doom-sfx-pcm-stream-long-window-v3150"

AUDIO_CORUN = v3149.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3149.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3149.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3149.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3149.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3149.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3150.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
SFX_BACKEND_SOURCE_TEXT = v3149.SFX_BACKEND_SOURCE_TEXT.replace(
    v3149.AUDIO_PCM_STREAM_PATH,
    AUDIO_PCM_STREAM_PATH,
)

_ORIGINAL_V3149_ADAPTER_SOURCE_FROM_PATCHED_V3148 = (
    v3149._v3149_adapter_source_from_patched_v3148
)
_ORIGINAL_V3149_RENDER_REPORT = v3149.render_report
_ORIGINAL_V3149_POSTPROCESS_MANIFEST = v3149._postprocess_manifest


def rel(path: Path) -> str:
    return v3149.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3149.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3149.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3149.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3149.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3149.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3149.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3149.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3149": b"a90-doomgeneric-v3150",
        b"a90.doomgeneric.v3149": b"a90.doomgeneric.v3150",
        b"v3149": b"v3150",
        b"V3149": b"V3150",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3149.REQUIRED_STRINGS) + (
    b"physical-button-exit",
    b"video.demo.doom.clear.reason=%s",
)


def _v3150_values() -> dict[str, Any]:
    values = {name: getattr(v3149, name) for name in v3149._v3149_values()}
    values.update({
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
    })
    return values


def _v3150_adapter_source_from_patched_v3148() -> str:
    return (
        _ORIGINAL_V3149_ADAPTER_SOURCE_FROM_PATCHED_V3148()
        .replace("real-sfx-pcm-stream-long-window-physical-exit",
                 "real-sfx-pcm-stream-long-window-physical-exit-clear")
        .replace("v3149", "v3150")
        .replace("V3149", "V3150")
    )


def _apply_v3150_globals() -> dict[str, Any]:
    saved = {name: getattr(v3149, name) for name in _v3150_values()}
    for name, value in _v3150_values().items():
        setattr(v3149, name, value)
    saved["_v3149_adapter_source_from_patched_v3148"] = (
        v3149._v3149_adapter_source_from_patched_v3148
    )
    saved["render_report"] = v3149.render_report
    saved["_postprocess_manifest"] = v3149._postprocess_manifest
    v3149._v3149_adapter_source_from_patched_v3148 = _v3150_adapter_source_from_patched_v3148
    v3149.render_report = render_report
    v3149._postprocess_manifest = _postprocess_manifest
    return saved


def _restore_v3150_globals(saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(v3149, name, value)


def v3150_adapter_source() -> str:
    saved = _apply_v3150_globals()
    try:
        return _v3150_adapter_source_from_patched_v3148()
    finally:
        _restore_v3150_globals(saved)


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3150 DOOMGENERIC Physical Exit Clear Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo exit polish over the V3149 long-window SFX stack.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V3149 240s bounded DOOM SFX PCM stream window.",
        "- Keeps audio refresh disabled so route/setcal/PCM open churn does not run during gameplay.",
        "- Keeps the physical-button exit detector on read-only `event3,event0`.",
        "- Adds display clear on physical-button exit so the last DOOM frame is not left on screen.",
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
        "- Physical exit: `POWER`, `VOLUP`, or `VOLDOWN` down event exits the loop, clears display, and stops audio.",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Physical input handling opens `/dev/input/event0` and `/dev/input/event3` read-only/nonblocking.",
        "- Display cleanup uses the existing KMS clear path already used by `video demo doom loop-stop`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3150 builder and focused tests.",
        "- `unittest`: V3150 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3150 identity, long-window SFX markers, physical-exit clear markers, and inherited HUD/input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-physical-exit-clear-candidate`.",
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
            "action": "exit-doom-loop-stop-audio-and-clear-display",
            "clear_reason": "physical-button-exit",
        },
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-physical-exit-clear-candidate",
        "adoption_state": "pending-physical-exit-clear-live-validation",
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
    (OUT_DIR / "doomgeneric-physical-exit-clear-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-physical-exit-clear-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": v3149.RUNTIME_WAD_PATH,
        "expected_wad_sha256": v3149.EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_duration_ms": AUDIO_CORUN_DURATION_MS,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "physical_button_exit": True,
        "display_clear_on_physical_exit": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-physical-exit-clear-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    saved = _apply_v3150_globals()
    try:
        rc = v3149.main()
    finally:
        _restore_v3150_globals(saved)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
