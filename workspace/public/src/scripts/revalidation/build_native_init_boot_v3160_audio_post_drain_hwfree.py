#!/usr/bin/env python3
"""Build V3160 audio post-drain DROP+HW_FREE candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3159_audio_post_drain_drop as v3159

REPO_ROOT = repo_root()

CYCLE = "V3160"
INIT_VERSION = "0.11.3"
INIT_BUILD = "v3160-audio-post-drain-hwfree"
BUILD_TAG = INIT_BUILD
DECISION = "v3160-audio-post-drain-hwfree-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3160_AUDIO_POST_DRAIN_HWFREE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3160_audio_post_drain_hwfree.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3160_audio_post_drain_hwfree"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3160_audio_post_drain_hwfree.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v538_audio_post_drain_hwfree"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3160"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3160.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3160.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3160"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3160-audio-post-drain-hwfree"

FRAME_PATH = "/tmp/a90-doomgeneric-v3160-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3160-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3160-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3160-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3160-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3160-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3160-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-audio-post-drain-hwfree"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-audio-post-drain-hwfree"

INPUT_THREAD_MARKER = v3159.INPUT_THREAD_MARKER.replace("v3159", "v3160")
TIME_MODEL_MARKER = v3159.TIME_MODEL_MARKER.replace("v3159", "v3160")
DEMO_HUD_MARKER = v3159.DEMO_HUD_MARKER.replace("v3159", "v3160")
PACED_TIME_MARKER = v3159.PACED_TIME_MARKER.replace("v3159", "v3160")
TICK_TELEMETRY_MARKER = v3159.TICK_TELEMETRY_MARKER.replace("v3159", "v3160")
SCALE_MARKER = v3159.SCALE_MARKER.replace("v3159", "v3160")
PHASE_TELEMETRY_MARKER = v3159.PHASE_TELEMETRY_MARKER.replace("v3159", "v3160")
GAMETIC_FRAME_TELEMETRY_MARKER = v3159.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3159",
    "v3160",
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3160.audio=real-sfx-pcm-stream-audio-post-drain-hwfree"
SOUND_MODE = "native-doom-sfx-audio-post-drain-hwfree-v3160"

AUDIO_CORUN = v3159.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = v3159.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = v3159.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = v3159.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3159.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = v3159.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3160.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = v3159.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = v3159.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES

V3159_ADAPTER_SOURCE_TEXT = v3159.v3159_adapter_source()
V3159_OVERRIDES = v3159._v3159_overrides


def rel(path: Path) -> str:
    return v3159.rel(path)


def _rewrite_v3160_text(text: str) -> str:
    return (
        text.replace(v3159.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
        .replace("audio-post-drain-drop", "audio-post-drain-hwfree")
        .replace("v3159", "v3160")
        .replace("V3159", "V3160")
        .replace(v3159.INIT_VERSION, INIT_VERSION)
        .replace(v3159.INIT_BUILD, INIT_BUILD)
        .replace(v3159.ENGINE_NAME, ENGINE_NAME)
        .replace(v3159.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
        .replace(v3159.SOUND_MODE, SOUND_MODE)
    )


SFX_BACKEND_SOURCE_TEXT = _rewrite_v3160_text(v3159.SFX_BACKEND_SOURCE_TEXT)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3159.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3159.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3159.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3159.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3159.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        v3159.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        v3159.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"audio-post-drain-drop": b"audio-post-drain-hwfree",
        b"a90-doomgeneric-v3159": b"a90-doomgeneric-v3160",
        b"a90.doomgeneric.v3159": b"a90.doomgeneric.v3160",
        b"v3159": b"v3160",
        b"V3159": b"V3160",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3159.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.3",
    b"v3160-audio-post-drain-hwfree",
    b"audio.play.execute.post_drain_drop.rc=%d errno=%d",
    b"audio.play.execute.post_drain_hw_free.rc=%d errno=%d",
    b"audio.play.worker.post_drain_hw_free_rc=%d",
)


def _v3160_overrides() -> dict[str, Any]:
    overrides = dict(V3159_OVERRIDES())
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


def _v3160_values() -> dict[str, Any]:
    values = dict(v3159.v3158.v3157.v3156.v3155._ORIGINAL_V3154_VALUES())
    values.update(_v3160_overrides())
    return values


def _v3160_adapter_source_from_patched_v3148() -> str:
    return (
        V3159_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-audio-post-drain-drop",
                 "real-sfx-pcm-stream-audio-post-drain-hwfree")
        .replace("v3159", "v3160")
        .replace("V3159", "V3160")
    )


def v3160_adapter_source() -> str:
    return _v3160_adapter_source_from_patched_v3148()


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3160 Audio Post-Drain HW_FREE Source Build",
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
        "- Preserves V3158 Bad Apple/Nyan Player HUD fastscale and V3159 post-drain DROP.",
        "- Adds `SNDRV_PCM_IOCTL_HW_FREE` after drain/drop before PCM close to prevent worker close hangs.",
        "- Exports `audio.play.execute.post_drain_hw_free.*` worker markers for live validation.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No PMIC, regulator, GDSC, GPIO writes, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- The audio change stays inside the safe internal speaker playback path.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3160 builder and focused tests.",
        "- `unittest`: V3160 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3160/0.11.3 identity and audio post-drain HW_FREE marker.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `audio-post-drain-hwfree-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-post-drain-hwfree-candidate",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
        "promotion": {
            "patch_version": INIT_VERSION,
            "source_baseline": "v3159-audio-post-drain-drop",
            "requires_live_validation": ["badapple", "nyan", "audio-worker-completion"],
            "preserves_doom_demo": True,
        },
        "audio_playback": {
            "post_drain_drop": True,
            "post_drain_hw_free": True,
            "post_drain_drop_marker": "audio.play.execute.post_drain_drop.rc",
            "post_drain_hw_free_marker": "audio.play.execute.post_drain_hw_free.rc",
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
    (OUT_DIR / "audio-post-drain-hwfree-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "audio-post-drain-hwfree-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": ["badapple", "nyan", "audio-worker-completion"],
        "audio_post_drain_drop": True,
        "audio_post_drain_hw_free": True,
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-badapple-nyan-av-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _apply_v3160_globals() -> list[tuple[str, Any, bool]]:
    saved: list[tuple[str, Any, bool]] = []
    for name, value in _v3160_overrides().items():
        existed = hasattr(v3159, name)
        saved.append((name, getattr(v3159, name, None), existed))
        setattr(v3159, name, value)
    for name, value in (
        ("_v3159_overrides", _v3160_overrides),
        ("_v3159_values", _v3160_values),
        ("_v3159_adapter_source_from_patched_v3148", _v3160_adapter_source_from_patched_v3148),
        ("v3159_adapter_source", v3160_adapter_source),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((name, getattr(v3159, name), True))
        setattr(v3159, name, value)
    return saved


def _restore_v3160_globals(saved: list[tuple[str, Any, bool]]) -> None:
    for name, value, existed in reversed(saved):
        if existed:
            setattr(v3159, name, value)
        else:
            delattr(v3159, name)


def main() -> int:
    saved = _apply_v3160_globals()
    try:
        return v3159.main()
    finally:
        _restore_v3160_globals(saved)


if __name__ == "__main__":
    raise SystemExit(main())
