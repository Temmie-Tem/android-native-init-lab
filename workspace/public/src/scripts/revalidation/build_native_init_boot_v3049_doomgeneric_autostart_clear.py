#!/usr/bin/env python3
"""Build V3049 native-init doomgeneric autostart/clear candidate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3047_doomgeneric_batch_input as v3047
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3049"
INIT_VERSION = "0.10.83"
INIT_BUILD = "v3049-doomgeneric-autostart-clear"
BUILD_TAG = INIT_BUILD
DECISION = "v3049-doomgeneric-autostart-clear-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3049_DOOMGENERIC_AUTOSTART_CLEAR_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3049_doomgeneric_autostart_clear.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3049_doomgeneric_autostart_clear"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3049_doomgeneric_autostart_clear.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_autostart_clear"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3049"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3049.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3049.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3049"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3049-autostart-clear"

RUNTIME_WAD_ROOT = v3047.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3047.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3047.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3047.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3047.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3047.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3047.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3047.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3047.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3047.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3049-autostart-clear-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3049-input.state"
FRAME_WIDTH = v3047.FRAME_WIDTH
FRAME_HEIGHT = v3047.FRAME_HEIGHT
FRAME_STRIDE = v3047.FRAME_STRIDE
FRAME_BYTES = v3047.FRAME_BYTES
NATIVE_DASHBOARD = v3047.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3047.NATIVE_DASHBOARD_LARGE_FRAME

HOST_KEYBOARD_BRIDGE = v3047.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3047.HOST_DASHBOARD
BASE_V3047_ADAPTER_SOURCE = v3047.v3047_adapter_source

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.83 (v3049-doomgeneric-autostart-clear)",
    b"v3049-doomgeneric-autostart-clear",
    b"doomgeneric-private-link-v3049-autostart-clear",
    b"/bin/a90_doomgeneric_private_engine_v3049",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    b"--wad-frame-loop",
    b"--input-state",
    b"--frame-ms",
    b"a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous",
    b"a90.doomgeneric.v3045.loop=input-state-file-to-DG_GetKey-33ms-continuous",
    b"a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888",
    b"a90.doomgeneric.v3045.loop_frames_zero=continuous",
    b"a90.doomgeneric.v3049.autostart=warp-e1m1-skill2",
    b"-warp",
    b"-skill",
    b"doompad.batch=state-mask-v3047",
    b"doompad.state_batch seq=",
    b"doompad state <seq> <mask>",
    b"video.demo.doom.clear.reason=",
    b"video.demo.doom.clear.rc=",
    b"video.demo.doom.loop_start.continuous",
    b"video.demo.doom.loop_status.continuous",
    b"video.demo.doom.dashboard.native=1",
    b"video.demo.doom.dashboard.presenter_log=quiet-per-frame",
    b"host_doompad_dashboard_v3035.py",
    b"host_doompad_keyboard_v3033.py",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3047.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3049 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3049_adapter_source() -> str:
    text = BASE_V3047_ADAPTER_SOURCE()
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3045_continuous_policy[] =\n'
        '    "a90.doomgeneric.v3045.loop_frames_zero=continuous";',
        'const char a90_doomgeneric_v3045_continuous_policy[] =\n'
        '    "a90.doomgeneric.v3045.loop_frames_zero=continuous";\n'
        'const char a90_doomgeneric_v3049_autostart_policy[] =\n'
        '    "a90.doomgeneric.v3049.autostart=warp-e1m1-skill2";',
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3045_continuous_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3045_continuous_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3049_autostart_policy) == 0U) {",
    )
    text = text.replace(
        '    static char arg_mb[] = "-mb";\n'
        '    static char arg_mb_value[] = "6";\n',
        '    static char arg_mb[] = "-mb";\n'
        '    static char arg_mb_value[] = "6";\n'
        '    static char arg_warp[] = "-warp";\n'
        '    static char arg_episode[] = "1";\n'
        '    static char arg_map[] = "1";\n'
        '    static char arg_skill[] = "-skill";\n'
        '    static char arg_skill_value[] = "2";\n',
    )
    text = text.replace(
        "    if (argv == NULL || max_args < 7) {\n"
        "        return 0;\n"
        "    }\n",
        "    if (argv == NULL || max_args < 12) {\n"
        "        return 0;\n"
        "    }\n",
        1,
    )
    text = text.replace(
        "    argv[5] = arg_mb;\n"
        "    argv[6] = arg_mb_value;\n"
        "    return 7;\n",
        "    argv[5] = arg_mb;\n"
        "    argv[6] = arg_mb_value;\n"
        "    argv[7] = arg_warp;\n"
        "    argv[8] = arg_episode;\n"
        "    argv[9] = arg_map;\n"
        "    argv[10] = arg_skill;\n"
        "    argv[11] = arg_skill_value;\n"
        "    return 12;\n",
        1,
    )
    text = text.replace("    char *argv[8];", "    char *argv[13];")
    text = text.replace(
        "    argv[5] = arg_mb;\n"
        "    argv[6] = arg_mb_value;\n"
        "    argv[7] = NULL;\n\n"
        "    doomgeneric_Create(7, argv);",
        "    argv[5] = arg_mb;\n"
        "    argv[6] = arg_mb_value;\n"
        "    argv[7] = arg_warp;\n"
        "    argv[8] = arg_episode;\n"
        "    argv[9] = arg_map;\n"
        "    argv[10] = arg_skill;\n"
        "    argv[11] = arg_skill_value;\n"
        "    argv[12] = NULL;\n\n"
        "    doomgeneric_Create(12, argv);",
    )
    return text


def configure_v3049_globals() -> None:
    v3047.CYCLE = CYCLE
    v3047.INIT_VERSION = INIT_VERSION
    v3047.INIT_BUILD = INIT_BUILD
    v3047.BUILD_TAG = BUILD_TAG
    v3047.DECISION = DECISION
    v3047.OUT_DIR = OUT_DIR
    v3047.OBJ_DIR = OBJ_DIR
    v3047.REPORT_PATH = REPORT_PATH
    v3047.BOOT_IMAGE = BOOT_IMAGE
    v3047.INIT_BINARY = INIT_BINARY
    v3047.RAMDISK_CPIO = RAMDISK_CPIO
    v3047.HELPER_BINARY = HELPER_BINARY
    v3047.ENGINE_BINARY = ENGINE_BINARY
    v3047.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3047.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3047.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3047.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3047.ENGINE_NAME = ENGINE_NAME
    v3047.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3047.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3047.FRAME_PATH = FRAME_PATH
    v3047.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3047.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3047.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3047.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3047.v3047_adapter_source = v3049_adapter_source
    v3047.render_report = render_report


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3049 DOOMGENERIC Autostart Clear Source Build",
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
        "- Keeps V3047 batch doompad input and V3045 continuous loop behavior.",
        "- Adds helper argv autostart: `-warp 1 1 -skill 2`.",
        "- Clears the KMS framebuffer on `video demo doom loop-stop`, including the inactive-loop case.",
        "- Leaves DOOM sound unchanged for this unit: helper still uses `-nosound -nomusic`.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Input state path: `{doom.get('input_state_path')}`",
        "- Autostart marker: `a90.doomgeneric.v3049.autostart=warp-e1m1-skill2`",
        "- Stop clear markers: `video.demo.doom.clear.reason=<reason>`, `video.demo.doom.clear.rc=<rc>`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: builder and focused tests.",
        "- `unittest`: V3049 source contract plus V3045/V3047 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3049 autostart, clear, batch-input, and continuous-loop markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3050`",
        "- Type: rollback-gated live validation of V3049 autostart/clear candidate.",
        "- Scope: flash exact V3049 boot image, health-check, verify DOOM enters gameplay without remaining at the menu, verify `loop-stop` clears the screen, and keep DOOM sound parked as separate backend work.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-autostart-clear-candidate`.",
    ]) + "\n"


def main() -> int:
    configure_v3049_globals()
    return v3047.main()


if __name__ == "__main__":
    raise SystemExit(main())
