#!/usr/bin/env python3
"""Build V3170 Bad Apple/Nyan A/V tail and readahead candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3169_badapple_nyan_finite_audio_cleanup as base

REPO_ROOT = repo_root()

CYCLE = "V3170"
INIT_VERSION = "0.11.13"
INIT_BUILD = "v3170-badapple-nyan-av-tail-readahead"
BUILD_TAG = INIT_BUILD
DECISION = "v3170-badapple-nyan-av-tail-readahead-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3170_BADAPPLE_NYAN_AV_TAIL_READAHEAD_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3170_badapple_nyan_av_tail_readahead.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3170_badapple_nyan_av_tail_readahead"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3170_badapple_nyan_av_tail_readahead.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v547_badapple_nyan_av_tail_readahead"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3170"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3170.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3170.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3170"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3170-badapple-nyan-av-tail-readahead"

FRAME_PATH = "/tmp/a90-doomgeneric-v3170-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3170-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3170-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3170-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3170-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3170-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3170-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-badapple-nyan-av-tail-readahead"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-badapple-nyan-av-tail-readahead"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3169", "v3170")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3169", "v3170")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3169", "v3170")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3169", "v3170")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3169", "v3170")
SCALE_MARKER = base.SCALE_MARKER.replace("v3169", "v3170")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3169", "v3170")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3169", "v3170")
SFX_STREAM_MARKER = "a90.doomgeneric.v3170.audio=real-sfx-pcm-stream-badapple-nyan-av-tail-readahead"
SOUND_MODE = "native-doom-sfx-badapple-nyan-av-tail-readahead-v3170"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3170.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = base.VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS
VIDEO_PLAYER_HUD_LIVE_TELEMETRY = base.VIDEO_PLAYER_HUD_LIVE_TELEMETRY
VIDEO_PLAYER_HUD_DYNAMIC_TEXT = base.VIDEO_PLAYER_HUD_DYNAMIC_TEXT

BASE_OVERRIDES = base._v3169_overrides
BASE_VALUES = base._v3169_values
V3169_ADAPTER_SOURCE_TEXT = base.v3169_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3170_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("badapple-nyan-finite-audio-cleanup", "badapple-nyan-av-tail-readahead")
        .replace("v3169", "v3170")
        .replace("V3169", "V3170")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3170_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"badapple-nyan-finite-audio-cleanup": b"badapple-nyan-av-tail-readahead",
        b"a90-doomgeneric-v3169": b"a90-doomgeneric-v3170",
        b"a90.doomgeneric.v3169": b"a90.doomgeneric.v3170",
        b"v3169": b"v3170",
        b"V3169": b"V3170",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_RETIRED_REQUIRED_MARKERS = (
    b"video.status.menu_av_late_drop=disabled-setcrtc-default",
    b"menu.demo.badapple.video_late_drop=disabled-setcrtc-default",
    b"menu.demo.nyan.video_late_drop=disabled-setcrtc-default",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
    if not any(marker in item for marker in _RETIRED_REQUIRED_MARKERS)
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.13",
    b"v3170-badapple-nyan-av-tail-readahead",
    b"audio.play.cap.nyan_preview_ms=%d",
    b"audio.play.cap.nyan_preview_sha256=%s",
    b"nyan-preview-pcm-tail-pad",
    b"menu.demo.badapple.audio_duration_ms=232800",
    b"menu.demo.badapple.audio_tail_pad_ms=710",
    b"menu.demo.nyan.audio_duration_ms=11000",
    b"menu.demo.nyan.audio_tail_pad_ms=1000",
    b"video.status.stream_readahead=sequential-window",
    b"video.stream.readahead.policy=sequential-window",
    b"video.stream.audio_sync.drop_policy=%s",
    b"audio-clock-late-frame-skip",
    b"video.stream.audio_sync.drop_present_modes=%s",
    b"video.status.menu_av_late_drop=audio-clock-setcrtc-pageflip",
    b"menu.demo.badapple.video_late_drop=audio-sync-setcrtc-skip",
    b"menu.demo.nyan.video_late_drop=audio-sync-setcrtc-skip",
)


def _v3170_overrides() -> dict[str, Any]:
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


def _v3170_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3170_overrides())
    return values


def _v3170_adapter_source_from_patched_v3148() -> str:
    return (
        V3169_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-finite-audio-cleanup",
                 "real-sfx-pcm-stream-badapple-nyan-av-tail-readahead")
        .replace("v3169", "v3170")
        .replace("V3169", "V3170")
    )


def v3170_adapter_source() -> str:
    return _v3170_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3170 Bad Apple/Nyan A/V Tail Readahead Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: Bad Apple/Nyan A/V stutter and sound tail regression.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds Nyan preview PCM duration cap for a bounded silent tail after the 10s asset.",
        "- Extends menu finite PCM durations so route/setcal cleanup does not overlap the final video frames.",
        "- Enables audio-clock late-frame skip for both `setcrtc` and `pageflip` A/V paths.",
        "- Adds sequential/windowed `posix_fadvise` readahead hints for SD-backed video streams.",
        "- Preserves V3169 finite PCM worker-owned cleanup and DOOM FIFO stream cleanup split.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3170 builder and focused tests.",
        "- `unittest`: V3170 Bad Apple/Nyan A/V tail/readahead source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3170/0.11.13 identity and A/V tail/readahead markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `badapple-nyan-av-tail-readahead-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-av-tail-readahead-candidate",
        "adoption_state": "pending-badapple-nyan-av-tail-readahead-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3169-badapple-nyan-finite-audio-cleanup",
            "requires_live_validation": [
                "badapple-fullsong-av",
                "nyan-preview-av",
                "setcrtc-late-frame-skip",
                "stream-readahead",
                "finite-pcm-tail-cleanup",
            ],
            "preserves_doom_demo": True,
        },
        "badapple_nyan_av": {
            "badapple_audio_duration_ms": 232800,
            "badapple_audio_tail_pad_ms": 710,
            "nyan_audio_duration_ms": 11000,
            "nyan_audio_tail_pad_ms": 1000,
            "late_drop_present_modes": ["setcrtc", "pageflip"],
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
    (OUT_DIR / "badapple-nyan-av-tail-readahead-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "badapple-nyan-av-tail-readahead-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "badapple-fullsong-av",
            "nyan-preview-av",
            "setcrtc-late-frame-skip",
            "stream-readahead",
            "finite-pcm-tail-cleanup",
        ],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-tail-readahead-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3170_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3170_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3169_overrides", _v3170_overrides),
        ("_v3169_values", _v3170_values),
        ("_v3169_adapter_source_from_patched_v3148", _v3170_adapter_source_from_patched_v3148),
        ("v3169_adapter_source", v3170_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3170_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3170_globals()
    try:
        return base.main()
    finally:
        _restore_v3170_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
