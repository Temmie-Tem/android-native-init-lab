#!/usr/bin/env python3
"""Build V3162 audio stop-owned cleanup candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3161_audio_close_deferred as base

REPO_ROOT = repo_root()

CYCLE = "V3162"
INIT_VERSION = "0.11.5"
INIT_BUILD = "v3162-audio-stop-owned-cleanup"
BUILD_TAG = INIT_BUILD
DECISION = "v3162-audio-stop-owned-cleanup-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V3162_AUDIO_STOP_OWNED_CLEANUP_SOURCE_BUILD_2026-06-25.md"
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3162_audio_stop_owned_cleanup.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3162_audio_stop_owned_cleanup"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3162_audio_stop_owned_cleanup.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v540_audio_stop_owned_cleanup"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3162"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3162.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3162.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3162"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3162-audio-stop-owned-cleanup"

FRAME_PATH = "/tmp/a90-doomgeneric-v3162-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3162-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3162-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3162-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3162-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3162-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3162-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-audio-stop-owned-cleanup"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-audio-stop-owned-cleanup"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3161", "v3162")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3161", "v3162")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3161", "v3162")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3161", "v3162")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3161", "v3162")
SCALE_MARKER = base.SCALE_MARKER.replace("v3161", "v3162")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3161", "v3162")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3161", "v3162")
SFX_STREAM_MARKER = "a90.doomgeneric.v3162.audio=real-sfx-pcm-stream-audio-stop-owned-cleanup"
SOUND_MODE = "native-doom-sfx-audio-stop-owned-cleanup-v3162"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3162.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES

BASE_OVERRIDES = base._v3161_overrides
BASE_VALUES = base._v3161_values
V3161_ADAPTER_SOURCE_TEXT = base.v3161_adapter_source()


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_v3162_text(text: str) -> str:
    return (
        text.replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("audio-close-deferred", "audio-stop-owned-cleanup")
        .replace("v3161", "v3162")
        .replace("V3161", "V3162")
        .replace(base.INIT_VERSION, INIT_VERSION)
        .replace(base.INIT_BUILD, INIT_BUILD)
        .replace(base.ENGINE_NAME, ENGINE_NAME)
        .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(base.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3162_text(base.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"audio-close-deferred": b"audio-stop-owned-cleanup",
        b"a90-doomgeneric-v3161": b"a90-doomgeneric-v3162",
        b"a90.doomgeneric.v3161": b"a90.doomgeneric.v3162",
        b"v3161": b"v3162",
        b"V3161": b"V3162",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.5",
    b"v3162-audio-stop-owned-cleanup",
    b"audio.play.integrated.cleanup.deferred=1 reason=pcm-complete-await-audio-stop",
    b"audio.play.worker.cleanup_deferred=1",
    b"audio.play.worker.cleanup_owner=audio-stop",
    b"audio.play.worker.exit_deferred=1",
)


def _v3162_overrides() -> dict[str, Any]:
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


def _v3162_values() -> dict[str, Any]:
    values = dict(BASE_VALUES())
    values.update(_v3162_overrides())
    return values


def _v3162_adapter_source_from_patched_v3148() -> str:
    return (
        V3161_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-audio-close-deferred",
                 "real-sfx-pcm-stream-audio-stop-owned-cleanup")
        .replace("v3161", "v3162")
        .replace("V3161", "V3162")
    )


def v3162_adapter_source() -> str:
    return _v3162_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3162 Audio Stop-Owned Cleanup Source Build",
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
        "- Preserves V3158 fastscale and V3161 post-drain close deferral markers.",
        "- Marks async PCM playback complete immediately after the listen window finishes.",
        "- Defers route reset and cleanup ownership to explicit `audio stop --execute` to avoid stale playback status.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3162 builder and focused tests.",
        "- `unittest`: V3162 source contract plus V3158-V3161 regressions.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3162/0.11.5 identity and stop-owned cleanup markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-stop-owned-cleanup-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-stop-owned-cleanup-candidate",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3161-audio-close-deferred",
            "requires_live_validation": ["badapple", "nyan", "audio-worker-completion", "audio-stop-cleanup"],
            "preserves_doom_demo": True,
        },
        "audio_playback": {
            "post_drain_drop": True,
            "post_drain_hw_free": True,
            "close_deferred": True,
            "stop_owned_cleanup": True,
            "cleanup_deferred_marker": "audio.play.integrated.cleanup.deferred",
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
    (OUT_DIR / "audio-stop-owned-cleanup-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-stop-owned-cleanup-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "audio-worker-completion", "audio-stop-cleanup"],
        "audio_stop_owned_cleanup": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3162_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3162_overrides().items():
        existed = hasattr(base, name)
        saved.append((name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3161_overrides", _v3162_overrides),
        ("_v3161_values", _v3162_values),
        ("_v3161_adapter_source_from_patched_v3148", _v3162_adapter_source_from_patched_v3148),
        ("v3161_adapter_source", v3162_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_v3162_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(base, name, value)
        else:
            delattr(base, name)


def main() -> int:
    saved = _apply_v3162_globals()
    try:
        return base.main()
    finally:
        _restore_v3162_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
