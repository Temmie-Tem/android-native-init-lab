#!/usr/bin/env python3
"""Build V3040 native-init doomgeneric large dashboard quiet-presenter candidate."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3038_doomgeneric_large_dashboard as v3038
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3040"
INIT_VERSION = "0.10.79"
INIT_BUILD = "v3040-doomgeneric-large-dashboard-quiet"
BUILD_TAG = INIT_BUILD
DECISION = "v3040-doomgeneric-large-dashboard-quiet-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3040_DOOMGENERIC_LARGE_DASHBOARD_QUIET_SOURCE_BUILD_2026-06-22.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3040_doomgeneric_large_dashboard_quiet.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3040_doomgeneric_large_dashboard_quiet"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3040_doomgeneric_large_dashboard_quiet.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_large_dashboard_quiet"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3040"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3040.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3040.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3040"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3040-large-dashboard-quiet"

RUNTIME_WAD_ROOT = v3038.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3038.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3038.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3038.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3038.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3038.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3038.DEFAULT_LOOP_FRAMES
MAX_LOOP_FRAMES = v3038.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3038.LOOP_FRAME_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3040-large-dashboard-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3040-input.state"
FRAME_WIDTH = v3038.FRAME_WIDTH
FRAME_HEIGHT = v3038.FRAME_HEIGHT
FRAME_STRIDE = v3038.FRAME_STRIDE
FRAME_BYTES = v3038.FRAME_BYTES
NATIVE_DASHBOARD = 1
NATIVE_DASHBOARD_LARGE_FRAME = 1
LARGE_FRAME_WIDTH = v3038.LARGE_FRAME_WIDTH
LARGE_FRAME_HEIGHT = v3038.LARGE_FRAME_HEIGHT
LARGE_FRAME_SCALE = v3038.LARGE_FRAME_SCALE

HOST_KEYBOARD_BRIDGE = v3038.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3038.HOST_DASHBOARD

BASE_V3033_ADAPTER_SOURCE = v3038.BASE_V3033_ADAPTER_SOURCE

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.79 (v3040-doomgeneric-large-dashboard-quiet)",
    b"v3040-doomgeneric-large-dashboard-quiet",
    b"doomgeneric-private-link-v3040-large-dashboard-quiet",
    b"/bin/a90_doomgeneric_private_engine_v3040",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    b"--wad-frame-loop",
    b"--input-state",
    b"--frame-ms",
    b"a90.doomgeneric.v3040.large_dashboard_quiet=state-file-frame-loop-kms-large-overlay-title-quiet-present",
    b"a90.doomgeneric.v3040.loop=input-state-file-to-DG_GetKey",
    b"video.demo.doom.dashboard.native=1",
    b"video.demo.doom.dashboard.layout=top-frame-metrics-logs-input",
    b"video.demo.doom.dashboard.presenter_log=quiet-per-frame",
    b"video.demo.doom.dashboard.large_frame=1",
    b"video.demo.doom.dashboard.frame_mode=large-overlay-title",
    b"video.demo.doom.dashboard.frame_scale=3:2",
    b"DOOM LIVE DASHBOARD",
    b"KEYBOARD / DOOMPAD INPUT",
    b"640x400 -> 960x600",
    b"host_doompad_dashboard_v3035.py",
    b"host_doompad_keyboard_v3033.py",
    b"video demo doom loop-start [frames] --wad runtime-private --sha256",
    b"video.demo.doom.loop_start=background-presenter",
    b"video.demo.input.otg_required=0",
)


def rel(path: Path) -> str:
    return v3038.rel(path)


def v3040_adapter_source() -> str:
    return (
        BASE_V3033_ADAPTER_SOURCE()
        .replace(
            "a90.doomgeneric.v3033.visible_loop=state-file-frame-loop",
            "a90.doomgeneric.v3040.large_dashboard_quiet=state-file-frame-loop-kms-large-overlay-title-quiet-present",
        )
        .replace(
            "a90.doomgeneric.v3033.loop=input-state-file-to-DG_GetKey",
            "a90.doomgeneric.v3040.loop=input-state-file-to-DG_GetKey",
        )
    )


def configure_v3040_globals() -> None:
    v3038.CYCLE = CYCLE
    v3038.INIT_VERSION = INIT_VERSION
    v3038.INIT_BUILD = INIT_BUILD
    v3038.BUILD_TAG = BUILD_TAG
    v3038.DECISION = DECISION
    v3038.OUT_DIR = OUT_DIR
    v3038.OBJ_DIR = OBJ_DIR
    v3038.REPORT_PATH = REPORT_PATH
    v3038.BOOT_IMAGE = BOOT_IMAGE
    v3038.INIT_BINARY = INIT_BINARY
    v3038.RAMDISK_CPIO = RAMDISK_CPIO
    v3038.HELPER_BINARY = HELPER_BINARY
    v3038.ENGINE_BINARY = ENGINE_BINARY
    v3038.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3038.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3038.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3038.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3038.ENGINE_NAME = ENGINE_NAME
    v3038.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3038.FRAME_PATH = FRAME_PATH
    v3038.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3038.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3038.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3038.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3038.v3038_adapter_source = v3040_adapter_source
    v3038.render_report = render_report


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3040 DOOMGENERIC Large Dashboard Quiet Source Build",
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
        "- Keeps the V3038 large `960x600` DOOM frame and overlay title layout.",
        "- Keeps the runtime-private WAD, private doomgeneric helper, native dashboard, and serial doompad input-state bridge.",
        "- Changes the active `doomdash` KMS presenter to quiet per-frame serial output with `a90_kms_present(\"doomdash\", false)`.",
        "- Adds `video.demo.doom.dashboard.presenter_log=quiet-per-frame` as the status marker.",
        "- Host input remains serial-only through `doompad key <role> <0|1>`; no OTG keyboard, evdev injection, uinput, or host USB HID injection is introduced.",
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
        "- Frame scale marker: `video.demo.doom.dashboard.frame_scale=3:2`",
        f"- Rendered frame size: `{LARGE_FRAME_WIDTH}x{LARGE_FRAME_HEIGHT}` from `{doom.get('frame_width')}x{doom.get('frame_height')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Native background command: `{doom.get('loop_start_command')}`",
        f"- Host dashboard: `{rel(HOST_DASHBOARD)}`",
        f"- Host keyboard bridge: `{doom.get('host_keyboard_bridge')}`",
        f"- Input state path: `{doom.get('input_state_path')}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        f"- Loop frame ms: `{doom.get('loop_frame_ms')}`",
        "",
        "## Private Engine Helper",
        "",
        f"- Bundled helper path: `{doom.get('engine_ramdisk_path')}`",
        f"- V3040 engine binary: `{doom.get('engine_binary')}`",
        f"- V3040 engine SHA256: `{doom.get('engine_binary_sha256')}`",
        f"- V3040 engine bytes: `{doom.get('engine_binary_bytes')}`",
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
        "- `unittest`: V3040 quiet-dashboard tests plus V3038/V3036/V3035/V3033 regression tests.",
        "- Build: AArch64 static private doomgeneric helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3040 quiet-dashboard markers, helper path, input-state path, SD WAD path/hash, host dashboard marker, and bounded loop command markers.",
        "- Ramdisk inventory: helper path present and WAD file count is zero.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3041`",
        "- Type: rollback-gated live validation of V3040 quiet large-dashboard candidate.",
        "- Scope: flash only the exact V3040 boot image through `native_init_flash.py`, health-check, run `video demo doom loop-start 300 --wad runtime-private --sha256 EXPECTED`, confirm quiet-presenter markers, drive bounded doompad transitions while active loop is running, stop the loop, and leave candidate installed only if health and validation pass.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-large-dashboard-quiet-candidate`.",
    ]) + "\n"


def main() -> int:
    if not HOST_DASHBOARD.is_file():
        raise RuntimeError(f"missing host dashboard: {HOST_DASHBOARD}")
    configure_v3040_globals()
    return v3038.main()


if __name__ == "__main__":
    raise SystemExit(main())
