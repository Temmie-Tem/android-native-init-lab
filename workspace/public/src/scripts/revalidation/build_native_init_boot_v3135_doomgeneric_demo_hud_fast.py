#!/usr/bin/env python3
"""Build V3135 DOOM compact demo HUD over the V3133/V3131 smooth stack."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3133_doomgeneric_demo_hud as v3133

REPO_ROOT = repo_root()

CYCLE = "V3135"
INIT_VERSION = "0.10.121"
INIT_BUILD = "v3135-doomgeneric-demo-hud-fast"
BUILD_TAG = INIT_BUILD
DECISION = "v3135-doomgeneric-demo-hud-fast-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3135_DOOMGENERIC_DEMO_HUD_FAST_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3135_doomgeneric_demo_hud_fast.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3135_doomgeneric_demo_hud_fast"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3135_doomgeneric_demo_hud_fast.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v527_doomgeneric_demo_hud_fast"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3135"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3135.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3135.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3135"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3135-demo-hud-fast"

FRAME_PATH = "/tmp/a90-doomgeneric-v3135-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3135-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3135-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3135-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3135-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3135-tick-telemetry.txt"

INPUT_THREAD_MARKER = v3133.INPUT_THREAD_MARKER.replace("v3133", "v3135")
TIME_MODEL_MARKER = v3133.TIME_MODEL_MARKER.replace("v3133", "v3135")
DEMO_HUD_MARKER = "a90.doomgeneric.v3135.demo_hud=fast-native-cached-compact-targeted"

RUNTIME_WAD_PATH = v3133.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3133.EXPECTED_WAD_SHA256
FRAME_WIDTH = v3133.FRAME_WIDTH
FRAME_HEIGHT = v3133.FRAME_HEIGHT
FRAME_STRIDE = v3133.FRAME_STRIDE
FRAME_BYTES = v3133.FRAME_BYTES
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-fast-monotonic-input-thread"
INPUT_UDP_PORT = v3133.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3133.DEVICE_NCM_HOST

DASHBOARD_METRICS_INTERVAL_FRAMES = 1800
DASHBOARD_STATUS_INTERVAL_FRAMES = 300
NATIVE_DASHBOARD = 1
NATIVE_DASHBOARD_MINIMAL = 0
NATIVE_DASHBOARD_LARGE_FRAME = 0
NATIVE_DEMO_HUD = 1
NATIVE_DEMO_HUD_FAST = 1
NATIVE_DEMO_HUD_READABLE = 0
NATIVE_DEMO_HUD_SECTIONED = 0
NATIVE_DEMO_HUD_LARGE_GROUPS = 0
PRE_SCALED_LARGE_FRAME = 0
FRAME_SCALE = "1:1-demo-hud-fast"
SCALE_PATH = "producer-960x600-raw-rowcopy-demo-hud-fast"

PACED_TIME_MARKER = v3133.PACED_TIME_MARKER.replace("v3133", "v3135")
TICK_TELEMETRY_MARKER = v3133.TICK_TELEMETRY_MARKER.replace("v3133", "v3135")
SCALE_MARKER = "a90.doomgeneric.v3135.scale=producer-960x600-1to1-demo-hud-fast"
PHASE_TELEMETRY_MARKER = v3133.PHASE_TELEMETRY_MARKER.replace("v3133", "v3135")
GAMETIC_FRAME_TELEMETRY_MARKER = v3133.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3133", "v3135")

_V3131_ADAPTER_SOURCE = v3133.v3131.v3131_adapter_source


def rel(path: Path) -> str:
    return v3133.rel(path)


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3135 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        v3133.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        v3133.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        v3133.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        v3133.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        v3133.DEMO_HUD_MARKER.encode("ascii"): DEMO_HUD_MARKER.encode("ascii"),
        b"a90-doomgeneric-v3133": b"a90-doomgeneric-v3135",
        b"a90.doomgeneric.v3133": b"a90.doomgeneric.v3135",
        b"v3133": b"v3135",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_DROPPED_INHERITED_MARKERS = (
    b"video.demo.doom.dashboard.profile=demo-hud-full",
    b"video.demo.doom.dashboard.frame_mode=standard-dashboard",
    b"video.demo.doom.dashboard.clear_path=dirty-dashboard-regions",
)

REQUIRED_STRINGS = tuple(
    item
    for item in (_rewrite_required_string(item) for item in v3133.REQUIRED_STRINGS)
    if item not in _DROPPED_INHERITED_MARKERS
) + (
    DEMO_HUD_MARKER.encode("ascii"),
    b"video.demo.doom.dashboard.profile=demo-hud-fast",
    b"video.demo.doom.dashboard.layout=top-frame-compact-metrics-input-footer",
    b"video.demo.doom.dashboard.redraw=doom-frame-plus-targeted-compact-hud",
    b"video.demo.doom.dashboard.frame_mode=demo-hud-fast-1to1",
    b"video.demo.doom.dashboard.status_interval_frames=",
    b"video.demo.doom.dashboard.status_pacing=cached-frame-interval",
    b"video.demo.doom.dashboard.clear_path=targeted-demo-hud-regions",
    b"compact cached HUD",
)


def v3135_adapter_source() -> str:
    source = _V3131_ADAPTER_SOURCE()
    replacements = {
        "v3131": "v3135",
        "V3131": "V3135",
        v3133.v3131.FRAME_PATH: FRAME_PATH,
        v3133.v3131.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3133.v3131.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3133.v3131.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3133.v3131.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
        v3133.v3131.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3133.v3131.INPUT_THREAD_MARKER: INPUT_THREAD_MARKER,
        v3133.v3131.TIME_MODEL_MARKER: TIME_MODEL_MARKER,
        v3133.v3131.PACED_TIME_MARKER: PACED_TIME_MARKER,
        v3133.v3131.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3133.v3131.SCALE_MARKER: SCALE_MARKER,
        v3133.v3131.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3133.v3131.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)

    source = _replace_required(
        source,
        'const char a90_doomgeneric_v3135_time_policy[] =\n'
        f'    "{TIME_MODEL_MARKER}";\n',
        'const char a90_doomgeneric_v3135_time_policy[] =\n'
        f'    "{TIME_MODEL_MARKER}";\n'
        'const char a90_doomgeneric_v3135_demo_hud_policy[] =\n'
        f'    "{DEMO_HUD_MARKER}";\n',
    )
    source = _replace_required(
        source,
        "        marker_checksum(a90_doomgeneric_v3135_input_thread_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3135_time_policy) == 0U) {\n",
        "        marker_checksum(a90_doomgeneric_v3135_input_thread_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3135_time_policy) == 0U ||\n"
        "        marker_checksum(a90_doomgeneric_v3135_demo_hud_policy) == 0U) {\n",
    )
    source = _replace_required(
        source,
        f'    ok = ok && fprintf(fp, "time_model_marker={TIME_MODEL_MARKER}\\n") >= 0;\n',
        f'    ok = ok && fprintf(fp, "time_model_marker={TIME_MODEL_MARKER}\\n") >= 0;\n'
        f'    ok = ok && fprintf(fp, "demo_hud_marker={DEMO_HUD_MARKER}\\n") >= 0;\n',
    )
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3135 DOOMGENERIC Fast Demo HUD Source Build",
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
        "- Inherits V3133's UDP/NCM evdev input, monotonic active DOOM time, and direct shared-frame blit.",
        "- Replaces the full native HUD panels with a compact cached demo HUD: title, 960x600 DOOM frame, short hardware/DOOM/input strip, recent key log, and footer.",
        f"- Updates expensive hardware metrics every `{DASHBOARD_METRICS_INTERVAL_FRAMES}` frames instead of every `30` frames.",
        f"- Caches bridge status every `{DASHBOARD_STATUS_INTERVAL_FRAMES}` frames instead of re-statting helper/WAD state every frame.",
        "- Uses targeted dashboard-region redraw after the first frame, keeping the DOOM frame path unchanged.",
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
        f"- Dashboard metrics interval frames: `{DASHBOARD_METRICS_INTERVAL_FRAMES}`",
        f"- Dashboard status interval frames: `{DASHBOARD_STATUS_INTERVAL_FRAMES}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- No GPU/GL stack, panel re-init, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Changes are limited to userspace native-init draw flags/strings plus the private DOOM helper identity marker.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3135 builder and focused tests.",
        "- `unittest`: V3135 source contract plus V3133/V3131 and host evdev regressions.",
        "- Build: AArch64 static helper compile/link with pthread, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3135 identity, input-thread marker, monotonic time marker, fast demo-HUD marker, and compact HUD profile strings.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Flash exact V3135 image, health-check, run bounded 240-frame DOOM loop, and compare timing against V3133 full HUD.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-demo-hud-fast-candidate`.",
    ]) + "\n"


_PATCHED_V3133_ATTRS = (
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
    "DEMO_HUD_MARKER",
    "PACED_TIME_MARKER",
    "TICK_TELEMETRY_MARKER",
    "SCALE_MARKER",
    "PHASE_TELEMETRY_MARKER",
    "GAMETIC_FRAME_TELEMETRY_MARKER",
    "FRAME_IPC",
    "REQUIRED_STRINGS",
    "DASHBOARD_METRICS_INTERVAL_FRAMES",
    "DASHBOARD_STATUS_INTERVAL_FRAMES",
    "NATIVE_DASHBOARD",
    "NATIVE_DASHBOARD_MINIMAL",
    "NATIVE_DASHBOARD_LARGE_FRAME",
    "NATIVE_DEMO_HUD",
    "NATIVE_DEMO_HUD_FAST",
    "NATIVE_DEMO_HUD_READABLE",
    "NATIVE_DEMO_HUD_SECTIONED",
    "NATIVE_DEMO_HUD_LARGE_GROUPS",
    "PRE_SCALED_LARGE_FRAME",
    "FRAME_SCALE",
    "SCALE_PATH",
)


def configure_v3135_module() -> dict[str, Any]:
    saved = {name: getattr(v3133, name) for name in _PATCHED_V3133_ATTRS}
    saved["v3133_adapter_source"] = v3133.v3133_adapter_source
    saved["render_report"] = v3133.render_report
    for name in _PATCHED_V3133_ATTRS:
        setattr(v3133, name, globals()[name])
    v3133.v3133_adapter_source = v3135_adapter_source
    v3133.render_report = render_report
    return saved


def restore_v3133_module(saved: dict[str, Any]) -> None:
    for name in _PATCHED_V3133_ATTRS:
        setattr(v3133, name, saved[name])
    v3133.v3133_adapter_source = saved["v3133_adapter_source"]
    v3133.render_report = saved["render_report"]


def main() -> int:
    saved = configure_v3135_module()
    try:
        rc = v3133.main()
    finally:
        restore_v3133_module(saved)

    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "demo_hud_fast": True,
        "demo_hud_marker": DEMO_HUD_MARKER,
        "native_demo_hud_fast": bool(NATIVE_DEMO_HUD_FAST),
        "dashboard_metrics_interval_frames": DASHBOARD_METRICS_INTERVAL_FRAMES,
        "dashboard_status_interval_frames": DASHBOARD_STATUS_INTERVAL_FRAMES,
        "dashboard_clear_path": "targeted-demo-hud-regions",
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "frame_ipc": FRAME_IPC,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_port": INPUT_UDP_PORT,
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-demo-hud-fast-candidate",
        "adoption_state": "pending-demo-hud-fast-live-validation",
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
    (OUT_DIR / "doomgeneric-demo-hud-fast-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-demo-hud-fast-candidate",
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
        "dashboard_status_interval_frames": DASHBOARD_STATUS_INTERVAL_FRAMES,
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_demo_hud_fast": bool(NATIVE_DEMO_HUD_FAST),
        "pace_socket_path": PACE_SOCKET_PATH,
        "frame_ipc": FRAME_IPC,
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-demo-hud-fast-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
