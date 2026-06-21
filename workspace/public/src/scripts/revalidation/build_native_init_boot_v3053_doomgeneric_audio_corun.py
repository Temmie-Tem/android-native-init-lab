#!/usr/bin/env python3
"""Build V3053 native-init DOOM audio co-run candidate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3051_doomgeneric_autostart_probe_fix as v3051
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3053"
INIT_VERSION = "0.10.85"
INIT_BUILD = "v3053-doomgeneric-audio-corun"
BUILD_TAG = INIT_BUILD
DECISION = "v3053-doomgeneric-audio-corun-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3053_DOOMGENERIC_AUDIO_CORUN_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3053_doomgeneric_audio_corun.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3053_doomgeneric_audio_corun"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3053_doomgeneric_audio_corun.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_audio_corun"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3053"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3053.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3053.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3053"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3053-audio-corun"

RUNTIME_WAD_ROOT = v3051.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3051.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3051.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3051.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3051.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3051.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3051.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3051.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3051.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3051.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3053-audio-corun-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3053-input.state"
FRAME_WIDTH = v3051.FRAME_WIDTH
FRAME_HEIGHT = v3051.FRAME_HEIGHT
FRAME_STRIDE = v3051.FRAME_STRIDE
FRAME_BYTES = v3051.FRAME_BYTES
NATIVE_DASHBOARD = v3051.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3051.NATIVE_DASHBOARD_LARGE_FRAME

SOUND_MODE = "native-audio-corun-tone-v3053"
AUDIO_CORUN = 1
AUDIO_CORUN_MODE = "native-audio-corun-tone-v3053"
AUDIO_CORUN_DURATION_MS = 10000
AUDIO_CORUN_AMPLITUDE_MILLI = 80

HOST_KEYBOARD_BRIDGE = v3051.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3051.HOST_DASHBOARD
BASE_V3051_ADAPTER_SOURCE = v3051.v3051_adapter_source

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.85 (v3053-doomgeneric-audio-corun)",
    b"v3053-doomgeneric-audio-corun",
    b"doomgeneric-private-link-v3053-audio-corun",
    b"/bin/a90_doomgeneric_private_engine_v3053",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    b"a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled",
    b"native-audio-corun-tone-v3053",
    b"video.demo.doom.audio_corun.enabled=",
    b"video.demo.doom.audio_corun.mode=",
    b"video.demo.doom.audio.corun=1",
    b"video.demo.doom.audio.source=native-bounded-tone",
    b"video.demo.doom.audio.real_doom_sfx=0",
    b"video.demo.doom.audio.start.rc=",
    b"video.demo.doom.loop_start.audio_nonfatal=1",
    b"video.demo.doom.audio.stop.requested=1",
    b"audio.stop.worker.tracked_pid=",
    b"audio.stop.worker.stop_rc=",
    b"doompad.batch=state-mask-v3047",
    b"video.demo.doom.clear.reason=",
    b"video.demo.doom.loop_start.continuous",
    b"video.demo.doom.dashboard.native=1",
    b"host_doompad_dashboard_v3035.py",
    b"host_doompad_keyboard_v3033.py",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3051.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3053 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3053_adapter_source() -> str:
    text = BASE_V3051_ADAPTER_SOURCE()
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3051_probe_policy[] =\n'
        '    "a90.doomgeneric.v3051.probe=autostart-argv12";',
        'const char a90_doomgeneric_v3051_probe_policy[] =\n'
        '    "a90.doomgeneric.v3051.probe=autostart-argv12";\n'
        'const char a90_doomgeneric_v3053_audio_policy[] =\n'
        '    "a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled";',
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3051_probe_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3051_probe_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3053_audio_policy) == 0U) {",
    )
    return text


def configure_v3053_globals() -> None:
    v3033 = v3051.v3049.v3047.v3045.v3042.v3040.v3038.v3033
    v3051.CYCLE = CYCLE
    v3051.INIT_VERSION = INIT_VERSION
    v3051.INIT_BUILD = INIT_BUILD
    v3051.BUILD_TAG = BUILD_TAG
    v3051.DECISION = DECISION
    v3051.OUT_DIR = OUT_DIR
    v3051.OBJ_DIR = OBJ_DIR
    v3051.REPORT_PATH = REPORT_PATH
    v3051.BOOT_IMAGE = BOOT_IMAGE
    v3051.INIT_BINARY = INIT_BINARY
    v3051.RAMDISK_CPIO = RAMDISK_CPIO
    v3051.HELPER_BINARY = HELPER_BINARY
    v3051.ENGINE_BINARY = ENGINE_BINARY
    v3051.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3051.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3051.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3051.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3051.ENGINE_NAME = ENGINE_NAME
    v3051.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3051.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3051.FRAME_PATH = FRAME_PATH
    v3051.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3051.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3051.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3051.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3051.v3051_adapter_source = v3053_adapter_source
    v3051.render_report = render_report

    v3033.SOUND_MODE = SOUND_MODE
    v3033.AUDIO_CORUN = AUDIO_CORUN
    v3033.AUDIO_CORUN_MODE = AUDIO_CORUN_MODE
    v3033.AUDIO_CORUN_DURATION_MS = AUDIO_CORUN_DURATION_MS
    v3033.AUDIO_CORUN_AMPLITUDE_MILLI = AUDIO_CORUN_AMPLITUDE_MILLI


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    audio = doom.get("audio_corun", {}) if isinstance(doom, dict) else {}
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3053 DOOMGENERIC Audio Co-run Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3051 DOOM autostart/probe behavior and V3047 batch input.",
        "- Enables `A90_DOOMGENERIC_AUDIO_CORUN=1` so `video demo doom loop-start` starts the existing native audio worker with a bounded internal-speaker tone.",
        "- Adds loop-start/loop-stop markers for the audio co-run path and records that this is not real DOOM SFX.",
        "- Updates `audio stop --execute` to terminate the tracked async audio worker before resetting playback route.",
        "- Leaves the private DOOM engine argv unchanged: `-nosound -nomusic` remains active.",
        "",
        "## Audio Co-run Contract",
        "",
        f"- Sound mode marker: `{SOUND_MODE}`",
        f"- Co-run enabled: `{int(bool(audio.get('enabled', AUDIO_CORUN)))}`",
        f"- Co-run mode: `{audio.get('mode', AUDIO_CORUN_MODE)}`",
        f"- Duration: `{audio.get('duration_ms', AUDIO_CORUN_DURATION_MS)}` ms",
        f"- Amplitude: `{audio.get('amplitude_milli', AUDIO_CORUN_AMPLITUDE_MILLI)}` milli",
        "- Source: `native-bounded-tone` through `audio play internal-speaker-safe --mode listen --execute`.",
        "- Real DOOM SFX backend: `0` for this unit.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Input state path: `{doom.get('input_state_path')}`",
        "- Autostart marker: `a90.doomgeneric.v3049.autostart=warp-e1m1-skill2`",
        "- Probe marker: `a90.doomgeneric.v3051.probe=autostart-argv12`",
        "- Audio marker: `a90.doomgeneric.v3053.audio=native-audio-corun-tone-real-sfx-disabled`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: V3053 source contract plus V3051/V3049 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3053 audio co-run, V3051 probe, V3049 autostart/clear, batch-input, and continuous-loop markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3054`",
        "- Type: rollback-gated live validation of V3053 audio co-run candidate.",
        "- Scope: flash exact V3053 boot image, health-check, run `video demo doom status`, `loop-start`, verify audio worker/status markers, verify `loop-stop` stops the tracked worker and clears the screen.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-audio-corun-candidate`.",
    ]) + "\n"


def main() -> int:
    configure_v3053_globals()
    return v3051.main()


if __name__ == "__main__":
    raise SystemExit(main())
