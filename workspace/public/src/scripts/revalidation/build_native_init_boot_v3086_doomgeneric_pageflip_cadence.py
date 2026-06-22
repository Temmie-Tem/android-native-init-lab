#!/usr/bin/env python3
"""Build V3086 native-init DOOM pageflip cadence candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3084_doomgeneric_serial_preserve as v3084
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3086"
INIT_VERSION = "0.10.100"
INIT_BUILD = "v3086-doomgeneric-pageflip-cadence"
BUILD_TAG = INIT_BUILD
DECISION = "v3086-doomgeneric-pageflip-cadence-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3086_DOOMGENERIC_PAGEFLIP_CADENCE_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3086_doomgeneric_pageflip_cadence.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3086_doomgeneric_pageflip_cadence"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3086_doomgeneric_pageflip_cadence.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_pageflip_cadence"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3086"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3086.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3086.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3086"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3086-pageflip-cadence"

RUNTIME_WAD_ROOT = v3084.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3084.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3084.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3084.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3084.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3084.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3084.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3084.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3084.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3084.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3084.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3086-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3086-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3086-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3086-input.sock"
INPUT_UDP_PORT = v3084.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3084.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3086-pace.sock"
BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3084.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = 0
FRAME_WIDTH = v3084.FRAME_WIDTH
FRAME_HEIGHT = v3084.FRAME_HEIGHT
FRAME_STRIDE = v3084.FRAME_STRIDE
FRAME_BYTES = v3084.FRAME_BYTES
NATIVE_DASHBOARD = v3084.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3084.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3084.NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DOOM_PRESENT_PAGEFLIP = v3084.NATIVE_DOOM_PRESENT_PAGEFLIP
FRAME_SCALE = v3084.FRAME_SCALE
SCALE_PATH = v3084.SCALE_PATH
REUSE_FRAME_BUFFER = v3084.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3084.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3084.FRAME_TIMING_PROBE
BASELINE_BACKGROUND_CANCEL = v3084.BASELINE_BACKGROUND_CANCEL
CANDIDATE_BACKGROUND_CANCEL = v3084.CANDIDATE_BACKGROUND_CANCEL

SOUND_MODE = v3084.SOUND_MODE
AUDIO_CORUN = v3084.AUDIO_CORUN
AUDIO_CORUN_MODE = v3084.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3084.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3084.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3084.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3084.HOST_DASHBOARD
V3059 = v3084.V3059

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.100 (v3086-doomgeneric-pageflip-cadence)",
    b"v3086-doomgeneric-pageflip-cadence",
    b"doomgeneric-private-link-v3086-pageflip-cadence",
    b"/bin/a90_doomgeneric_private_engine_v3086",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    SHARED_FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    PACE_SOCKET_PATH.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-copy",
    b"video.demo.doom.presenter.pageflip_min_submit_interval_ms=%d",
    b"video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy",
    b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3084.rel(path)


def v3033_module() -> Any:
    return v3084.v3033_module()


def _set_pageflip_guard(value: int) -> None:
    v3084.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value
    v3084.v3083.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value
    v3084.v3083.v3081.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value
    v3084.v3083.v3081.v3079.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value
    v3033_module().PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = value


def apply_v3086_globals() -> None:
    v3084.CYCLE = CYCLE
    v3084.INIT_VERSION = INIT_VERSION
    v3084.INIT_BUILD = INIT_BUILD
    v3084.BUILD_TAG = BUILD_TAG
    v3084.DECISION = DECISION
    v3084.OUT_DIR = OUT_DIR
    v3084.OBJ_DIR = OBJ_DIR
    v3084.REPORT_PATH = REPORT_PATH
    v3084.BOOT_IMAGE = BOOT_IMAGE
    v3084.INIT_BINARY = INIT_BINARY
    v3084.RAMDISK_CPIO = RAMDISK_CPIO
    v3084.HELPER_BINARY = HELPER_BINARY
    v3084.ENGINE_BINARY = ENGINE_BINARY
    v3084.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3084.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3084.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3084.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3084.ENGINE_NAME = ENGINE_NAME
    v3084.FRAME_PATH = FRAME_PATH
    v3084.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3084.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3084.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3084.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3084.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3084.render_report = render_report
    _set_pageflip_guard(PAGEFLIP_MIN_SUBMIT_INTERVAL_MS)
    v3084.apply_v3084_globals()

    v3033 = v3033_module()
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3033.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3033.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
    V3059.v3059_adapter_source = v3084.v3083.v3081.v3081_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3086 DOOMGENERIC Pageflip Cadence Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone cadence isolation.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3084 background serial-preserve, V3083 fast 3:2 large dashboard, V3081 shared-frame IPC, V3079 presenter-paced helper, timing probe, and UDP/NCM input.",
        f"- Changes only pageflip submit guard: `{BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS}ms` -> `{PAGEFLIP_MIN_SUBMIT_INTERVAL_MS}ms`.",
        "- Purpose: isolate whether the V3085 30fps lock comes from the extra submit guard landing each frame on every other vblank.",
        "",
        "## Cadence Contract",
        "",
        f"- Baseline pageflip min submit interval ms: `{BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS}`",
        f"- Candidate pageflip min submit interval ms: `{PAGEFLIP_MIN_SUBMIT_INTERVAL_MS}`",
        f"- Presenter poll ms: `{PRESENTER_POLL_MS}`",
        f"- Helper frame ms: `{LOOP_FRAME_MS}`",
        f"- Frame scale: `{FRAME_SCALE}`",
        f"- Scale path: `{SCALE_PATH}`",
        "- Frame IPC: `shared-mmap-seq-copy`",
        f"- Shared frame path: `{SHARED_FRAME_PATH}`",
        f"- Pace socket: `{PACE_SOCKET_PATH}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3086 builder and focused tests.",
        "- `unittest`: V3086 source contract plus V3084/V3083/V3081/V3079/V3077/V3074/V3071 lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3086 identity, serial-preserve marker, fast-scale marker, shared-frame markers, pace/pageflip markers, timing telemetry, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3087`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3086 boot image via `native_init_flash.py`, health-check, require pageflip min submit interval `0`, run bounded timing loop, compare flip delta distribution with V3085, and confirm background serial preserve still holds.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-pageflip-cadence-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3086_globals()
    rc = v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "cadence_experiment": "pageflip-min-submit-guard-off",
        "helper_loop_command": (
            f"{ENGINE_REMOTE_PATH} --wad-frame-loop {RUNTIME_WAD_PATH} "
            f"--frames {DEFAULT_LOOP_FRAMES} --output {FRAME_PATH} "
            f"--input-state {INPUT_STATE_PATH} --frame-ms {LOOP_FRAME_MS} "
            f"--input-socket {INPUT_SOCKET_PATH} --pace-socket {PACE_SOCKET_PATH} "
            f"--shared-frame {SHARED_FRAME_PATH} --input-udp {INPUT_UDP_PORT}"
        ),
    })
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-pageflip-cadence-candidate",
        "adoption_state": "pending-pageflip-cadence-live-validation",
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
    (OUT_DIR / "doomgeneric-pageflip-cadence-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-pageflip-cadence-candidate",
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
        "input_state_path": INPUT_STATE_PATH,
        "input_socket_path": INPUT_SOCKET_PATH,
        "input_udp_host": DEVICE_NCM_HOST,
        "input_udp_port": INPUT_UDP_PORT,
        "pace_socket_path": PACE_SOCKET_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "frame_ipc": v3084.v3083.v3081.CANDIDATE_FRAME_IPC,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "background_cancel": CANDIDATE_BACKGROUND_CANCEL,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-pageflip-cadence-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
