#!/usr/bin/env python3
"""Build V3069 native-init DOOM dashboard metrics-cache candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3067_doomgeneric_reader_reuse as v3067
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3069"
INIT_VERSION = "0.10.92"
INIT_BUILD = "v3069-doomgeneric-metrics-cache"
BUILD_TAG = INIT_BUILD
DECISION = "v3069-doomgeneric-metrics-cache-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3069_DOOMGENERIC_METRICS_CACHE_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3069_doomgeneric_metrics_cache.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3069_doomgeneric_metrics_cache"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3069_doomgeneric_metrics_cache.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_metrics_cache"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3069"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3069.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3069.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3069"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3069-metrics-cache"

RUNTIME_WAD_ROOT = v3067.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3067.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3067.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3067.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3067.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3067.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3067.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3067.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3067.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3067.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3067.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3069-metrics-cache-frame.xbgr8888"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3069-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3069-input.sock"
INPUT_UDP_PORT = v3067.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3067.DEVICE_NCM_HOST
FRAME_WIDTH = v3067.FRAME_WIDTH
FRAME_HEIGHT = v3067.FRAME_HEIGHT
FRAME_STRIDE = v3067.FRAME_STRIDE
FRAME_BYTES = v3067.FRAME_BYTES
NATIVE_DASHBOARD = v3067.NATIVE_DASHBOARD
NATIVE_DASHBOARD_LARGE_FRAME = v3067.NATIVE_DASHBOARD_LARGE_FRAME
REUSE_FRAME_BUFFER = v3067.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = 30
BASELINE_DASHBOARD_METRICS_INTERVAL_FRAMES = 1

SOUND_MODE = v3067.SOUND_MODE
AUDIO_CORUN = v3067.AUDIO_CORUN
AUDIO_CORUN_MODE = v3067.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3067.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3067.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3067.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3067.HOST_DASHBOARD

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.92 (v3069-doomgeneric-metrics-cache)",
    b"v3069-doomgeneric-metrics-cache",
    b"doomgeneric-private-link-v3069-metrics-cache",
    b"/bin/a90_doomgeneric_private_engine_v3069",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"--input-udp",
    b"udp-ncm-to-DG_GetKey-with-serial-doompad-fallback",
    b"video.demo.doom.loop.frame_ms=",
    b"video.demo.doom.presenter.pacing=helper-frame-mtime",
    b"video.demo.doom.presenter.reader=reused-loop-buffer",
    b"video.demo.doom.presenter.buffer_reuse=1",
    b"video.demo.doom.dashboard.metrics_interval_frames=",
    b"video.demo.doom.dashboard.metrics_pacing=cached-frame-interval",
    b"video.demo.doom.dashboard.native=1",
    b"video.demo.doom.dashboard.large_frame=0",
    b"video.demo.doom.dashboard.frame_scale=1:1",
    b"video.demo.input.udp_port=",
    b"video.demo.input.socket_path=",
    b"video.demo.input.otg_required=0",
    b"doompad.batch=state-mask-v3047",
    b"video.demo.doom.loop_start.continuous",
    b"native-audio-corun-tone-v3053",
    b"host_doompad_keyboard_v3033.py",
)


def rel(path: Path) -> str:
    return v3067.rel(path)


def v3033_module() -> Any:
    return v3067.v3033_module()


def apply_v3069_globals() -> None:
    v3033 = v3033_module()
    v3067.CYCLE = CYCLE
    v3067.INIT_VERSION = INIT_VERSION
    v3067.INIT_BUILD = INIT_BUILD
    v3067.BUILD_TAG = BUILD_TAG
    v3067.DECISION = DECISION
    v3067.OUT_DIR = OUT_DIR
    v3067.OBJ_DIR = OBJ_DIR
    v3067.REPORT_PATH = REPORT_PATH
    v3067.BOOT_IMAGE = BOOT_IMAGE
    v3067.INIT_BINARY = INIT_BINARY
    v3067.RAMDISK_CPIO = RAMDISK_CPIO
    v3067.HELPER_BINARY = HELPER_BINARY
    v3067.ENGINE_BINARY = ENGINE_BINARY
    v3067.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3067.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3067.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3067.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3067.ENGINE_NAME = ENGINE_NAME
    v3067.DEFAULT_LOOP_FRAMES = DEFAULT_LOOP_FRAMES
    v3067.LOOP_FRAME_MS = LOOP_FRAME_MS
    v3067.PRESENTER_POLL_MS = PRESENTER_POLL_MS
    v3067.FRAME_PATH = FRAME_PATH
    v3067.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3067.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3067.INPUT_UDP_PORT = INPUT_UDP_PORT
    v3067.DEVICE_NCM_HOST = DEVICE_NCM_HOST
    v3067.NATIVE_DASHBOARD = NATIVE_DASHBOARD
    v3067.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3067.SOUND_MODE = SOUND_MODE
    v3067.AUDIO_CORUN = AUDIO_CORUN
    v3067.AUDIO_CORUN_MODE = AUDIO_CORUN_MODE
    v3067.AUDIO_CORUN_DURATION_MS = AUDIO_CORUN_DURATION_MS
    v3067.AUDIO_CORUN_AMPLITUDE_MILLI = AUDIO_CORUN_AMPLITUDE_MILLI
    v3067.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3067.render_report = render_report
    v3033.REUSE_FRAME_BUFFER = REUSE_FRAME_BUFFER
    v3033.DASHBOARD_METRICS_INTERVAL_FRAMES = DASHBOARD_METRICS_INTERVAL_FRAMES


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3069 DOOMGENERIC Metrics Cache Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone frame pacing.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3067 reader-buffer reuse, V3065 large-scale-off, V3063 frame_ms=28, and UDP/NCM input unchanged.",
        "- Changes native DOOM dashboard metrics from per-frame sysfs reads to cached reads every 30 presented frames.",
        "- This targets the V3068 stack finding where presenter blocked in `wsa881x_get_temp` through thermal sysfs.",
        "",
        "## Metrics Contract",
        "",
        f"- Baseline metrics interval frames: `{BASELINE_DASHBOARD_METRICS_INTERVAL_FRAMES}`",
        f"- Candidate metrics interval frames: `{DASHBOARD_METRICS_INTERVAL_FRAMES}`",
        "- Metrics pacing marker: `cached-frame-interval`",
        f"- Reader reuse: `{REUSE_FRAME_BUFFER}`",
        f"- Helper frame ms: `{doom.get('loop_frame_ms', LOOP_FRAME_MS)}`",
        f"- Presenter poll ms: `{doom.get('presenter_poll_ms', PRESENTER_POLL_MS)}`",
        f"- Dashboard large frame: `{int(bool(NATIVE_DASHBOARD_LARGE_FRAME))}`",
        f"- Frame path: `{doom.get('frame_path')}`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3069 builder and focused tests.",
        "- `unittest`: V3069 source contract plus V3067/V3065/V3063/V3061/V3059 and base visible-loop regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3069 identity, reader reuse, dashboard metrics cache, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3070`",
        "- Type: rollback-gated live validation of V3069 metrics-cache candidate.",
        "- Scope: flash exact V3069 boot image via `native_init_flash.py`, health-check, require `video.demo.doom.dashboard.metrics_pacing=cached-frame-interval`, start continuous DOOM loop, and sample presenter state/stack after metrics throttling.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-metrics-cache-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3069_globals()
    rc = v3067.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "dashboard_metrics_interval_frames": DASHBOARD_METRICS_INTERVAL_FRAMES,
        "baseline_dashboard_metrics_interval_frames": BASELINE_DASHBOARD_METRICS_INTERVAL_FRAMES,
        "dashboard_metrics_pacing": "cached-frame-interval",
        "metrics_cache_experiment": {
            "per_frame_sysfs_metrics_removed": True,
            "target_finding": "presenter-blocked-in-wsa881x_get_temp-via-thermal-sysfs",
            "input_pacing_scaling_and_reader_unchanged_from_v3067": True,
        },
        "helper_loop_command": (
            f"{ENGINE_REMOTE_PATH} --wad-frame-loop {RUNTIME_WAD_PATH} "
            f"--frames {DEFAULT_LOOP_FRAMES} --output {FRAME_PATH} "
            f"--input-state {INPUT_STATE_PATH} --frame-ms {LOOP_FRAME_MS} "
            f"--input-socket {INPUT_SOCKET_PATH} --input-udp {INPUT_UDP_PORT}"
        ),
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-metrics-cache-candidate",
        "adoption_state": "pending-metrics-cache-live-validation",
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
    (OUT_DIR / "doomgeneric-metrics-cache-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-metrics-cache-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "engine_binary": rel(ENGINE_BINARY),
        "engine_ramdisk_path": ENGINE_REMOTE_PATH,
        "runtime_wad_path": RUNTIME_WAD_PATH,
        "expected_wad_sha256": EXPECTED_WAD_SHA256,
        "frame_path": FRAME_PATH,
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "presenter_reader": "reused-loop-buffer",
        "dashboard_metrics_interval_frames": DASHBOARD_METRICS_INTERVAL_FRAMES,
        "dashboard_metrics_pacing": "cached-frame-interval",
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "frame_scale": "1:1",
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-metrics-cache-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
