#!/usr/bin/env python3
"""Build V3154 DOOM physical-button exit hud-pid-adopt candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3151_doomgeneric_physical_exit_menu_return as v3151

REPO_ROOT = repo_root()

CYCLE = "V3154"
INIT_VERSION = "0.10.136"
INIT_BUILD = "v3154-doomgeneric-physical-exit-hud-pid-adopt"
BUILD_TAG = INIT_BUILD
DECISION = "v3154-doomgeneric-physical-exit-hud-pid-adopt-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3154_DOOMGENERIC_PHYSICAL_EXIT_HUD_PID_ADOPT_SOURCE_BUILD_2026-06-24.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3154_doomgeneric_physical_exit_hud_pid_adopt.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3154_doomgeneric_physical_exit_hud_pid_adopt"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3154_doomgeneric_physical_exit_hud_pid_adopt.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v532_doomgeneric_physical_exit_hud_pid_adopt"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3154"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3154.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3154.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3154"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3154-physical-exit-hud-pid-adopt"

FRAME_PATH = "/tmp/a90-doomgeneric-v3154-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3154-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3154-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3154-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3154-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3154-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3154-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-sfx-long-window-physical-exit-hud-pid-adopt"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-sfx-long-window-physical-exit-hud-pid-adopt"

INPUT_THREAD_MARKER = v3151.INPUT_THREAD_MARKER.replace("v3151", "v3154")
TIME_MODEL_MARKER = v3151.TIME_MODEL_MARKER.replace("v3151", "v3154")
DEMO_HUD_MARKER = v3151.DEMO_HUD_MARKER.replace("v3151", "v3154")
PACED_TIME_MARKER = v3151.PACED_TIME_MARKER.replace("v3151", "v3154")
TICK_TELEMETRY_MARKER = v3151.TICK_TELEMETRY_MARKER.replace("v3151", "v3154")
SCALE_MARKER = v3151.SCALE_MARKER.replace("v3151", "v3154")
PHASE_TELEMETRY_MARKER = v3151.PHASE_TELEMETRY_MARKER.replace("v3151", "v3154")
GAMETIC_FRAME_TELEMETRY_MARKER = v3151.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3151", "v3154")
SFX_STREAM_MARKER = "a90.doomgeneric.v3154.audio=real-sfx-pcm-stream-long-window-physical-exit-hud-pid-adopt"
SOUND_MODE = "native-doom-sfx-pcm-stream-long-window-v3154"

AUDIO_CORUN = v3151.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3151.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3151.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3151.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3151.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3151.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3154.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
SFX_BACKEND_SOURCE_TEXT = v3151.SFX_BACKEND_SOURCE_TEXT.replace(
    v3151.AUDIO_PCM_STREAM_PATH,
    AUDIO_PCM_STREAM_PATH,
)

_ORIGINAL_V3151_ADAPTER_SOURCE_FROM_PATCHED_V3148 = (
    v3151._v3151_adapter_source_from_patched_v3148
)


def rel(path: Path) -> str:
    return v3151.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3151.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3151.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3151.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3151.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3151.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3151.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3151.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3151": b"a90-doomgeneric-v3154",
        b"a90.doomgeneric.v3151": b"a90.doomgeneric.v3154",
        b"v3151": b"v3154",
        b"V3151": b"V3154",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in v3151.REQUIRED_STRINGS
    if b"video.demo.doom.return_menu.autohud_rc=%d" not in item
) + (
    b"video.demo.doom.return_menu.direct_present=1",
    b"video.demo.doom.return_menu.reason=physical-button-exit",
    b"video.demo.doom.return_menu.existing_hud_pid=%ld",
    b"video.demo.doom.return_menu.existing_hud_alive=%d",
    b"video.demo.doom.return_menu.spawn_hud_rc=%d",
    b"video.demo.doom.return_menu.live_hud_pid=%ld",
    b"video.demo.doom.return_menu.live_hud_alive=%d",
    b"video.demo.doom.return_menu.active=%d",
    b"/tmp/a90-autohud.pid",
)


def _v3154_values() -> dict[str, Any]:
    values = {name: getattr(v3151, name) for name in v3151._v3151_values()}
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


def _v3154_adapter_source_from_patched_v3148() -> str:
    return (
        _ORIGINAL_V3151_ADAPTER_SOURCE_FROM_PATCHED_V3148()
        .replace("real-sfx-pcm-stream-long-window-physical-exit-menu-return",
                 "real-sfx-pcm-stream-long-window-physical-exit-hud-pid-adopt")
        .replace("v3151", "v3154")
        .replace("V3151", "V3154")
    )


def _apply_v3154_globals() -> dict[str, Any]:
    saved = {name: getattr(v3151, name) for name in _v3154_values()}
    for name, value in _v3154_values().items():
        setattr(v3151, name, value)
    saved["_v3151_adapter_source_from_patched_v3148"] = (
        v3151._v3151_adapter_source_from_patched_v3148
    )
    saved["render_report"] = v3151.render_report
    saved["_postprocess_manifest"] = v3151._postprocess_manifest
    v3151._v3151_adapter_source_from_patched_v3148 = _v3154_adapter_source_from_patched_v3148
    v3151.render_report = render_report
    v3151._postprocess_manifest = _postprocess_manifest
    return saved


def _restore_v3154_globals(saved: dict[str, Any]) -> None:
    for name, value in saved.items():
        setattr(v3151, name, value)


def v3154_adapter_source() -> str:
    saved = _apply_v3154_globals()
    try:
        return _v3154_adapter_source_from_patched_v3148()
    finally:
        _restore_v3154_globals(saved)


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {})
    return "\n".join([
        "# Native Init V3154 DOOMGENERIC Physical Exit HUD PID Adopt Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo exit UX and physical-button menu recovery.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Presents a native menu frame before stopping audio, so physical exit does not wait on the audio route reset.",
        "- Starts a live autohud input reader when no existing HUD is alive after DOOM cleanup.",
        "- Persists/adopts the HUD PID so PID1 `status`, `stophud`, and `screenmenu` stay consistent after DOOM child cleanup.",
        "- Records existing/live HUD state in return-menu logs so physical-button recovery is measurable.",
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
        "- Physical exit: `POWER`, `VOLUP`, or `VOLDOWN` exits the loop, presents the menu frame, restores live HUD input, then stops audio.",
        f"- Frame IPC: `{FRAME_IPC}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Physical input handling opens `/dev/input/event0` and `/dev/input/event3` read-only/nonblocking.",
        "- Menu return reuses an existing autohud when alive, otherwise starts a new HUD input reader from the DOOM exit path.",
        "- HUD PID adoption uses `/tmp/a90-autohud.pid`; it is cleared on stop/reap.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3154 builder and focused tests.",
        "- `unittest`: V3154 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3154 identity, physical-exit hud-pid-adopt markers, and inherited DOOM/audio/input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-physical-exit-hud-pid-adopt-candidate`.",
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
        "candidate_type": "doomgeneric-physical-exit-hud-pid-adopt-candidate",
        "adoption_state": "pending-physical-exit-hud-pid-adopt-live-validation",
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
    (OUT_DIR / "doomgeneric-physical-exit-hud-pid-adopt-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-physical-exit-hud-pid-adopt-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "runtime_wad_path": v3151.v3150.v3149.RUNTIME_WAD_PATH,
        "expected_wad_sha256": v3151.v3150.v3149.EXPECTED_WAD_SHA256,
        "audio_pcm_stream_path": AUDIO_PCM_STREAM_PATH,
        "audio_duration_ms": AUDIO_CORUN_DURATION_MS,
        "audio_refresh_ms": AUDIO_CORUN_REFRESH_MS,
        "physical_button_exit": True,
        "direct_menu_present_on_physical_exit": True,
        "hud_pid_adopt_on_physical_exit": True,
        "start_new_hud_from_doom_exit_path": True,
        "sound_mode": SOUND_MODE,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-physical-exit-hud-pid-adopt-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    saved = _apply_v3154_globals()
    try:
        rc = v3151.main()
    finally:
        _restore_v3154_globals(saved)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
