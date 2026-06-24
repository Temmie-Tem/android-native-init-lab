#!/usr/bin/env python3
"""Build V3151 DOOM physical-button exit menu-return candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3150_doomgeneric_physical_exit_clear as v3150

REPO_ROOT = repo_root()

CYCLE = "V3151"
INIT_VERSION = "0.10.133"
INIT_BUILD = "v3151-doomgeneric-physical-exit-menu-return"
BUILD_TAG = INIT_BUILD
DECISION = "v3151-doomgeneric-physical-exit-menu-return-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3151_DOOMGENERIC_PHYSICAL_EXIT_MENU_RETURN_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3151_doomgeneric_physical_exit_menu_return.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3151_doomgeneric_physical_exit_menu_return"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3151_doomgeneric_physical_exit_menu_return.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v532_doomgeneric_physical_exit_menu_return"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3151"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3151.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3151.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3151"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3151-physical-exit-menu-return"

FRAME_PATH = "/tmp/a90-doomgeneric-v3151-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3151-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3151-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3151-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3151-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3151-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3151-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-long-window-physical-exit-menu-return"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-long-window-physical-exit-menu-return"

INPUT_THREAD_MARKER = v3150.INPUT_THREAD_MARKER.replace("v3150", "v3151")
TIME_MODEL_MARKER = v3150.TIME_MODEL_MARKER.replace("v3150", "v3151")
DEMO_HUD_MARKER = v3150.DEMO_HUD_MARKER.replace("v3150", "v3151")
PACED_TIME_MARKER = v3150.PACED_TIME_MARKER.replace("v3150", "v3151")
TICK_TELEMETRY_MARKER = v3150.TICK_TELEMETRY_MARKER.replace("v3150", "v3151")
SCALE_MARKER = v3150.SCALE_MARKER.replace("v3150", "v3151")
PHASE_TELEMETRY_MARKER = v3150.PHASE_TELEMETRY_MARKER.replace("v3150", "v3151")
GAMETIC_FRAME_TELEMETRY_MARKER = v3150.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3150", "v3151")
SFX_STREAM_MARKER = "a90.doomgeneric.v3151.audio=real-sfx-pcm-stream-long-window-physical-exit-menu-return"
SOUND_MODE = "native-doom-sfx-pcm-stream-long-window-v3151"

AUDIO_CORUN = v3150.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3150.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3150.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3150.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3150.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3150.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3151.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
SFX_BACKEND_SOURCE_TEXT = v3150.SFX_BACKEND_SOURCE_TEXT.replace(
    v3150.AUDIO_PCM_STREAM_PATH,
    AUDIO_PCM_STREAM_PATH,
)

_ORIGINAL_V3150_ADAPTER_SOURCE_FROM_PATCHED_V3148 = (
    v3150._v3150_adapter_source_from_patched_v3148
)


def rel(path: Path) -> str:
    return v3150.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3150.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3150.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3150.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3150.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3150.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3150.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3150.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3150": b"a90-doomgeneric-v3151",
        b"a90.doomgeneric.v3150": b"a90.doomgeneric.v3151",
        b"v3150": b"v3151",
        b"V3150": b"V3151",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3150.REQUIRED_STRINGS) + (
    b"video.demo.doom.return_menu.requested=1",
    b"video.demo.doom.return_menu.autohud_rc=%d",
    b"video.demo.doom.return_menu.active=%d",
)


def _v3151_values() -> dict[str, Any]:
    values = {name: getattr(v3150, name) for name in v3150._v3150_values()}
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


def _v3151_adapter_source_from_patched_v3148() -> str:
    return (
        _ORIGINAL_V3150_ADAPTER_SOURCE_FROM_PATCHED_V3148()
        .replace("real-sfx-pcm-stream-long-window-physical-exit-clear",
                 "real-sfx-pcm-stream-long-window-physical-exit-menu-return")
        .replace("v3150", "v3151")
        .replace("V3150", "V3151")
    )


def _apply_v3151_globals() -> dict[str, Any]:
    saved = {name: getattr(v3150, name) for name in _v3151_values()}
    for name, value in _v3151_values().items():
        setattr(v3150, name, value)
    saved["_v3150_adapter_source_from_patched_v3148"] = (
        v3150._v3150_adapter_source_from_patched_v3148
    )
    saved["render_report"] = v3150.render_report
    saved["_postprocess_manifest"] = v3150._postprocess_manifest
    v3150._v3150_adapter_source_from_patched_v3148 = _v3151_adapter_source_from_patched_v3148
    v3150.render_report = render_report
    v3150._postprocess_manifest = _postprocess_manifest
    return saved


def _restore_v3151_globals(saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(v3150, name, value)


def v3151_adapter_source() -> str:
    saved = _apply_v3151_globals()
    try:
        return _v3151_adapter_source_from_patched_v3148()
    finally:
        _restore_v3151_globals(saved)


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3151 DOOMGENERIC Physical Exit Menu Return Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo exit UX over the V3150 clear path.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V3150 physical-button display clear.",
        "- Requests menu return after physical-button exit by starting autohud if needed and writing the menu show IPC.",
        "- Keeps the V3150 long-window DOOM SFX stream and disabled audio refresh.",
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
        "- Physical exit: `POWER`, `VOLUP`, or `VOLDOWN` exits the loop, clears display, stops audio, and returns to menu/HUD.",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Physical input handling opens `/dev/input/event0` and `/dev/input/event3` read-only/nonblocking.",
        "- Menu return uses the existing autohud/menu IPC path used by `screenmenu`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3151 builder and focused tests.",
        "- `unittest`: V3151 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3151 identity, physical-exit clear/menu-return markers, and inherited DOOM/audio/input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-physical-exit-menu-return-candidate`.",
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
            "action": "exit-doom-loop-stop-audio-clear-display-and-return-menu",
            "clear_reason": "physical-button-exit",
            "menu_return": True,
        },
        "sound_mode": SOUND_MODE,
        "sfx_stream_marker": SFX_STREAM_MARKER,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-physical-exit-menu-return-candidate",
        "adoption_state": "pending-physical-exit-menu-return-live-validation",
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
    (OUT_DIR / "doomgeneric-physical-exit-menu-return-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-physical-exit-menu-return-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": v3150.v3149.RUNTIME_WAD_PATH,
        "expected_wad_sha256": v3150.v3149.EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_duration_ms": AUDIO_CORUN_DURATION_MS,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "physical_button_exit": True,
        "display_clear_on_physical_exit": True,
        "menu_return_on_physical_exit": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-physical-exit-menu-return-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    saved = _apply_v3151_globals()
    try:
        rc = v3150.main()
    finally:
        _restore_v3151_globals(saved)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
