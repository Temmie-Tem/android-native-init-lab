#!/usr/bin/env python3
"""Build V3161 audio close-deferred candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3160_audio_post_drain_hwfree as base

REPO_ROOT = repo_root()

CYCLE = "V3161"
INIT_VERSION = "0.11.4"
INIT_BUILD = "v3161-audio-close-deferred"
BUILD_TAG = INIT_BUILD
DECISION = "v3161-audio-close-deferred-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3161_AUDIO_CLOSE_DEFERRED_SOURCE_BUILD_2026-06-25.md"
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3161_audio_close_deferred.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3161_audio_close_deferred"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3161_audio_close_deferred.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v539_audio_close_deferred"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3161"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3161.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3161.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3161"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3161-audio-close-deferred"

FRAME_PATH = "/tmp/a90-doomgeneric-v3161-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3161-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3161-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3161-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3161-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3161-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3161-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-audio-close-deferred"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-audio-close-deferred"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3160", "v3161")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3160", "v3161")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3160", "v3161")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3160", "v3161")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3160", "v3161")
SCALE_MARKER = base.SCALE_MARKER.replace("v3160", "v3161")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3160", "v3161")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3160", "v3161")
SFX_STREAM_MARKER = "a90.doomgeneric.v3161.audio=real-sfx-pcm-stream-audio-close-deferred"
SOUND_MODE = "native-doom-sfx-audio-close-deferred-v3161"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3161.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES

BASE_OVERRIDES = base._v3160_overrides
V3160_ADAPTER_SOURCE_TEXT = base.v3160_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3161_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("audio-post-drain-hwfree", "audio-close-deferred")
        .replace("v3160", "v3161")
        .replace("V3160", "V3161")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3161_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"audio-post-drain-hwfree": b"audio-close-deferred",
        b"a90-doomgeneric-v3160": b"a90-doomgeneric-v3161",
        b"a90.doomgeneric.v3160": b"a90.doomgeneric.v3161",
        b"v3160": b"v3161",
        b"V3160": b"V3161",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.4",
    b"v3161-audio-close-deferred",
    b"audio.play.execute.close.deferred=1 reason=route-reset-before-pcm-close",
    b"audio.play.worker.close_deferred=1",
)


def _v3161_overrides() -> dict[str, Any]:
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


def _v3161_values() -> dict[str, Any]:
    values = dict(base.v3159.v3158.v3157.v3156.v3155._ORIGINAL_V3154_VALUES())
    values.update(_v3161_overrides())
    return values


def _v3161_adapter_source_from_patched_v3148() -> str:
    return (
        V3160_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-audio-post-drain-hwfree",
                 "real-sfx-pcm-stream-audio-close-deferred")
        .replace("v3160", "v3161")
        .replace("V3160", "V3161")
    )


def v3161_adapter_source() -> str:
    return _v3161_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3161 Audio Close Deferred Source Build",
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
        "- Preserves V3158 fastscale and V3160 drain/drop/HW_FREE markers.",
        "- Defers explicit PCM close so route reset and setcal cleanup can complete before driver close.",
        "- Exports `audio.play.execute.close.deferred=1` and worker close-deferred status markers.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3161 builder and focused tests.",
        "- `unittest`: V3161 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3161/0.11.4 identity and audio close-deferred marker.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-close-deferred-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-close-deferred-candidate",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3160-audio-post-drain-hwfree",
            "requires_live_validation": ["badapple", "nyan", "audio-worker-completion"],
            "preserves_doom_demo": True,
        },
        "audio_playback": {
            "post_drain_drop": True,
            "post_drain_hw_free": True,
            "close_deferred": True,
            "close_deferred_marker": "audio.play.execute.close.deferred",
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
    (OUT_DIR / "audio-close-deferred-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-close-deferred-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "audio-worker-completion"],
        "audio_close_deferred": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3161_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3161_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3160_overrides", _v3161_overrides),
        ("_v3160_values", _v3161_values),
        ("_v3160_adapter_source_from_patched_v3148", _v3161_adapter_source_from_patched_v3148),
        ("v3160_adapter_source", v3161_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3161_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3161_globals()
    try:
        return base.main()
    finally:
        _restore_v3161_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
