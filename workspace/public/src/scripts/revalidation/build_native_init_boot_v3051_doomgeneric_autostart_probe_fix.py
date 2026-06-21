#!/usr/bin/env python3
"""Build V3051 native-init doomgeneric autostart probe-fix candidate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3049_doomgeneric_autostart_clear as v3049
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3051"
INIT_VERSION = "0.10.84"
INIT_BUILD = "v3051-doomgeneric-autostart-probe-fix"
BUILD_TAG = INIT_BUILD
DECISION = "v3051-doomgeneric-autostart-probe-fix-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3051_DOOMGENERIC_AUTOSTART_PROBE_FIX_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3051_doomgeneric_autostart_probe_fix.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3051_doomgeneric_autostart_probe_fix"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3051_doomgeneric_autostart_probe_fix.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_autostart_probe_fix"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3051"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3051.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3051.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3051"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3051-autostart-probe-fix"

RUNTIME_WAD_ROOT = v3049.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3049.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3049.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3049.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3049.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3049.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3049.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3049.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3049.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3049.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3051-autostart-probe-fix-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3051-input.state"
FRAME_WIDTH = v3049.FRAME_WIDTH
FRAME_HEIGHT = v3049.FRAME_HEIGHT
FRAME_STRIDE = v3049.FRAME_STRIDE
FRAME_BYTES = v3049.FRAME_BYTES
NATIVE_DASHBOARD = v3049.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3049.NATIVE_DASHBOARD_LARGE_FRAME

HOST_KEYBOARD_BRIDGE = v3049.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3049.HOST_DASHBOARD
BASE_V3049_ADAPTER_SOURCE = v3049.v3049_adapter_source

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.84 (v3051-doomgeneric-autostart-probe-fix)",
    b"v3051-doomgeneric-autostart-probe-fix",
    b"doomgeneric-private-link-v3051-autostart-probe-fix",
    b"/bin/a90_doomgeneric_private_engine_v3051",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    b"a90.doomgeneric.v3049.autostart=warp-e1m1-skill2",
    b"a90.doomgeneric.v3051.probe=autostart-argv12",
    b"-warp",
    b"-skill",
    b"doompad.batch=state-mask-v3047",
    b"video.demo.doom.clear.reason=",
    b"video.demo.doom.clear.rc=",
    b"video.demo.doom.loop_start.continuous",
    b"video.demo.doom.loop_status.continuous",
    b"video.demo.doom.dashboard.native=1",
    b"host_doompad_dashboard_v3035.py",
    b"host_doompad_keyboard_v3033.py",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3049.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3051 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3051_adapter_source() -> str:
    text = BASE_V3049_ADAPTER_SOURCE()
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3049_autostart_policy[] =\n'
        '    "a90.doomgeneric.v3049.autostart=warp-e1m1-skill2";',
        'const char a90_doomgeneric_v3049_autostart_policy[] =\n'
        '    "a90.doomgeneric.v3049.autostart=warp-e1m1-skill2";\n'
        'const char a90_doomgeneric_v3051_probe_policy[] =\n'
        '    "a90.doomgeneric.v3051.probe=autostart-argv12";',
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3049_autostart_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3049_autostart_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3051_probe_policy) == 0U) {",
    )
    text = replace_required(
        text,
        "    char *argv[8] = {0};\n"
        "    int argc = a90_doomgeneric_prepare_argv(argv, 8);\n",
        "    char *argv[13] = {0};\n"
        "    int argc = a90_doomgeneric_prepare_argv(argv, 13);\n",
    )
    text = replace_required(
        text,
        '    if (argc != 7 || strcmp(argv[1], "-iwad") != 0 ||\n'
        '        strcmp(argv[2], A90_DG_RUNTIME_WAD_PATH) != 0 ||\n'
        '        strcmp(argv[3], "-nosound") != 0 ||\n'
        '        strcmp(argv[4], "-nomusic") != 0) {\n'
        '        return 20;\n'
        '    }\n',
        '    if (argc != 12 || strcmp(argv[1], "-iwad") != 0 ||\n'
        '        strcmp(argv[2], A90_DG_RUNTIME_WAD_PATH) != 0 ||\n'
        '        strcmp(argv[3], "-nosound") != 0 ||\n'
        '        strcmp(argv[4], "-nomusic") != 0 ||\n'
        '        strcmp(argv[7], "-warp") != 0 ||\n'
        '        strcmp(argv[8], "1") != 0 ||\n'
        '        strcmp(argv[9], "1") != 0 ||\n'
        '        strcmp(argv[10], "-skill") != 0 ||\n'
        '        strcmp(argv[11], "2") != 0) {\n'
        '        return 20;\n'
        '    }\n',
    )
    return text


def configure_v3051_globals() -> None:
    v3049.CYCLE = CYCLE
    v3049.INIT_VERSION = INIT_VERSION
    v3049.INIT_BUILD = INIT_BUILD
    v3049.BUILD_TAG = BUILD_TAG
    v3049.DECISION = DECISION
    v3049.OUT_DIR = OUT_DIR
    v3049.OBJ_DIR = OBJ_DIR
    v3049.REPORT_PATH = REPORT_PATH
    v3049.BOOT_IMAGE = BOOT_IMAGE
    v3049.INIT_BINARY = INIT_BINARY
    v3049.RAMDISK_CPIO = RAMDISK_CPIO
    v3049.HELPER_BINARY = HELPER_BINARY
    v3049.ENGINE_BINARY = ENGINE_BINARY
    v3049.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3049.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3049.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3049.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3049.ENGINE_NAME = ENGINE_NAME
    v3049.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3049.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3049.FRAME_PATH = FRAME_PATH
    v3049.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3049.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3049.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3049.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3049.v3049_adapter_source = v3051_adapter_source
    v3049.render_report = render_report


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3051 DOOMGENERIC Autostart Probe Fix Source Build",
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
        "- Keeps V3049 autostart and loop-stop clear behavior.",
        "- Fixes private helper self-probe to validate the 12-argument autostart argv contract.",
        "- Leaves DOOM sound unchanged: `-nosound -nomusic` remains in argv.",
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
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: V3051 source contract plus V3049/V3047 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3051 probe, V3049 autostart/clear, batch-input, and continuous-loop markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3052`",
        "- Type: rollback-gated live validation of V3051 probe-fix candidate.",
        "- Scope: flash exact V3051 boot image, health-check, require engine-probe `rc=0`, verify DOOM loop start/status, verify loop-stop clear, and keep DOOM sound parked as separate backend work.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-autostart-probe-fix-candidate`.",
    ]) + "\n"


def main() -> int:
    configure_v3051_globals()
    return v3049.main()


if __name__ == "__main__":
    raise SystemExit(main())
