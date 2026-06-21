#!/usr/bin/env python3
"""Build V3045 native-init doomgeneric continuous loop candidate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3042_doomgeneric_latency_color as v3042
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3045"
INIT_VERSION = "0.10.81"
INIT_BUILD = "v3045-doomgeneric-continuous-loop"
BUILD_TAG = INIT_BUILD
DECISION = "v3045-doomgeneric-continuous-loop-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3045_DOOMGENERIC_CONTINUOUS_LOOP_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3045_doomgeneric_continuous_loop.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3045_doomgeneric_continuous_loop"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3045_doomgeneric_continuous_loop.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_continuous_loop"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3045"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3045.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3045.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3045"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3045-continuous-loop"

RUNTIME_WAD_ROOT = v3042.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3042.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3042.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3042.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3042.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3042.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3042.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = 0
MAX_LOOP_FRAMES = v3042.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3042.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3045-continuous-loop-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3045-input.state"
FRAME_WIDTH = v3042.FRAME_WIDTH
FRAME_HEIGHT = v3042.FRAME_HEIGHT
FRAME_STRIDE = v3042.FRAME_STRIDE
FRAME_BYTES = v3042.FRAME_BYTES
NATIVE_DASHBOARD = v3042.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3042.NATIVE_DASHBOARD_LARGE_FRAME
LARGE_FRAME_WIDTH = v3042.LARGE_FRAME_WIDTH
LARGE_FRAME_HEIGHT = v3042.LARGE_FRAME_HEIGHT
LARGE_FRAME_SCALE = v3042.LARGE_FRAME_SCALE

HOST_KEYBOARD_BRIDGE = v3042.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3042.HOST_DASHBOARD
BASE_V3042_ADAPTER_SOURCE = v3042.v3042_adapter_source

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.81 (v3045-doomgeneric-continuous-loop)",
    b"v3045-doomgeneric-continuous-loop",
    b"doomgeneric-private-link-v3045-continuous-loop",
    b"/bin/a90_doomgeneric_private_engine_v3045",
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
    b"video.demo.doom.loop_start.continuous",
    b"video.demo.doom.loop_status.continuous",
    b"video.demo.doom.dashboard.native=1",
    b"video.demo.doom.dashboard.layout=top-frame-metrics-logs-input",
    b"video.demo.doom.dashboard.presenter_log=quiet-per-frame",
    b"video.demo.doom.dashboard.large_frame=1",
    b"video.demo.doom.dashboard.frame_mode=large-overlay-title",
    b"DOOM LIVE DASHBOARD",
    b"KEYBOARD / DOOMPAD INPUT",
    b"host_doompad_dashboard_v3035.py",
    b"host_doompad_keyboard_v3033.py",
    b"video demo doom loop-start [frames] --wad runtime-private --sha256",
    b"video.demo.doom.loop_start=background-presenter",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3042.rel(path)


def replace_required(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing source fragment for V3045 patch: {old[:80]!r}")
    return text.replace(old, new)


def v3045_adapter_source() -> str:
    text = (
        BASE_V3042_ADAPTER_SOURCE()
        .replace(
            "a90.doomgeneric.v3042.latency_color=33ms-loop-rb-swap-xbgr8888",
            "a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous",
        )
        .replace(
            "a90.doomgeneric.v3042.loop=input-state-file-to-DG_GetKey-33ms",
            "a90.doomgeneric.v3045.loop=input-state-file-to-DG_GetKey-33ms-continuous",
        )
        .replace(
            "a90.doomgeneric.v3042.frame_color=rb-swap-to-xbgr8888",
            "a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888",
        )
    )
    text = replace_required(
        text,
        'const char a90_doomgeneric_v3042_color_policy[] =\n'
        '    "a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888";',
        'const char a90_doomgeneric_v3042_color_policy[] =\n'
        '    "a90.doomgeneric.v3045.frame_color=rb-swap-to-xbgr8888";\n'
        'const char a90_doomgeneric_v3045_continuous_policy[] =\n'
        '    "a90.doomgeneric.v3045.loop_frames_zero=continuous";',
    )
    text = replace_required(
        text,
        "int a90_doomgeneric_run_wad_frame_loop(const char *wad_path,",
        "static int a90_doomgeneric_parse_loop_frames(const char *text, int max_value) {\n"
        "    if (text != NULL && strcmp(text, \"0\") == 0) {\n"
        "        return 0;\n"
        "    }\n"
        "    return a90_doomgeneric_parse_positive_int(text, max_value);\n"
        "}\n\n"
        "int a90_doomgeneric_run_wad_frame_loop(const char *wad_path,",
    )
    text = replace_required(
        text,
        "frames <= 0 || frames > 300 || frame_ms <= 0 || frame_ms > 250) {",
        "frames < 0 || frames > 300 || frame_ms <= 0 || frame_ms > 250) {",
    )
    text = replace_required(
        text,
        "for (index = 0; index < frames; ++index) {",
        "for (index = 0; frames == 0 || index < frames; ++index) {",
    )
    text = replace_required(
        text,
        "frames = a90_doomgeneric_parse_positive_int(argv[4], 300);\n"
        "        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);\n"
        "        if (frames <= 0 || frame_ms <= 0) {",
        "frames = a90_doomgeneric_parse_loop_frames(argv[4], 300);\n"
        "        frame_ms = a90_doomgeneric_parse_positive_int(argv[10], 250);\n"
        "        if (frames < 0 || frame_ms <= 0) {",
    )
    text = replace_required(
        text,
        "marker_checksum(a90_doomgeneric_v3033_loop_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3042_color_policy) == 0U) {",
        "marker_checksum(a90_doomgeneric_v3033_loop_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3042_color_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3045_continuous_policy) == 0U) {",
    )
    return text


def configure_v3045_globals() -> None:
    v3042.CYCLE = CYCLE
    v3042.INIT_VERSION = INIT_VERSION
    v3042.INIT_BUILD = INIT_BUILD
    v3042.BUILD_TAG = BUILD_TAG
    v3042.DECISION = DECISION
    v3042.OUT_DIR = OUT_DIR
    v3042.OBJ_DIR = OBJ_DIR
    v3042.REPORT_PATH = REPORT_PATH
    v3042.BOOT_IMAGE = BOOT_IMAGE
    v3042.INIT_BINARY = INIT_BINARY
    v3042.RAMDISK_CPIO = RAMDISK_CPIO
    v3042.HELPER_BINARY = HELPER_BINARY
    v3042.ENGINE_BINARY = ENGINE_BINARY
    v3042.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3042.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3042.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3042.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3042.ENGINE_NAME = ENGINE_NAME
    v3042.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3042.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3042.FRAME_PATH = FRAME_PATH
    v3042.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3042.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3042.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3042.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3042.v3042_adapter_source = v3045_adapter_source
    v3042.render_report = render_report


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    continuous_command = (
        f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}"
    )
    default_continuous_command = (
        f"video demo doom loop-start --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}"
    )
    return "\n".join([
        "# Native Init V3045 DOOMGENERIC Continuous Loop Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        "- Device action: `none` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps the V3042 33ms helper cadence, large native dashboard, quiet presenter, and red/blue channel correction.",
        "- Extends the private doomgeneric helper so `--frames 0` means continuous frame loop.",
        "- Extends native `video demo doom loop-start` so the omitted-frame default and explicit `0` start a continuous background presenter.",
        "- Keeps foreground `video demo doom loop` bounded by default so the serial command path is not accidentally held forever.",
        "- Host input remains serial-only through `doompad key <role> <0|1>`; no OTG keyboard, evdev injection, uinput, or host USB HID injection is introduced.",
        "",
        "## Continuous Loop Contract",
        "",
        "- Candidate marker: `a90.doomgeneric.v3045.continuous_loop=33ms-loop-start-zero-continuous`",
        "- Loop marker: `a90.doomgeneric.v3045.loop=input-state-file-to-DG_GetKey-33ms-continuous`",
        "- Helper marker: `a90.doomgeneric.v3045.loop_frames_zero=continuous`",
        f"- Continuous loop frames sentinel: `{CONTINUOUS_LOOP_FRAMES}`",
        f"- Continuous explicit command: `{continuous_command}`",
        f"- Continuous default command: `{default_continuous_command}`",
        f"- Bounded foreground command remains: `{doom.get('loop_command')}`",
        f"- Helper loop frame ms: `{doom.get('loop_frame_ms')}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Input state path: `{doom.get('input_state_path')}`",
        "",
        "## Runtime WAD Contract",
        "",
        f"- Runtime WAD root: `{doom.get('runtime_wad_root')}`",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Runtime WAD max bytes: `{doom.get('runtime_wad_max_bytes')}`",
        f"- WAD files in ramdisk: `{doom.get('ramdisk_wad_file_count')}`",
        f"- Public WAD files committed/present: `{doom.get('public_wad_file_count')}`",
        f"- WAD bytes embedded in boot image: `{doom.get('wad_embedded_in_boot')}`",
        "",
        "## Dashboard Contract",
        "",
        "- Native dashboard flag: `A90_DOOMGENERIC_NATIVE_DASHBOARD=1`",
        "- Large-frame flag: `A90_DOOMGENERIC_NATIVE_DASHBOARD_LARGE_FRAME=1`",
        "- Presenter log marker: `video.demo.doom.dashboard.presenter_log=quiet-per-frame`",
        "- Frame mode marker: `video.demo.doom.dashboard.frame_mode=large-overlay-title`",
        f"- Rendered frame size: `{LARGE_FRAME_WIDTH}x{LARGE_FRAME_HEIGHT}` from `{doom.get('frame_width')}x{doom.get('frame_height')}`",
        f"- Host dashboard: `{rel(HOST_DASHBOARD)}`",
        f"- Host keyboard bridge: `{doom.get('host_keyboard_bridge')}`",
        "",
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3045 engine binary: `{doom.get('engine_binary')}`",
        f"- V3045 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3045 engine bytes: `{doom.get('engine_binary_bytes')}`",
        f"- Helper bundled in ramdisk: `{int(bool(doom.get('helper_bundled_in_ramdisk')))}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Safety",
        "",
        "- No device action was performed by this builder.",
        "- No flash, serial live command, Wi-Fi action, sysfs write, evdev injection, uinput, PMIC, regulator, backlight, GPIO, GDSC, or forbidden partition path is touched.",
        "- WAD/IWAD bytes remain only on the runtime SD path and are not copied into public, ramdisk, boot image, reports, or generated source.",
        "- The generated boot image and helper are private/untracked. Public output is limited to source, tests, host tooling, and this metadata-only report.",
        "- Rollback target remains `v2321-usb-clean-identity-rodata` for the next live unit.",
        "",
        "## Host Validation",
        "",
        "- `py_compile`: builder, dependent host scripts, and focused tests.",
        "- `unittest`: V3045 continuous-loop tests plus V3042/V3040/V3038 host regressions.",
        "- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3045 continuous-loop markers, helper path, input-state path, SD WAD path/hash, host dashboard marker, and continuous status markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3046`",
        "- Type: rollback-gated live validation of V3045 continuous-loop candidate.",
        "- Scope: flash only the exact V3045 boot image through `native_init_flash.py`, health-check, run `video demo doom loop-start 0 --wad runtime-private --sha256 EXPECTED`, confirm continuous loop-status markers, drive host keyboard/dashboard input for more than the old 300-frame lifetime, stop the loop, and leave candidate installed only if health and validation pass.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-continuous-loop-candidate`.",
    ]) + "\n"


def main() -> int:
    if not HOST_DASHBOARD.is_file():
        raise RuntimeError(f"missing host dashboard: {HOST_DASHBOARD}")
    configure_v3045_globals()
    return v3042.main()


if __name__ == "__main__":
    raise SystemExit(main())
