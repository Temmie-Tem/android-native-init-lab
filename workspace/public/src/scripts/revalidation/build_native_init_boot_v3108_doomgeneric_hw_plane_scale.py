#!/usr/bin/env python3
"""Build V3108 native-init DOOM hardware plane scaling candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
import build_native_init_boot_v3100_doomgeneric_phase_telemetry as v3100
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path

REPO_ROOT = repo_root()

CYCLE = "V3108"
INIT_VERSION = "0.10.109"
INIT_BUILD = "v3108-doomgeneric-hw-plane-scale"
BUILD_TAG = INIT_BUILD
DECISION = "v3108-doomgeneric-hw-plane-scale-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3108_DOOMGENERIC_HW_PLANE_SCALE_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3108_doomgeneric_hw_plane_scale.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3108_doomgeneric_hw_plane_scale"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3108_doomgeneric_hw_plane_scale.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v520_doomgeneric_hw_plane_scale"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3108"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3108.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3108.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3108"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3108-hw-plane-scale"

RUNTIME_WAD_ROOT = v3100.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3100.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3100.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3100.RUNTIME_WAD_MAX_BYTES
DEFAULT_FRAME_TICKS = v3100.DEFAULT_FRAME_TICKS
DEFAULT_SMOKE_FRAMES = v3100.DEFAULT_SMOKE_FRAMES
DEFAULT_LOOP_FRAMES = v3100.DEFAULT_LOOP_FRAMES
CONTINUOUS_LOOP_FRAMES = v3100.CONTINUOUS_LOOP_FRAMES
MAX_LOOP_FRAMES = v3100.MAX_LOOP_FRAMES
LOOP_FRAME_MS = v3100.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3100.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3108-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3108-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3108-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3108-input.sock"
INPUT_UDP_PORT = v3100.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3100.DEVICE_NCM_HOST
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3108-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3108-tick-telemetry.txt"

PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3100.PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS = v3100.BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS
FRAME_WIDTH = v3100.FRAME_WIDTH
FRAME_HEIGHT = v3100.FRAME_HEIGHT
FRAME_STRIDE = v3100.FRAME_STRIDE
FRAME_BYTES = v3100.FRAME_BYTES
NATIVE_DASHBOARD = v3100.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3100.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = 1
BASELINE_NATIVE_DASHBOARD_LARGE_FRAME = v3100.NATIVE_DASHBOARD_LARGE_FRAME
HW_PLANE_SCALE = 1
NATIVE_DOOM_PRESENT_PAGEFLIP = v3100.NATIVE_DOOM_PRESENT_PAGEFLIP
BASELINE_FRAME_SCALE = v3100.FRAME_SCALE
FRAME_SCALE = "3:2-hw-plane"
SCALE_PATH = "drm-plane-srcdst"
FALLBACK_SCALE_PATH = "fast-3to2-rowcopy"
REUSE_FRAME_BUFFER = v3100.REUSE_FRAME_BUFFER
DASHBOARD_METRICS_INTERVAL_FRAMES = v3100.DASHBOARD_METRICS_INTERVAL_FRAMES
FRAME_TIMING_PROBE = v3100.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3100.SEQ_TELEMETRY
BASELINE_BACKGROUND_CANCEL = v3100.BASELINE_BACKGROUND_CANCEL
CANDIDATE_BACKGROUND_CANCEL = v3100.CANDIDATE_BACKGROUND_CANCEL

SOUND_MODE = v3100.SOUND_MODE
AUDIO_CORUN = v3100.AUDIO_CORUN
AUDIO_CORUN_MODE = v3100.AUDIO_CORUN_MODE
AUDIO_CORUN_DURATION_MS = v3100.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_AMPLITUDE_MILLI = v3100.AUDIO_CORUN_AMPLITUDE_MILLI

HOST_KEYBOARD_BRIDGE = v3100.HOST_KEYBOARD_BRIDGE
HOST_DASHBOARD = v3100.HOST_DASHBOARD
V3059 = v3100.V3059

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3108.tick_telemetry=hw-plane-scale-original-cadence"
SCALE_MARKER = "a90.doomgeneric.v3108.scale=drm-plane-srcdst-large"
PHASE_TELEMETRY_MARKER = "a90.doomgeneric.v3108.phase_telemetry=tick-draw-dump-split"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3108.gametic_frame_telemetry=loop-dump-gametic-summary"
)
SEQ_TELEMETRY_CONTRACT = v3100.SEQ_TELEMETRY_CONTRACT
SEQ_TELEMETRY_MODEL = v3100.SEQ_TELEMETRY_MODEL

REQUIRED_STRINGS = (
    b"A90 Linux init 0.10.109 (v3108-doomgeneric-hw-plane-scale)",
    b"v3108-doomgeneric-hw-plane-scale",
    b"doomgeneric-private-link-v3108-hw-plane-scale",
    b"/bin/a90_doomgeneric_private_engine_v3108",
    RUNTIME_WAD_PATH.encode("ascii"),
    EXPECTED_WAD_SHA256.encode("ascii"),
    FRAME_PATH.encode("ascii"),
    SHARED_FRAME_PATH.encode("ascii"),
    INPUT_STATE_PATH.encode("ascii"),
    INPUT_SOCKET_PATH.encode("ascii"),
    PACE_SOCKET_PATH.encode("ascii"),
    TICK_TELEMETRY_PATH.encode("ascii"),
    TICK_TELEMETRY_MARKER.encode("ascii"),
    SCALE_MARKER.encode("ascii"),
    PHASE_TELEMETRY_MARKER.encode("ascii"),
    GAMETIC_FRAME_TELEMETRY_MARKER.encode("ascii"),
    b"a90.doomgeneric.v3059.input=udp-ncm-state-with-unix-dgram-fallback",
    b"a90.doomgeneric.v3079.pace=presenter-pageflip-token",
    b"a90.doomgeneric.v3081.frame_ipc=shared-mmap-seq",
    b"--shared-frame",
    b"shared-mmap-copy",
    b"video.demo.doom.dashboard.hw_plane_scale=1",
    b"video.demo.doom.dashboard.frame_mode=minimal-large-hw-plane-scale",
    b"video.demo.doom.dashboard.frame_scale=3:2",
    b"video.demo.doom.dashboard.scale_path=drm-plane-srcdst",
    b"video.demo.doom.dashboard.hw_plane.fallback=fast-3to2-rowcopy",
    SEQ_TELEMETRY_CONTRACT.encode("ascii"),
    SEQ_TELEMETRY_MODEL.encode("ascii"),
    b"video.demo.doom.loop.timing_probe=1",
    b"native-audio-corun-tone-v3053",
)


def rel(path: Path) -> str:
    return v3100.rel(path)


def v3033_module() -> Any:
    return v3100.v3033_module()


def _replace_required(source: str, old: str, new: str) -> str:
    if old not in source:
        raise RuntimeError(f"missing V3108 adapter source anchor: {old[:96]!r}")
    return source.replace(old, new, 1)


def v3108_adapter_source() -> str:
    source = v3100.v3100_adapter_source()
    replacements = {
        v3100.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3100.SCALE_1TO1_MARKER: SCALE_MARKER,
        v3100.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
        v3100.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3100.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3100.FRAME_PATH: FRAME_PATH,
        v3100.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3100.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3100.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3100.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    source = _replace_required(
        source,
        '    ok = ok && fprintf(fp, "fake_time_model=DG_SleepMs-accumulated\\n") >= 0;\n',
        '    ok = ok && fprintf(fp, "fake_time_model=DG_SleepMs-accumulated\\n") >= 0;\n'
        f'    ok = ok && fprintf(fp, "scale_marker={SCALE_MARKER}\\n") >= 0;\n'
        '    ok = ok && fprintf(fp, "scale_path=drm-plane-srcdst\\n") >= 0;\n',
    )
    return source


def _set_hw_plane_scale(value: int) -> None:
    v3033 = v3033_module()
    v3033.HW_PLANE_SCALE = value


def apply_v3108_globals() -> None:
    v3100.apply_v3100_globals()
    base = v3100.v3098.v3096.v3086
    base.CYCLE = CYCLE
    base.INIT_VERSION = INIT_VERSION
    base.INIT_BUILD = INIT_BUILD
    base.BUILD_TAG = BUILD_TAG
    base.DECISION = DECISION
    base.OUT_DIR = OUT_DIR
    base.OBJ_DIR = OBJ_DIR
    base.REPORT_PATH = REPORT_PATH
    base.BOOT_IMAGE = BOOT_IMAGE
    base.INIT_BINARY = INIT_BINARY
    base.RAMDISK_CPIO = RAMDISK_CPIO
    base.HELPER_BINARY = HELPER_BINARY
    base.ENGINE_BINARY = ENGINE_BINARY
    base.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    base.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    base.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    base.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    base.ENGINE_NAME = ENGINE_NAME
    base.FRAME_PATH = FRAME_PATH
    base.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    base.INPUT_STATE_PATH = INPUT_STATE_PATH
    base.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    base.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    base.REQUIRED_STRINGS = REQUIRED_STRINGS
    base.render_report = render_report
    base.v3084.v3083.v3081.v3081_adapter_source = v3108_adapter_source
    v3100.v3098.v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3100.v3098.v3096._set_seq_telemetry(SEQ_TELEMETRY)
    _set_hw_plane_scale(HW_PLANE_SCALE)
    base.apply_v3086_globals()
    v3100.v3098.v3096._set_large_frame(NATIVE_DASHBOARD_LARGE_FRAME)
    v3100.v3098.v3096._set_seq_telemetry(SEQ_TELEMETRY)
    _set_hw_plane_scale(HW_PLANE_SCALE)
    base.v3084.v3083.v3081.v3081_adapter_source = v3108_adapter_source
    V3059.v3059_adapter_source = v3108_adapter_source

    v3033 = v3033_module()
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3033.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3033.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3033.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3033.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3033.HW_PLANE_SCALE = HW_PLANE_SCALE


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    markers = manifest.get("v3033_marker_strings", [])
    marker_lines = [f"- `{marker}`" for marker in markers] if isinstance(markers, list) else []
    return "\n".join([
        "# Native Init V3108 DOOMGENERIC Hardware Plane Scale Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: DOOM large-frame scale-path optimization.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps the original DOOM cadence lineage from V3100 rather than the non-original-speed V3104 paced-tic diagnostic.",
        "- Re-enables the 640x400 -> 960x600 large DOOM dashboard frame.",
        "- Adds `VIDEO_DEMO_DOOMGENERIC_HW_PLANE_SCALE=1`: the presenter copies the raw 640x400 XBGR8888 frame into a small dumb buffer and asks DRM/SDE to scale it with plane source/destination rectangles.",
        "- The software 3:2 fast row-copy scaler remains a fallback if no unused compatible plane can be attached.",
        "- `loop-stop` clears the scaled plane before restoring the full-screen KMS path.",
        "",
        "## Scale Contract",
        "",
        f"- V3107 plane probe: `candidate_count=16`, `active_source=current-plane`.",
        f"- Baseline frame scale: `{BASELINE_FRAME_SCALE}`",
        f"- Candidate frame scale: `{FRAME_SCALE}`",
        f"- Candidate scale path: `{SCALE_PATH}`",
        f"- Fallback scale path: `{FALLBACK_SCALE_PATH}`",
        "- Plane policy: use an unused compatible plane only; do not steal the current full-screen primary plane.",
        "- Display mutation: bounded `DRM_IOCTL_MODE_SETPLANE` only, with full-screen KMS path retained.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Continuous command: `video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}`",
        "",
        "## Additional Cause Check",
        "",
        "- If `hw_plane.presented=0`, the large path has fallen back to the CPU 3:2 row-copy scaler, so V3095's large-scaler stutter remains expected.",
        "- If `hw_plane.presented=1` but the DOOM frame is not visible, suspect plane ordering/zpos or a legacy `SETPLANE` driver quirk; this source build records plane id/fb id/rc but live visual confirmation is still required.",
        "- If pageflip stays near 16.6 ms and `seq.shared_missed_frames=0`, remaining stepped motion is the known DOOM 35 Hz game-tic cadence on the 60 Hz panel, not presenter jitter.",
        "- Sound in this candidate is still `native-audio-corun-tone-v3053`, not real DOOM music/SFX; silence after the bounded tone duration is not evidence that DOOM audio is wired.",
        "",
        "## Marker Check",
        "",
        *marker_lines,
        "",
        "## Validation",
        "",
        "- `py_compile`: V3108 builder and focused tests.",
        "- `unittest`: V3108 source contract plus current KMS/DOOM scale-path checks.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3108 identity, hardware-plane scale markers, shared-frame/pageflip/input/audio markers, and original-cadence telemetry markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3109`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3108 image via `native_init_flash.py`, health-check, run bounded large DOOM loop, require `hw_plane.presented=1` or record fallback, compare draw/total timing and pageflip deltas with V3095/V3101.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-hw-plane-scale-candidate`.",
    ]) + "\n"


def main() -> int:
    apply_v3108_globals()
    rc = v3100.v3098.v3096.v3086.v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "scale_marker": SCALE_MARKER,
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
        "phase_telemetry_marker": PHASE_TELEMETRY_MARKER,
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "fake_time_model": "DG_SleepMs-accumulated",
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "baseline_native_dashboard_large_frame": bool(BASELINE_NATIVE_DASHBOARD_LARGE_FRAME),
        "hw_plane_scale": bool(HW_PLANE_SCALE),
        "baseline_frame_scale": BASELINE_FRAME_SCALE,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "fallback_scale_path": FALLBACK_SCALE_PATH,
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
        "candidate_type": "doomgeneric-hw-plane-scale-candidate",
        "adoption_state": "pending-hw-plane-scale-live-validation",
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
    (OUT_DIR / "doomgeneric-hw-plane-scale-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-hw-plane-scale-candidate",
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
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
        "phase_telemetry_marker": PHASE_TELEMETRY_MARKER,
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "scale_marker": SCALE_MARKER,
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "pageflip_min_submit_interval_baseline_ms": BASELINE_PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "pageflip_min_submit_interval_ms": PAGEFLIP_MIN_SUBMIT_INTERVAL_MS,
        "frame_ipc": v3100.v3098.v3096.v3086.v3084.v3083.v3081.CANDIDATE_FRAME_IPC,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "fallback_scale_path": FALLBACK_SCALE_PATH,
        "baseline_frame_scale": BASELINE_FRAME_SCALE,
        "background_cancel": CANDIDATE_BACKGROUND_CANCEL,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip-plus-drm-plane-srcdst",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "fake_time_model": "DG_SleepMs-accumulated",
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "hw_plane_scale": bool(HW_PLANE_SCALE),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-hw-plane-scale-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
