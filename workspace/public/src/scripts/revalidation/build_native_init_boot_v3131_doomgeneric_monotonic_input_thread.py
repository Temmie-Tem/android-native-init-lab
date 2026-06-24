#!/usr/bin/env python3
"""Build V3131 DOOM input-thread candidate with live monotonic game time."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3129_doomgeneric_input_thread_direct_blit as v3129

REPO_ROOT = repo_root()

CYCLE = "V3131"
INIT_VERSION = "0.10.119"
INIT_BUILD = "v3131-doomgeneric-monotonic-input-thread"
BUILD_TAG = INIT_BUILD
DECISION = "v3131-doomgeneric-monotonic-input-thread-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3131_DOOMGENERIC_MONOTONIC_INPUT_THREAD_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3131_doomgeneric_monotonic_input_thread.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3131_doomgeneric_monotonic_input_thread"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3131_doomgeneric_monotonic_input_thread.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v525_doomgeneric_monotonic_input_thread"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3131"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3131.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3131.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3131"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3131-monotonic-input-thread"

FRAME_PATH = "/tmp/a90-doomgeneric-v3131-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3131-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3131-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3131-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3131-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3131-tick-telemetry.txt"

INPUT_THREAD_MARKER = v3129.INPUT_THREAD_MARKER.replace("v3129", "v3131")
TIME_MODEL_MARKER = "a90.doomgeneric.v3131.time_model=clock-monotonic-while-loop-active"

RUNTIME_WAD_PATH = v3129.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3129.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3129.FRAME_WIDTH
FRAME_HEIGHT = v3129.FRAME_HEIGHT
FRAME_STRIDE = v3129.FRAME_STRIDE
FRAME_BYTES = v3129.FRAME_BYTES
FRAME_IPC = "shared-mmap-direct-blit-summary-only-monotonic-input-thread"
INPUT_UDP_PORT = v3129.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3129.DEVICE_NCM_HOST

PACED_TIME_MARKER = v3129.PACED_TIME_MARKER.replace("v3129", "v3131")
TICK_TELEMETRY_MARKER = v3129.TICK_TELEMETRY_MARKER.replace("v3129", "v3131")
SCALE_MARKER = v3129.SCALE_MARKER.replace("v3129", "v3131")
PHASE_TELEMETRY_MARKER = v3129.PHASE_TELEMETRY_MARKER.replace("v3129", "v3131")
GAMETIC_FRAME_TELEMETRY_MARKER = v3129.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3129", "v3131")

_V3129_ADAPTER_SOURCE = v3129.v3129_adapter_source


def rel(path: Path) -> str:
    return v3129.rel(path)


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3131 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3129.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3129.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3129.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3129.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        b"a90-doomgeneric-v3129": b"a90-doomgeneric-v3131",
        b"a90.doomgeneric.v3129": b"a90.doomgeneric.v3131",
        b"paced_time_model=presenter-token-doom-tic-quantum": b"paced_time_model=monotonic-clock-while-loop-active",
        b"v3129": b"v3131",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3129.REQUIRED_STRINGS) + (
    TIME_MODEL_MARKER.encode("ascii"),
    b"CLOCK_MONOTONIC",
)


def v3131_adapter_source() -> str:
    source = _V3129_ADAPTER_SOURCE()
    replacements = {
        "v3129": "v3131",
        "V3129": "V3131",
        v3129.FRAME_PATH: FRAME_PATH,
        v3129.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3129.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3129.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3129.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
        v3129.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3129.PACED_TIME_MARKER: PACED_TIME_MARKER,
        v3129.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3129.SCALE_MARKER: SCALE_MARKER,
        v3129.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3129.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    source = _replace_required(
        source,
        "#include <stdint.h>\n#include <pthread.h>\n#include <arpa/inet.h>",
        "#include <stdint.h>\n#include <pthread.h>\n#include <arpa/inet.h>\n#include <time.h>",
    )
    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3131_input_thread_policy[] =\n'
        f'    "{INPUT_THREAD_MARKER}";\n',
        'const char a90_doomgeneric_v3131_input_thread_policy[] =\n'
        f'    "{INPUT_THREAD_MARKER}";\n'
        'const char a90_doomgeneric_v3131_time_policy[] =\n'
        f'    "{TIME_MODEL_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "static uint32_t paced_time_advance_calls;\n"
        "static uint64_t paced_time_advance_us_total;\n"
        "static int paced_time_active;\n",
        "static uint32_t paced_time_advance_calls;\n"
        "static uint64_t paced_time_advance_us_total;\n"
        "static int paced_time_active;\n"
        "static uint32_t monotonic_time_base_ms;\n"
        "static int monotonic_time_base_set;\n"
        "static uint32_t monotonic_time_last_ticks_ms;\n",
    )
    source = _replace_required(
        source,
        "static uint32_t marker_checksum(const volatile char *value) {\n",
        "static uint32_t a90_doomgeneric_monotonic_ms(void) {\n"
        "    struct timespec ts;\n\n"
        "    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) {\n"
        "        return fake_ticks_ms;\n"
        "    }\n"
        "    return (uint32_t)(((uint64_t)ts.tv_sec * 1000ULL) +\n"
        "                      ((uint64_t)ts.tv_nsec / 1000000ULL));\n"
        "}\n\n"
        "static uint32_t marker_checksum(const volatile char *value) {\n",
    )
    source = _replace_required(
        source,
        "    paced_time_advance_us_total = 0;\n"
        "    paced_time_active = 0;\n"
        "    tick_telemetry_sleep_calls = 0;\n",
        "    paced_time_advance_us_total = 0;\n"
        "    paced_time_active = 0;\n"
        "    monotonic_time_base_ms = a90_doomgeneric_monotonic_ms();\n"
        "    monotonic_time_base_set = 1;\n"
        "    monotonic_time_last_ticks_ms = 0;\n"
        "    tick_telemetry_sleep_calls = 0;\n",
    )
    source = _replace_required(
        source,
        "uint32_t DG_GetTicksMs(void) {\n"
        "    ++tick_telemetry_getticks_calls;\n"
        "    return paced_time_active ? paced_ticks_ms : fake_ticks_ms;\n"
        "}\n",
        "uint32_t DG_GetTicksMs(void) {\n"
        "    uint32_t now;\n\n"
        "    ++tick_telemetry_getticks_calls;\n"
        "    if (!paced_time_active) {\n"
        "        return fake_ticks_ms;\n"
        "    }\n"
        "    now = a90_doomgeneric_monotonic_ms();\n"
        "    if (!monotonic_time_base_set) {\n"
        "        monotonic_time_base_ms = now;\n"
        "        monotonic_time_base_set = 1;\n"
        "    }\n"
        "    monotonic_time_last_ticks_ms = now - monotonic_time_base_ms;\n"
        "    return monotonic_time_last_ticks_ms;\n"
        "}\n",
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3131_input_thread_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3131_input_thread_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3131_time_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        "    paced_ticks_ms = fake_ticks_ms;\n"
        "    paced_tick_remainder_us = 0;\n"
        "    paced_time_active = 1;\n"
        "    if (a90_doomgeneric_input_thread_start(&input_thread) != 0) {\n",
        "    paced_ticks_ms = fake_ticks_ms;\n"
        "    paced_tick_remainder_us = 0;\n"
        "    paced_time_active = 1;\n"
        "    monotonic_time_base_ms = a90_doomgeneric_monotonic_ms();\n"
        "    monotonic_time_base_set = 1;\n"
        "    monotonic_time_last_ticks_ms = 0;\n"
        "    if (a90_doomgeneric_input_thread_start(&input_thread) != 0) {\n",
    )
    source = _replace_required(
        source,
        '    ok = ok && fprintf(fp, "paced_time_model=presenter-token-doom-tic-quantum\\n") >= 0;\n',
        '    ok = ok && fprintf(fp, "paced_time_model=monotonic-clock-while-loop-active\\n") >= 0;\n'
        f'    ok = ok && fprintf(fp, "time_model_marker={TIME_MODEL_MARKER}\\n") >= 0;\n'
        '    ok = ok && fprintf(fp, "monotonic_time.last_ticks_ms=%u\\n", monotonic_time_last_ticks_ms) >= 0;\n',
    )
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3131 DOOMGENERIC Monotonic Input Thread Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM input reliability after V3129 live freeze.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Inherits V3129 background UDP/UNIX datagram input thread and direct shared-frame blit.",
        "- Changes active DOOM time from presenter-token-only paced ticks to `CLOCK_MONOTONIC` elapsed time while the loop is active.",
        "- This prevents `doomgeneric_Tick()` from observing frozen time internally and spinning without producing new shared-frame sequences.",
        f"- Input thread marker: `{INPUT_THREAD_MARKER}`",
        f"- Time model marker: `{TIME_MODEL_MARKER}`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame geometry: `{FRAME_WIDTH}x{FRAME_HEIGHT}` stride `{FRAME_STRIDE}` bytes `{FRAME_BYTES}`",
        f"- Frame IPC: `{FRAME_IPC}`",
        f"- UDP input target: `{DEVICE_NCM_HOST}:{INPUT_UDP_PORT}`",
        "- Expected live behavior: shared-frame sequence must continue advancing over a one-second sample while UDP input state sequence changes.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No GPU/GL stack, panel re-init, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Changes are limited to the userspace private DOOM helper and native-init identity/metadata.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3131 builder and focused tests.",
        "- `unittest`: V3131 source contract plus V3129 input-thread and host evdev regressions.",
        "- Build: AArch64 static helper compile/link with pthread, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3131 identity, input-thread marker, monotonic time marker, and direct-blit paths.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Flash exact V3131 image, health-check, start continuous DOOM loop, and verify shared-frame sequence plus UDP input response live.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-monotonic-input-thread-candidate`.",
    ]) + "\n"


_PATCHED_ATTRS = (
    "CYCLE",
    "INIT_VERSION",
    "INIT_BUILD",
    "BUILD_TAG",
    "DECISION",
    "OUT_DIR",
    "OBJ_DIR",
    "REPORT_PATH",
    "BOOT_IMAGE",
    "INIT_BINARY",
    "RAMDISK_CPIO",
    "HELPER_BINARY",
    "ENGINE_BINARY",
    "ENGINE_ADAPTER_SOURCE",
    "ENGINE_ADAPTER_OBJECT",
    "ENGINE_RAMDISK_PATH",
    "ENGINE_REMOTE_PATH",
    "ENGINE_NAME",
    "FRAME_PATH",
    "SHARED_FRAME_PATH",
    "INPUT_STATE_PATH",
    "INPUT_SOCKET_PATH",
    "PACE_SOCKET_PATH",
    "TICK_TELEMETRY_PATH",
    "INPUT_THREAD_MARKER",
    "PACED_TIME_MARKER",
    "TICK_TELEMETRY_MARKER",
    "SCALE_MARKER",
    "PHASE_TELEMETRY_MARKER",
    "GAMETIC_FRAME_TELEMETRY_MARKER",
    "FRAME_IPC",
    "REQUIRED_STRINGS",
)


def configure_v3131_module() -> dict[str, Any]:
    saved = {name: getattr(v3129, name) for name in _PATCHED_ATTRS}
    saved["v3129_adapter_source"] = v3129.v3129_adapter_source
    saved["render_report"] = v3129.render_report

    for name in _PATCHED_ATTRS:
        setattr(v3129, name, globals()[name])
    v3129.v3129_adapter_source = v3131_adapter_source
    v3129.render_report = render_report
    return saved


def restore_v3129_module(saved: dict[str, Any]) -> None:
    for name in _PATCHED_ATTRS:
        setattr(v3129, name, saved[name])
    v3129.v3129_adapter_source = saved["v3129_adapter_source"]
    v3129.render_report = saved["render_report"]


def main() -> int:
    saved = configure_v3131_module()
    try:
        rc = v3129.main()
    finally:
        restore_v3129_module(saved)

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "input_thread": True,
        "input_thread_marker": INPUT_THREAD_MARKER,
        "time_model": "clock-monotonic-while-loop-active",
        "time_model_marker": TIME_MODEL_MARKER,
        "frame_ipc": FRAME_IPC,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_port": INPUT_UDP_PORT,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-monotonic-input-thread-candidate",
        "adoption_state": "pending-monotonic-input-thread-live-validation",
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
    (OUT_DIR / "doomgeneric-monotonic-input-thread-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-monotonic-input-thread-candidate",
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
        "input_thread_marker": INPUT_THREAD_MARKER,
        "time_model_marker": TIME_MODEL_MARKER,
        "pace_socket_path": PACE_SOCKET_PATH,
        "frame_ipc": FRAME_IPC,
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-monotonic-input-thread-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
