#!/usr/bin/env python3
"""Build V3171 Bad Apple/Nyan setcrtc cadence candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3170_badapple_nyan_av_tail_readahead as base

REPO_ROOT = repo_root()

CYCLE = "V3171"
INIT_VERSION = "0.11.14"
INIT_BUILD = "v3171-badapple-nyan-setcrtc-cadence"
BUILD_TAG = INIT_BUILD
DECISION = "v3171-badapple-nyan-setcrtc-cadence-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3171_BADAPPLE_NYAN_SETCRTC_CADENCE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3171_badapple_nyan_setcrtc_cadence.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3171_badapple_nyan_setcrtc_cadence"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3171_badapple_nyan_setcrtc_cadence.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v548_badapple_nyan_setcrtc_cadence"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3171"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3171.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3171.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3171"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3171-badapple-nyan-setcrtc-cadence"

FRAME_PATH = "/tmp/a90-doomgeneric-v3171-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3171-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3171-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3171-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3171-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3171-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3171-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-setcrtc-cadence"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-setcrtc-cadence"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3170", "v3171")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3170", "v3171")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3170", "v3171")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3170", "v3171")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3170", "v3171")
SCALE_MARKER = base.SCALE_MARKER.replace("v3170", "v3171")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3170", "v3171")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3170", "v3171")
SFX_STREAM_MARKER = "a90.doomgeneric.v3171.audio=real-sfx-pcm-stream-badapple-nyan-setcrtc-cadence"
SOUND_MODE = "native-doom-sfx-badapple-nyan-setcrtc-cadence-v3171"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3171.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = base.VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS
VIDEO_PLAYER_HUD_LIVE_TELEMETRY = base.VIDEO_PLAYER_HUD_LIVE_TELEMETRY
VIDEO_PLAYER_HUD_DYNAMIC_TEXT = base.VIDEO_PLAYER_HUD_DYNAMIC_TEXT

BASE_OVERRIDES = base._v3170_overrides
BASE_VALUES = base._v3170_values
V3170_ADAPTER_SOURCE_TEXT = base.v3170_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3171_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-av-tail-readahead", "badapple-nyan-setcrtc-cadence")
        .replace("v3170", "v3171")
        .replace("V3170", "V3171")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3171_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-av-tail-readahead": b"badapple-nyan-setcrtc-cadence",
        b"a90-doomgeneric-v3170": b"a90-doomgeneric-v3171",
        b"a90.doomgeneric.v3170": b"a90.doomgeneric.v3171",
        b"v3170": b"v3171",
        b"V3170": b"V3171",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_RETIRED_REQUIRED_MARKERS = (
    b"video.status.menu_av_late_drop=audio-clock-setcrtc-pageflip",
    b"menu.demo.badapple.video_late_drop=audio-sync-setcrtc-skip",
    b"menu.demo.nyan.video_late_drop=audio-sync-setcrtc-skip",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
    if not any(marker in item for marker in _RETIRED_REQUIRED_MARKERS)
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.14",
    b"v3171-badapple-nyan-setcrtc-cadence",
    b"video.status.menu_av_late_drop=pageflip-only-setcrtc-cadence",
    b"menu.demo.badapple.video_late_drop=setcrtc-cadence-no-drop",
    b"menu.demo.nyan.video_late_drop=setcrtc-cadence-no-drop",
)


def _v3171_overrides() -> dict[str, Any]:
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


def _v3171_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3171_overrides())
    return values


def _v3171_adapter_source_from_patched_v3148() -> str:
    return (
        V3170_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-av-tail-readahead",
                 "real-sfx-pcm-stream-badapple-nyan-setcrtc-cadence")
        .replace("v3170", "v3171")
        .replace("V3170", "V3171")
    )


def v3171_adapter_source() -> str:
    return _v3171_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3171 Bad Apple/Nyan Setcrtc Cadence Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan visible stutter regression.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps menu playback on `setcrtc`, but disables audio-clock late-frame skipping on that path.",
        "- Leaves late-frame skipping available only for explicit `pageflip` diagnostics.",
        "- Preserves V3170 Nyan audio tail pad, finite PCM cleanup, and stream readahead.",
        "- Preserves DOOM input/audio changes from the current promotion line.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3171 builder and focused tests.",
        "- `unittest`: V3171 Bad Apple/Nyan setcrtc cadence source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3171/0.11.14 identity and setcrtc cadence markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-setcrtc-cadence-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-setcrtc-cadence-candidate",
        "adoption_state": "pending-badapple-nyan-setcrtc-cadence-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3170-badapple-nyan-av-tail-readahead",
            "requires_live_validation": [
                "badapple-fullsong-av",
                "nyan-preview-av",
                "setcrtc-stable-cadence",
                "pageflip-late-drop-diagnostic",
                "finite-pcm-tail-cleanup",
            ],
            "preserves_doom_demo": True,
        },
        "badapple_nyan_av": {
            "badapple_audio_duration_ms": 232800,
            "badapple_audio_tail_pad_ms": 710,
            "nyan_audio_duration_ms": 11000,
            "nyan_audio_tail_pad_ms": 1000,
            "setcrtc_drop_policy": "disabled-stable-cadence",
            "late_drop_present_modes": ["pageflip"],
            "stream_readahead": "sequential-window",
            "stream_readahead_bytes": 8 * 1024 * 1024,
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
    (OUT_DIR / "badapple-nyan-setcrtc-cadence-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-setcrtc-cadence-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "badapple-fullsong-av",
            "nyan-preview-av",
            "setcrtc-stable-cadence",
            "pageflip-late-drop-diagnostic",
            "finite-pcm-tail-cleanup",
        ],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-setcrtc-cadence-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3171_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3171_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3170_overrides", _v3171_overrides),
        ("_v3170_values", _v3171_values),
        ("_v3170_adapter_source_from_patched_v3148", _v3171_adapter_source_from_patched_v3148),
        ("v3170_adapter_source", v3171_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3171_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3171_globals()
    try:
        return base.main()
    finally:
        _restore_v3171_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
