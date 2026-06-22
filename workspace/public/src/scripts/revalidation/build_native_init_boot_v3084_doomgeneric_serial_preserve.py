#!/usr/bin/env python3
"""Build V3084 native-init DOOM background serial-preserve candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3083_doomgeneric_fastscale_large as v3083
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3084"
INIT_VERSION = "0.10.99"
INIT_BUILD = "v3084-doomgeneric-serial-preserve"
BUILD_TAG = INIT_BUILD
DECISION = "v3084-doomgeneric-serial-preserve-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3084_DOOMGENERIC_SERIAL_PRESERVE_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3084_doomgeneric_serial_preserve.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3084_doomgeneric_serial_preserve"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3084_doomgeneric_serial_preserve.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v512_doomgeneric_serial_preserve"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3084"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3084.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3084.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3084"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3084-serial-preserve"

RUNTIME_WAD_ROOT = v3083.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3083.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3083.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3083.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3083.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3083.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3083.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3083.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3083.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3083.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3083.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3084-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3084-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3084-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3084-input.sock"
INPUT_UDP_PORT = v3083.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3083.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3084-pace.sock"
PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3083.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3083.FRAME_WIDTH
FRAME_HEIGHT = v3083.FRAME_HEIGHT
FRAME_STRIDE = v3083.FRAME_STRIDE
FRAME_BYTES = v3083.FRAME_BYTES
NATIVE_DASHBOARD = v3083.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3083.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = v3083.NATIVE_DASHBOARD_LARGE_FRAME
NATIVE_DOOM_PRESENT_PAGEFLIP = v3083.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_BACKGROUND_CANCEL = "background-child-reads-serial-cancel"
CANDIDATE_BACKGROUND_CANCEL = "disabled-serial-preserve"
FRAME_SCALE = v3083.CANDIDATE_FRAME_SCALE
SCALE_PATH = v3083.SCALE_PATH
REUSE_FRAME_BUFFER = v3083.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3083.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3083.FRAME_TIMING_PROBE

SOUND_MODE = v3083.SOUND_MODE
AUDIO_CORUN = v3083.AUDIO_CORUN
AUDIO_CORUN_MODE = v3083.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3083.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3083.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3083.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3083.HOST_DASHBOARD
V3059 = v3083.V3059

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.99 (v3084-doomgeneric-serial-preserve)",
    b"v3084-doomgeneric-serial-preserve",
    b"doomgeneric-private-link-v3084-serial-preserve",
    b"/bin/a90_doomgeneric_private_engine_v3084",
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
    b"video.demo.doom.dashboard.scale_path=fast-3to2-rowcopy",
    b"video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
    b"video.demo.doom.loop.frame_ipc=",
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3083.rel(path)


def v3033_module() -> Any:
    return v3083.v3033_module()


def apply_v3084_globals() -> None:
    v3083.CYCLE = CYCLE
    v3083.INIT_VERSION = INIT_VERSION
    v3083.INIT_BUILD = INIT_BUILD
    v3083.BUILD_TAG = BUILD_TAG
    v3083.DECISION = DECISION
    v3083.OUT_DIR = OUT_DIR
    v3083.OBJ_DIR = OBJ_DIR
    v3083.REPORT_PATH = REPORT_PATH
    v3083.BOOT_IMAGE = BOOT_IMAGE
    v3083.INIT_BINARY = INIT_BINARY
    v3083.RAMDISK_CPIO = RAMDISK_CPIO
    v3083.HELPER_BINARY = HELPER_BINARY
    v3083.ENGINE_BINARY = ENGINE_BINARY
    v3083.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3083.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3083.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3083.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3083.ENGINE_NAME = ENGINE_NAME
    v3083.FRAME_PATH = FRAME_PATH
    v3083.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3083.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3083.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3083.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3083.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3083.render_report = render_report
    v3083.apply_v3083_globals()

    v3033 = v3033_module()
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3033.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    V3059.v3059_adapter_source = v3083.v3081.v3081_adapter_source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3084 DOOMGENERIC Serial Preserve Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: active Video playback / DOOM capstone control-plane robustness.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps V3083 fast 3:2 large minimal dashboard, V3081 shared-frame IPC, V3079 presenter-paced helper, pageflip presentation, frame_ms=28, timing probe, and UDP/NCM input.",
        "- Changes only background DOOM loop cancellation: foreground `video demo doom loop` remains q/Ctrl-C cancellable, but `loop-start` background children no longer read serial STDIN.",
        "- This prevents the background presenter from consuming bytes from later `cmdv1` commands while the shell is also reading the same USB ACM stream.",
        "",
        "## Serial Preserve Contract",
        "",
        f"- Baseline background cancel: `{BASELINE_BACKGROUND_CANCEL}`",
        f"- Candidate background cancel: `{CANDIDATE_BACKGROUND_CANCEL}`",
        "- Loop-start marker: `video.demo.doom.loop_start.background_cancel=disabled-serial-preserve`",
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
        "- `py_compile`: V3084 builder and focused tests.",
        "- `unittest`: V3084 source contract plus V3083/V3081/V3079/V3077/V3074/V3071 lineage regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3084 identity, serial-preserve marker, fast-scale marker, shared-frame markers, pace/pageflip markers, timing telemetry, and UDP input markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3085`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3084 boot image via `native_init_flash.py`, health-check, require serial-preserve/fast-scale/shared-frame markers, run bounded loop, start continuous background loop, then verify subsequent `version`/`status`/`loop-status` commands remain framed while gameplay continues.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-serial-preserve-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3084_globals()
    rc = v3083.v3081.v3079.v3077.v3074.v3071.v3069.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "shared_frame_path": SHARED_FRAME_PATH,
        "raw_fallback_frame_path": FRAME_PATH,
        "frame_ipc": v3083.v3081.CANDIDATE_FRAME_IPC,
        "pace_socket_path": PACE_SOCKET_PATH,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "background_cancel_baseline": BASELINE_BACKGROUND_CANCEL,
        "background_cancel": CANDIDATE_BACKGROUND_CANCEL,
        "serial_preserve_marker": "video.demo.doom.loop_start.background_cancel=disabled-serial-preserve",
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip",
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
        "candidate_type": "doomgeneric-serial-preserve-candidate",
        "adoption_state": "pending-serial-preserve-live-validation",
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
    (OUT_DIR / "doomgeneric-serial-preserve-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-serial-preserve-candidate",
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
        "frame_ipc": v3083.v3081.CANDIDATE_FRAME_IPC,
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
        "adoption_state": "pending-serial-preserve-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
