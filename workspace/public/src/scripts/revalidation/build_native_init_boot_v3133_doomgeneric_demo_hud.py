#!/usr/bin/env python3
"""Build V3133 DOOM demo HUD candidate over the V3131 smooth input stack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3131_doomgeneric_monotonic_input_thread as v3131

REPO_ROOT = repo_root()

CYCLE = "V3133"
INIT_VERSION = "0.10.120"
INIT_BUILD = "v3133-doomgeneric-demo-hud"
BUILD_TAG = INIT_BUILD
DECISION = "v3133-doomgeneric-demo-hud-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3133_DOOMGENERIC_DEMO_HUD_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3133_doomgeneric_demo_hud.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3133_doomgeneric_demo_hud"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3133_doomgeneric_demo_hud.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v526_doomgeneric_demo_hud"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3133"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3133.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3133.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3133"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3133-demo-hud"

FRAME_PATH = "/tmp/a90-doomgeneric-v3133-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3133-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3133-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3133-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3133-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3133-tick-telemetry.txt"

INPUT_THREAD_MARKER = v3131.INPUT_THREAD_MARKER.replace("v3131", "v3133")
TIME_MODEL_MARKER = v3131.TIME_MODEL_MARKER.replace("v3131", "v3133")
DEMO_HUD_MARKER = "a90.doomgeneric.v3133.demo_hud=full-native-cached-metrics-keylog-footer"

RUNTIME_WAD_PATH = v3131.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3131.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3131.FRAME_WIDTH
FRAME_HEIGHT = v3131.FRAME_HEIGHT
FRAME_STRIDE = v3131.FRAME_STRIDE
FRAME_BYTES = v3131.FRAME_BYTES
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-monotonic-input-thread"
INPUT_UDP_PORT = v3131.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3131.DEVICE_NCM_HOST

DASHBOARD_METRICS_INTERVAL_FRAMES = 30
DASHBOARD_STATUS_INTERVAL_FRAMES = 1
NATIVE_DASHBOARD = 1
NATIVE_DASHBOARD_MINIMAL = 0
NATIVE_DASHBOARD_LARGE_FRAME = 0
NATIVE_DEMO_HUD = 1
NATIVE_DEMO_HUD_FAST = 0
NATIVE_DEMO_HUD_READABLE = 0
NATIVE_DEMO_HUD_SECTIONED = 0
NATIVE_DEMO_HUD_LARGE_GROUPS = 0
PRE_SCALED_LARGE_FRAME = 0
FRAME_SCALE = "1:1-demo-hud"
SCALE_PATH = "producer-960x600-raw-rowcopy-demo-hud"

PACED_TIME_MARKER = v3131.PACED_TIME_MARKER.replace("v3131", "v3133")
TICK_TELEMETRY_MARKER = v3131.TICK_TELEMETRY_MARKER.replace("v3131", "v3133")
SCALE_MARKER = "a90.doomgeneric.v3133.scale=producer-960x600-1to1-demo-hud"
PHASE_TELEMETRY_MARKER = v3131.PHASE_TELEMETRY_MARKER.replace("v3131", "v3133")
GAMETIC_FRAME_TELEMETRY_MARKER = v3131.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3131", "v3133")

_V3131_ADAPTER_SOURCE = v3131.v3131_adapter_source
_BASE_APPLY_V3126_GLOBALS = v3131.v3129.v3126.apply_v3126_globals


def rel(path: Path) -> str:
    return v3131.rel(path)


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3133 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3131.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3131.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3131.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3131.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3131.SCALE_MARKER.encode("ascii"): SCALE_MARKER.encode("ascii"),
        b"a90-doomgeneric-v3131": b"a90-doomgeneric-v3133",
        b"a90.doomgeneric.v3131": b"a90.doomgeneric.v3133",
        b"v3131": b"v3133",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_DROPPED_INHERITED_MARKERS = (
    b"video.demo.doom.dashboard.pre_scaled_large_frame=1",
    b"video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
    b"video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
    b"video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
)

REQUIRED_STRINGS = tuple(
    item
    for item in (_rewrite_required_string(item) for item in v3131.REQUIRED_STRINGS)
    if item not in _DROPPED_INHERITED_MARKERS
) + (
    DEMO_HUD_MARKER.encode("ascii"),
    b"video.demo.doom.dashboard.profile=demo-hud-full",
    b"video.demo.doom.dashboard.footer=physical-key-exit-and-copyright",
    b"video.demo.doom.dashboard.metrics_pacing=cached-frame-interval",
    b"video.demo.doom.dashboard.frame_mode=standard-dashboard",
    b"video.demo.doom.dashboard.frame_scale=1:1",
    b"HOST host_doompad_keyboard_v3033.py UDP EVDEV",
    b"POWER VOL EXIT   HOST KEYS VIA USB NCM",
)


def v3133_adapter_source() -> str:
    source = _V3131_ADAPTER_SOURCE()
    replacements = {
        "v3131": "v3133",
        "V3131": "V3133",
        v3131.FRAME_PATH: FRAME_PATH,
        v3131.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3131.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3131.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3131.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
        v3131.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3131.INPUT_THREAD_MARKER: INPUT_THREAD_MARKER,
        v3131.TIME_MODEL_MARKER: TIME_MODEL_MARKER,
        v3131.PACED_TIME_MARKER: PACED_TIME_MARKER,
        v3131.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3131.SCALE_MARKER: SCALE_MARKER,
        v3131.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3131.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3133_time_policy[] =\n'
        f'    "{TIME_MODEL_MARKER}";\n',
        'const char a90_doomgeneric_v3133_time_policy[] =\n'
        f'    "{TIME_MODEL_MARKER}";\n'
        'const char a90_doomgeneric_v3133_demo_hud_policy[] =\n'
        f'    "{DEMO_HUD_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3133_input_thread_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3133_time_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3133_input_thread_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3133_time_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3133_demo_hud_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        f'    ok = ok && fprintf(fp, "time_model_marker={TIME_MODEL_MARKER}\\n") >= 0;\n',
        f'    ok = ok && fprintf(fp, "time_model_marker={TIME_MODEL_MARKER}\\n") >= 0;\n'
        f'    ok = ok && fprintf(fp, "demo_hud_marker={DEMO_HUD_MARKER}\\n") >= 0;\n',
    )
    return source


def dashboard_attr_modules() -> tuple[Any, ...]:
    v3126 = v3131.v3129.v3126
    v3123 = v3126.v3123
    v3120 = v3123.v3120
    v3118 = v3120.v3118
    v3116 = v3118.v3116
    v3114 = v3116.v3114
    v3112 = v3114.v3112
    v3108 = v3112.v3108
    v3100 = v3108.v3100
    v3098 = v3100.v3098
    v3096 = v3098.v3096
    v3086 = v3096.v3086
    v3084 = v3086.v3084
    v3083 = v3084.v3083
    v3081 = v3083.v3081
    v3079 = v3081.v3079
    v3077 = v3079.v3077
    v3074 = v3077.v3074
    v3071 = v3074.v3071
    v3069 = v3071.v3069
    return (
        v3126,
        v3123,
        v3120,
        v3118,
        v3116,
        v3114,
        v3112,
        v3108,
        v3100,
        v3098,
        v3096,
        v3086,
        v3084,
        v3083,
        v3081,
        v3079,
        v3077,
        v3074,
        v3071,
        v3069,
        v3131.v3129.v3126.v3123.v3120.v3118.v3116.v3033_module(),
    )


_DASHBOARD_ATTRS = (
    "NATIVE_DASHBOARD",
    "NATIVE_DASHBOARD_MINIMAL",
    "NATIVE_DASHBOARD_LARGE_FRAME",
    "NATIVE_DEMO_HUD",
    "NATIVE_DEMO_HUD_FAST",
    "NATIVE_DEMO_HUD_READABLE",
    "NATIVE_DEMO_HUD_SECTIONED",
    "NATIVE_DEMO_HUD_LARGE_GROUPS",
    "DASHBOARD_METRICS_INTERVAL_FRAMES",
    "DASHBOARD_STATUS_INTERVAL_FRAMES",
    "PRE_SCALED_LARGE_FRAME",
    "FRAME_SCALE",
    "SCALE_PATH",
)


def save_dashboard_attrs() -> list[tuple[Any, str, Any]]:
    saved: list[tuple[Any, str, Any]] = []
    for module in dashboard_attr_modules():
        for name in _DASHBOARD_ATTRS:
            if hasattr(module, name):
                saved.append((module, name, getattr(module, name)))
    return saved


def restore_dashboard_attrs(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in saved:
        setattr(module, name, value)


def set_demo_dashboard_chain_globals() -> None:
    for module in dashboard_attr_modules():
        if hasattr(module, "NATIVE_DASHBOARD"):
            setattr(module, "NATIVE_DASHBOARD", NATIVE_DASHBOARD)
        if hasattr(module, "NATIVE_DASHBOARD_MINIMAL"):
            setattr(module, "NATIVE_DASHBOARD_MINIMAL", NATIVE_DASHBOARD_MINIMAL)
        if hasattr(module, "NATIVE_DASHBOARD_LARGE_FRAME"):
            setattr(module, "NATIVE_DASHBOARD_LARGE_FRAME", NATIVE_DASHBOARD_LARGE_FRAME)
        if hasattr(module, "NATIVE_DEMO_HUD"):
            setattr(module, "NATIVE_DEMO_HUD", NATIVE_DEMO_HUD)
        if hasattr(module, "NATIVE_DEMO_HUD_FAST"):
            setattr(module, "NATIVE_DEMO_HUD_FAST", NATIVE_DEMO_HUD_FAST)
        if hasattr(module, "NATIVE_DEMO_HUD_READABLE"):
            setattr(module, "NATIVE_DEMO_HUD_READABLE", NATIVE_DEMO_HUD_READABLE)
        if hasattr(module, "NATIVE_DEMO_HUD_SECTIONED"):
            setattr(module, "NATIVE_DEMO_HUD_SECTIONED", NATIVE_DEMO_HUD_SECTIONED)
        if hasattr(module, "NATIVE_DEMO_HUD_LARGE_GROUPS"):
            setattr(module, "NATIVE_DEMO_HUD_LARGE_GROUPS", NATIVE_DEMO_HUD_LARGE_GROUPS)
        if hasattr(module, "DASHBOARD_METRICS_INTERVAL_FRAMES"):
            setattr(module, "DASHBOARD_METRICS_INTERVAL_FRAMES", DASHBOARD_METRICS_INTERVAL_FRAMES)
        if hasattr(module, "DASHBOARD_STATUS_INTERVAL_FRAMES"):
            setattr(module, "DASHBOARD_STATUS_INTERVAL_FRAMES", DASHBOARD_STATUS_INTERVAL_FRAMES)
        if hasattr(module, "PRE_SCALED_LARGE_FRAME"):
            setattr(module, "PRE_SCALED_LARGE_FRAME", PRE_SCALED_LARGE_FRAME)
        if hasattr(module, "FRAME_SCALE"):
            setattr(module, "FRAME_SCALE", FRAME_SCALE)
        if hasattr(module, "SCALE_PATH"):
            setattr(module, "SCALE_PATH", SCALE_PATH)

    v3096 = v3131.v3129.v3126.v3123.v3120.v3118.v3116.v3114.v3112.v3108.v3100.v3098.v3096
    if hasattr(v3096, "_set_large_frame"):
        v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)


def apply_v3133_dashboard_globals() -> None:
    set_demo_dashboard_chain_globals()
    _BASE_APPLY_V3126_GLOBALS()
    set_demo_dashboard_chain_globals()
    v3033 = v3131.v3129.v3126.v3123.v3120.v3118.v3116.v3033_module()
    v3033.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3033.NATIVE_DASHBOARD_MINIMAL = NATIVE_DASHBOARD_MINIMAL
    v3033.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3033.NATIVE_DEMO_HUD = NATIVE_DEMO_HUD
    v3033.NATIVE_DEMO_HUD_FAST = NATIVE_DEMO_HUD_FAST
    v3033.NATIVE_DEMO_HUD_READABLE = NATIVE_DEMO_HUD_READABLE
    v3033.NATIVE_DEMO_HUD_SECTIONED = NATIVE_DEMO_HUD_SECTIONED
    v3033.NATIVE_DEMO_HUD_LARGE_GROUPS = NATIVE_DEMO_HUD_LARGE_GROUPS
    v3033.DASHBOARD_METRICS_INTERVAL_FRAMES = DASHBOARD_METRICS_INTERVAL_FRAMES
    v3033.DASHBOARD_STATUS_INTERVAL_FRAMES = DASHBOARD_STATUS_INTERVAL_FRAMES
    v3033.PRE_SCALED_LARGE_FRAME = PRE_SCALED_LARGE_FRAME
    v3033.FRAME_WIDTH = FRAME_WIDTH
    v3033.FRAME_HEIGHT = FRAME_HEIGHT
    v3033.FRAME_STRIDE = FRAME_STRIDE
    v3033.FRAME_BYTES = FRAME_BYTES
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3033.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3033.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3033.PACE_SOCKET_PATH = PACE_SOCKET_PATH


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3133 DOOMGENERIC Demo HUD Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM native demo presentation over the V3131 smooth input stack.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Inherits V3131 monotonic active DOOM time, background UDP/UNIX datagram input thread, and direct shared-frame blit.",
        "- Enables the native full dashboard instead of the minimal fastdraw HUD, but keeps the 960x600 pre-scaled DOOM frame at 1:1 so it fits the 1080px panel width.",
        f"- Caches hardware metrics every `{DASHBOARD_METRICS_INTERVAL_FRAMES}` frames, avoiding per-frame sysfs reads.",
        "- Adds a footer line for physical-key exit guidance, USB/NCM keyboard input, WAD status, and attribution text.",
        f"- Demo HUD marker: `{DEMO_HUD_MARKER}`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame geometry: `{FRAME_WIDTH}x{FRAME_HEIGHT}` stride `{FRAME_STRIDE}` bytes `{FRAME_BYTES}`",
        f"- Frame IPC: `{FRAME_IPC}`",
        f"- UDP input target: `{DEVICE_NCM_HOST}:{INPUT_UDP_PORT}`",
        f"- Native dashboard minimal: `{NATIVE_DASHBOARD_MINIMAL}`",
        f"- Native dashboard large-frame overlay: `{NATIVE_DASHBOARD_LARGE_FRAME}`",
        f"- Dashboard metrics interval frames: `{DASHBOARD_METRICS_INTERVAL_FRAMES}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No GPU/GL stack, panel re-init, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Changes are limited to userspace native-init draw flags/strings plus the private DOOM helper identity marker.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3133 builder and focused tests.",
        "- `unittest`: V3133 source contract plus V3131/V3129 and host evdev regressions.",
        "- Build: AArch64 static helper compile/link with pthread, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3133 identity, input-thread marker, monotonic time marker, demo-HUD marker, and native dashboard profile/footer strings.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Flash exact V3133 image, health-check, start continuous DOOM loop, and verify frame sequence plus visible native HUD markers.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-demo-hud-candidate`.",
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
    "TIME_MODEL_MARKER",
    "PACED_TIME_MARKER",
    "TICK_TELEMETRY_MARKER",
    "SCALE_MARKER",
    "PHASE_TELEMETRY_MARKER",
    "GAMETIC_FRAME_TELEMETRY_MARKER",
    "FRAME_IPC",
    "REQUIRED_STRINGS",
)


def configure_v3133_module() -> dict[str, Any]:
    saved = {name: getattr(v3131, name) for name in _PATCHED_ATTRS}
    saved["v3131_adapter_source"] = v3131.v3131_adapter_source
    saved["render_report"] = v3131.render_report
    saved["apply_v3126_globals"] = v3131.v3129.v3126.apply_v3126_globals
    saved["dashboard_attrs"] = save_dashboard_attrs()

    for name in _PATCHED_ATTRS:
        setattr(v3131, name, globals()[name])
    v3131.v3131_adapter_source = v3133_adapter_source
    v3131.render_report = render_report
    v3131.v3129.v3126.apply_v3126_globals = apply_v3133_dashboard_globals
    return saved


def restore_v3131_module(saved: dict[str, Any]) -> None:
    for name in _PATCHED_ATTRS:
        setattr(v3131, name, saved[name])
    v3131.v3131_adapter_source = saved["v3131_adapter_source"]
    v3131.render_report = saved["render_report"]
    v3131.v3129.v3126.apply_v3126_globals = saved["apply_v3126_globals"]
    restore_dashboard_attrs(saved["dashboard_attrs"])


def main() -> int:
    saved = configure_v3133_module()
    try:
        rc = v3131.main()
    finally:
        restore_v3131_module(saved)

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "input_thread": True,
        "input_thread_marker": INPUT_THREAD_MARKER,
        "time_model": "clock-monotonic-while-loop-active",
        "time_model_marker": TIME_MODEL_MARKER,
        "demo_hud": True,
        "demo_hud_marker": DEMO_HUD_MARKER,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_demo_hud": bool(NATIVE_DEMO_HUD),
        "dashboard_metrics_interval_frames": DASHBOARD_METRICS_INTERVAL_FRAMES,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "frame_ipc": FRAME_IPC,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_port": INPUT_UDP_PORT,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-demo-hud-candidate",
        "adoption_state": "pending-demo-hud-live-validation",
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
    (OUT_DIR / "doomgeneric-demo-hud-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-demo-hud-candidate",
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
        "demo_hud_marker": DEMO_HUD_MARKER,
        "dashboard_metrics_interval_frames": DASHBOARD_METRICS_INTERVAL_FRAMES,
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "pace_socket_path": PACE_SOCKET_PATH,
        "frame_ipc": FRAME_IPC,
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-demo-hud-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
