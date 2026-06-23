#!/usr/bin/env python3
"""Build V3123 DOOM direct shared blit with foreground summary-only serial logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3120_doomgeneric_direct_shared_blit as v3120

REPO_ROOT = repo_root()

CYCLE = "V3123"
INIT_VERSION = "0.10.116"
INIT_BUILD = "v3123-doomgeneric-summary-only-direct-blit"
BUILD_TAG = INIT_BUILD
DECISION = "v3123-doomgeneric-summary-only-direct-blit-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3123_DOOMGENERIC_SUMMARY_ONLY_DIRECT_BLIT_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3123_doomgeneric_summary_only_direct_blit.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3123_doomgeneric_summary_only_direct_blit"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3123_doomgeneric_summary_only_direct_blit.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v522_doomgeneric_summary_only_direct_blit"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3123"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3123.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3123.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3123"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3123-summary-only-direct-blit"

RUNTIME_WAD_ROOT = v3120.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3120.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3120.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3120.RUNTIME_WAD_MAX_BYTES
DEFAULT_LOOP_FRAMES = v3120.DEFAULT_LOOP_FRAMES
LOOP_FRAME_MS = v3120.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3120.PRESENTER_POLL_MS
FRAME_WIDTH = v3120.FRAME_WIDTH
FRAME_HEIGHT = v3120.FRAME_HEIGHT
FRAME_STRIDE = v3120.FRAME_STRIDE
FRAME_BYTES = v3120.FRAME_BYTES
FRAME_PATH = "/tmp/a90-doomgeneric-v3123-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3123-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3123-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3123-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3123-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3123-tick-telemetry.txt"
INPUT_UDP_PORT = v3120.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3120.DEVICE_NCM_HOST

NATIVE_DASHBOARD = v3120.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3120.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3120.NATIVE_DASHBOARD_LARGE_FRAME
HW_PLANE_SCALE = v3120.HW_PLANE_SCALE
PRE_SCALED_LARGE_FRAME = v3120.PRE_SCALED_LARGE_FRAME
NO_FULL_CLEAR = v3120.NO_FULL_CLEAR
DIRECT_SHARED_BLIT = v3120.DIRECT_SHARED_BLIT
FOREGROUND_FRAME_LOG = 0
FRAME_SCALE = v3120.FRAME_SCALE
SCALE_PATH = v3120.SCALE_PATH
FALLBACK_SCALE_PATH = v3120.FALLBACK_SCALE_PATH
FRAME_TIMING_PROBE = v3120.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3120.SEQ_TELEMETRY
NATIVE_DOOM_PRESENT_PAGEFLIP = v3120.NATIVE_DOOM_PRESENT_PAGEFLIP
CLEAR_PATH = v3120.CLEAR_PATH
FRAME_IPC = "shared-mmap-direct-blit-summary-only"

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3123.tick_telemetry=summary-only-direct-shared-blit"
SCALE_MARKER = "a90.doomgeneric.v3123.scale=producer-960x600-1to1-summary-only-direct-shared-blit"
PHASE_TELEMETRY_MARKER = "a90.doomgeneric.v3123.phase_telemetry=tick-draw-dump-split-summary-only-direct-shared-blit"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3123.gametic_frame_telemetry=loop-dump-gametic-summary-summary-only-direct-shared-blit"
)
DIRECT_SHARED_BLIT_MARKER = v3120.DIRECT_SHARED_BLIT_MARKER
SUMMARY_ONLY_MARKER = "video.demo.doom.loop.foreground_frame_log=0"

_V3120_APPLY_GLOBALS = v3120.apply_v3120_globals
_V3120_ADAPTER_SOURCE = v3120.v3120_adapter_source


def rel(path: Path) -> str:
    return v3120.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3120.TICK_TELEMETRY_MARKER.encode("ascii"): TICK_TELEMETRY_MARKER.encode("ascii"),
        v3120.SCALE_MARKER.encode("ascii"): SCALE_MARKER.encode("ascii"),
        v3120.PHASE_TELEMETRY_MARKER.encode("ascii"): PHASE_TELEMETRY_MARKER.encode("ascii"),
        v3120.GAMETIC_FRAME_TELEMETRY_MARKER.encode("ascii"): GAMETIC_FRAME_TELEMETRY_MARKER.encode("ascii"),
        v3120.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3120.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3120.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3120.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        b"a90-doomgeneric-v3120": b"a90-doomgeneric-v3123",
        b"a90.doomgeneric.v3120": b"a90.doomgeneric.v3123",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3120.REQUIRED_STRINGS) + (
    b"video.demo.doom.loop.foreground_frame_log=%d",
    b"video.demo.doom.dashboard.presenter_log=%s",
    b"summary-only",
)


def v3123_adapter_source() -> str:
    source = _V3120_ADAPTER_SOURCE()
    replacements = {
        v3120.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3120.SCALE_MARKER: SCALE_MARKER,
        v3120.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3120.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
        v3120.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3120.FRAME_PATH: FRAME_PATH,
        v3120.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3120.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3120.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3120.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
        "a90.doomgeneric.v3120": "a90.doomgeneric.v3123",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3123 DOOMGENERIC Summary-Only Direct Blit Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM frame IPC/copy reduction / validation-output decongestion.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Inherits V3120 direct shared-frame blit and V3118 no-full-clear pre-scaled producer behavior.",
        "- Adds `VIDEO_DEMO_DOOMGENERIC_FOREGROUND_FRAME_LOG=0` for this candidate, so foreground loop validation still draws each frame but does not emit per-frame dashboard lines over serial.",
        "- Adds loop-start summary markers for dashboard scale/no-full-clear/direct-reader state, preserving the evidence needed by live validation without flooding ACM output.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame geometry: `{FRAME_WIDTH}x{FRAME_HEIGHT}` stride `{FRAME_STRIDE}` bytes `{FRAME_BYTES}`",
        f"- Frame IPC: `{FRAME_IPC}`",
        f"- Scale path: `{SCALE_PATH}`",
        f"- Clear path: `{CLEAR_PATH}`",
        "- Expected live markers: `video.demo.doom.loop.presenter.reader=shared-mmap-direct-blit` and `video.demo.doom.loop.foreground_frame_log=0`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through the checked flash helper `native_init_flash.py` in the next live unit.",
        "- No GPU/GL stack, panel re-init, backlight, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- This source build only changes serial validation verbosity and keeps the userspace presenter read/blit path additive.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3123 builder and focused tests.",
        "- `unittest`: V3123 source contract plus V3122/V3120/V3119 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3123 identity, direct-shared-blit reader marker, summary-only foreground marker, pre-scaled/no-full-clear markers, shared-frame/pageflip/input/audio markers, and no HW-plane atomic requirement.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3124`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3123 image, require summary-only and direct-shared-blit markers, compare `timing.read.avg_us`, `timing.draw.avg_us`, and pageflip cadence against V3119/V3122.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-summary-only-direct-blit-candidate`.",
    ]) + "\n"


def configure_v3120_module() -> None:
    v3120.CYCLE = CYCLE
    v3120.INIT_VERSION = INIT_VERSION
    v3120.INIT_BUILD = INIT_BUILD
    v3120.BUILD_TAG = BUILD_TAG
    v3120.DECISION = DECISION
    v3120.OUT_DIR = OUT_DIR
    v3120.OBJ_DIR = OBJ_DIR
    v3120.REPORT_PATH = REPORT_PATH
    v3120.BOOT_IMAGE = BOOT_IMAGE
    v3120.INIT_BINARY = INIT_BINARY
    v3120.RAMDISK_CPIO = RAMDISK_CPIO
    v3120.HELPER_BINARY = HELPER_BINARY
    v3120.ENGINE_BINARY = ENGINE_BINARY
    v3120.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3120.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3120.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3120.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3120.ENGINE_NAME = ENGINE_NAME
    v3120.FRAME_PATH = FRAME_PATH
    v3120.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3120.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3120.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3120.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3120.TICK_TELEMETRY_PATH = TICK_TELEMETRY_PATH
    v3120.TICK_TELEMETRY_MARKER = TICK_TELEMETRY_MARKER
    v3120.SCALE_MARKER = SCALE_MARKER
    v3120.PHASE_TELEMETRY_MARKER = PHASE_TELEMETRY_MARKER
    v3120.GAMETIC_FRAME_TELEMETRY_MARKER = GAMETIC_FRAME_TELEMETRY_MARKER
    v3120.FRAME_IPC = FRAME_IPC
    v3120.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3120.v3120_adapter_source = v3123_adapter_source
    v3120.render_report = render_report


def apply_v3123_globals() -> None:
    configure_v3120_module()
    _V3120_APPLY_GLOBALS()
    v3033 = v3120.v3118.v3116.v3033_module()
    v3033.FOREGROUND_FRAME_LOG = FOREGROUND_FRAME_LOG


def main() -> int:
    original_apply = v3120.apply_v3120_globals
    try:
        configure_v3120_module()
        v3120.apply_v3120_globals = apply_v3123_globals
        rc = v3120.main()
    finally:
        v3120.apply_v3120_globals = original_apply

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "foreground_frame_log": bool(FOREGROUND_FRAME_LOG),
        "summary_only_foreground": True,
        "frame_ipc": FRAME_IPC,
        "presenter_reader": "shared-mmap-direct-blit",
        "expected_reader_marker": DIRECT_SHARED_BLIT_MARKER,
        "expected_summary_marker": SUMMARY_ONLY_MARKER,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-summary-only-direct-blit-candidate",
        "adoption_state": "pending-summary-only-direct-blit-live-validation",
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
    (OUT_DIR / "doomgeneric-summary-only-direct-blit-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-summary-only-direct-blit-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "frame_path": FRAME_PATH,
        "shared_frame_path": SHARED_FRAME_PATH,
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "frame_stride": FRAME_STRIDE,
        "frame_bytes": FRAME_BYTES,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "pace_socket_path": PACE_SOCKET_PATH,
        "scale_marker": SCALE_MARKER,
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "clear_path": CLEAR_PATH,
        "no_full_clear": bool(NO_FULL_CLEAR),
        "direct_shared_blit": bool(DIRECT_SHARED_BLIT),
        "foreground_frame_log": bool(FOREGROUND_FRAME_LOG),
        "frame_ipc": FRAME_IPC,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip-summary-only-direct-shared-blit",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(v3120.v3118.v3116.v3114.v3112.v3108.HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-summary-only-direct-blit-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
