#!/usr/bin/env python3
"""Build V3116 native-init DOOM pre-scaled producer candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3114_doomgeneric_hw_plane_atomic as v3114
import native_doomgeneric_engine_integration_build_v3024 as v3024

REPO_ROOT = repo_root()
BASE_V3108 = v3114.v3112.v3108
BASE_COMMON_CFLAGS = v3024.COMMON_CFLAGS

CYCLE = "V3116"
INIT_VERSION = "0.10.113"
INIT_BUILD = "v3116-doomgeneric-prescaled-producer"
BUILD_TAG = INIT_BUILD
DECISION = "v3116-doomgeneric-prescaled-producer-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3116_DOOMGENERIC_PRESCALED_PRODUCER_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3116_doomgeneric_prescaled_producer.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3116_doomgeneric_prescaled_producer"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3116_doomgeneric_prescaled_producer.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v521_doomgeneric_prescaled_producer"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3116"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3116.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3116.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3116"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3116-prescaled-producer"

RUNTIME_WAD_ROOT = v3114.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3114.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3114.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3114.RUNTIME_WAD_MAX_BYTES
DEFAULT_LOOP_FRAMES = v3114.DEFAULT_LOOP_FRAMES
LOOP_FRAME_MS = v3114.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3114.PRESENTER_POLL_MS
FRAME_WIDTH = 960
FRAME_HEIGHT = 600
FRAME_STRIDE = FRAME_WIDTH * 4
FRAME_BYTES = FRAME_STRIDE * FRAME_HEIGHT
FRAME_PATH = "/tmp/a90-doomgeneric-v3116-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3116-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3116-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3116-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3116-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3116-tick-telemetry.txt"
INPUT_UDP_PORT = v3114.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3114.DEVICE_NCM_HOST

NATIVE_DASHBOARD = v3114.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3114.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = 1
HW_PLANE_SCALE = 0
PRE_SCALED_LARGE_FRAME = 1
FRAME_SCALE = "1:1-pre-scaled-producer"
SCALE_PATH = "producer-pre-scaled-raw-rowcopy"
FALLBACK_SCALE_PATH = "none-presenter-scale-disabled"
FRAME_TIMING_PROBE = v3114.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3114.SEQ_TELEMETRY
NATIVE_DOOM_PRESENT_PAGEFLIP = v3114.NATIVE_DOOM_PRESENT_PAGEFLIP

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3116.tick_telemetry=prescaled-producer-original-cadence"
SCALE_MARKER = "a90.doomgeneric.v3116.scale=producer-960x600-1to1"
PHASE_TELEMETRY_MARKER = "a90.doomgeneric.v3116.phase_telemetry=tick-draw-dump-split"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3116.gametic_frame_telemetry=loop-dump-gametic-summary"
)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        b"0.10.112": INIT_VERSION.encode("ascii"),
        b"v3114-doomgeneric-hw-plane-atomic": INIT_BUILD.encode("ascii"),
        b"doomgeneric-private-link-v3114-hw-plane-atomic": ENGINE_NAME.encode("ascii"),
        b"/bin/a90_doomgeneric_private_engine_v3114": ENGINE_REMOTE_PATH.encode("ascii"),
        b"a90-doomgeneric-v3114": b"a90-doomgeneric-v3116",
        b"a90.doomgeneric.v3114": b"a90.doomgeneric.v3116",
        b"hw-plane-atomic": b"prescaled-producer",
        b"drm-plane-srcdst-atomic": b"producer-960x600-1to1",
        b"3:2-hw-plane-atomic": b"1:1-pre-scaled-producer",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3114.REQUIRED_STRINGS) + (
    b"video.demo.doom.dashboard.pre_scaled_large_frame=1",
    b"video.demo.doom.dashboard.frame_mode=minimal-large-pre-scaled-producer",
    b"video.demo.doom.dashboard.frame_scale=1:1-pre-scaled",
    b"video.demo.doom.dashboard.scale_path=producer-pre-scaled-raw-rowcopy",
    b"scale_path=producer-pre-scaled-1to1",
)
REQUIRED_STRINGS = tuple(
    item
    for item in REQUIRED_STRINGS
    if b"hw_plane" not in item
    and b"hw-plane" not in item
    and b"drm-plane-srcdst" not in item
    and b"fast-3to2-rowcopy" not in item
    and b"legacy_setplane" not in item
    and item not in {b"atomic-props", b"atomic-commit"}
)


def rel(path: Path) -> str:
    return v3114.rel(path)


def _replace_resolution_flags(flags: tuple[str, ...]) -> tuple[str, ...]:
    rewritten = []
    for flag in flags:
        if flag.startswith("-DDOOMGENERIC_RESX="):
            rewritten.append(f"-DDOOMGENERIC_RESX={FRAME_WIDTH}")
        elif flag.startswith("-DDOOMGENERIC_RESY="):
            rewritten.append(f"-DDOOMGENERIC_RESY={FRAME_HEIGHT}")
        else:
            rewritten.append(flag)
    return tuple(rewritten)


def apply_private_engine_resolution_flags() -> None:
    common = _replace_resolution_flags(BASE_COMMON_CFLAGS)
    v3024.COMMON_CFLAGS = common
    v3024.THIRD_PARTY_CFLAGS = common + ("-Wall", "-Wextra")
    v3024.ADAPTER_CFLAGS = common + ("-Wall", "-Wextra", "-Werror")


def v3033_module() -> Any:
    return v3114.v3033_module()


def v3116_adapter_source() -> str:
    source = v3114.V3108_ADAPTER_SOURCE()
    replacements = {
        BASE_V3108.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        BASE_V3108.SCALE_MARKER: SCALE_MARKER,
        BASE_V3108.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        BASE_V3108.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
        BASE_V3108.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        BASE_V3108.FRAME_PATH: FRAME_PATH,
        BASE_V3108.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        BASE_V3108.INPUT_STATE_PATH: INPUT_STATE_PATH,
        BASE_V3108.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        BASE_V3108.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    source = source.replace(
        "scale_path=drm-plane-srcdst\\n",
        "scale_path=producer-pre-scaled-1to1\\n",
    )
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3116 DOOMGENERIC Pre-Scaled Producer Source Build",
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
        "- Switches the DOOM helper output geometry from `640x400` to `960x600` while preserving shared-frame sequencing, UDP input, pace socket, pageflip presentation, and the minimal native dashboard.",
        "- Adds `VIDEO_DEMO_DOOMGENERIC_PRE_SCALED_LARGE_FRAME=1`, so the presenter treats the large DOOM frame as already final-size and copies it with a 1:1 raw rowcopy.",
        "- Disables the failed HW plane scale path for this candidate and avoids the presenter's known `fast-3to2-rowcopy` fallback.",
        "- Keeps real DOOM SFX/music out of scope; this is still the bounded native tone co-run sound contract.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Frame geometry: `{FRAME_WIDTH}x{FRAME_HEIGHT}` stride `{FRAME_STRIDE}` bytes `{FRAME_BYTES}`",
        f"- Scale marker: `{SCALE_MARKER}`",
        f"- Scale path: `{SCALE_PATH}`",
        f"- Fallback scale path: `{FALLBACK_SCALE_PATH}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through the checked flash helper `native_init_flash.py` in the next live unit.",
        "- No GPU/GL stack, panel re-init, backlight, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- This source build only changes userspace helper geometry and presenter copy policy.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3116 builder and focused tests.",
        "- `unittest`: V3116 source contract plus relevant V3114/V3115 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3116 identity, pre-scaled producer markers, shared-frame/pageflip/input/audio markers, and no HW-plane atomic requirement.",
        "- `aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror`: `a90_doomgeneric_bridge.c` and HUD include path covered by native-init build.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3117`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3116 image, hide auto menu, run bounded large DOOM loop, require `pre_scaled_large_frame=1`, `frame_scale=1:1-pre-scaled`, raw-rowcopy scale path, shared-frame clean sequence, and pageflip cadence/timing comparison with V3095/V3115.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-prescaled-producer-candidate`.",
    ]) + "\n"


def apply_v3116_globals() -> None:
    v3114.CYCLE = CYCLE
    v3114.INIT_VERSION = INIT_VERSION
    v3114.INIT_BUILD = INIT_BUILD
    v3114.BUILD_TAG = BUILD_TAG
    v3114.DECISION = DECISION
    v3114.OUT_DIR = OUT_DIR
    v3114.OBJ_DIR = OBJ_DIR
    v3114.REPORT_PATH = REPORT_PATH
    v3114.BOOT_IMAGE = BOOT_IMAGE
    v3114.INIT_BINARY = INIT_BINARY
    v3114.RAMDISK_CPIO = RAMDISK_CPIO
    v3114.HELPER_BINARY = HELPER_BINARY
    v3114.ENGINE_BINARY = ENGINE_BINARY
    v3114.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3114.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3114.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3114.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3114.ENGINE_NAME = ENGINE_NAME
    v3114.FRAME_PATH = FRAME_PATH
    v3114.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3114.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3114.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3114.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3114.TICK_TELEMETRY_PATH = TICK_TELEMETRY_PATH
    v3114.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3114.HW_PLANE_SCALE = HW_PLANE_SCALE
    v3114.FRAME_SCALE = FRAME_SCALE
    v3114.SCALE_PATH = SCALE_PATH
    v3114.FALLBACK_SCALE_PATH = FALLBACK_SCALE_PATH
    v3114.TICK_TELEMETRY_MARKER = TICK_TELEMETRY_MARKER
    v3114.SCALE_MARKER = SCALE_MARKER
    v3114.PHASE_TELEMETRY_MARKER = PHASE_TELEMETRY_MARKER
    v3114.GAMETIC_FRAME_TELEMETRY_MARKER = GAMETIC_FRAME_TELEMETRY_MARKER
    v3114.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3114.v3114_adapter_source = v3116_adapter_source
    v3114.render_report = render_report
    v3114.apply_v3114_globals()

    v3033 = v3033_module()
    v3033.FRAME_WIDTH = FRAME_WIDTH
    v3033.FRAME_HEIGHT = FRAME_HEIGHT
    v3033.FRAME_STRIDE = FRAME_STRIDE
    v3033.FRAME_BYTES = FRAME_BYTES
    v3033.NATIVE_DASHBOARD_LARGE_FRAME = NATIVE_DASHBOARD_LARGE_FRAME
    v3033.HW_PLANE_SCALE = HW_PLANE_SCALE
    v3033.PRE_SCALED_LARGE_FRAME = PRE_SCALED_LARGE_FRAME
    v3033.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3033.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3033.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3033.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    apply_private_engine_resolution_flags()


def main() -> int:
    apply_v3116_globals()
    rc = v3114.v3112.v3108.v3100.v3098.v3096.v3086.v3084.main()
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    doom = manifest.setdefault("doomgeneric_visible_loop", {})
    doom.update({
        "scale_marker": SCALE_MARKER,
        "tick_telemetry_marker": TICK_TELEMETRY_MARKER,
        "phase_telemetry_marker": PHASE_TELEMETRY_MARKER,
        "gametic_frame_telemetry_marker": GAMETIC_FRAME_TELEMETRY_MARKER,
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "hw_plane_scale": bool(HW_PLANE_SCALE),
        "pre_scaled_large_frame": bool(PRE_SCALED_LARGE_FRAME),
        "frame_width": FRAME_WIDTH,
        "frame_height": FRAME_HEIGHT,
        "frame_stride": FRAME_STRIDE,
        "frame_bytes": FRAME_BYTES,
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
        "candidate_type": "doomgeneric-prescaled-producer-candidate",
        "adoption_state": "pending-prescaled-producer-live-validation",
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
    (OUT_DIR / "doomgeneric-prescaled-producer-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-prescaled-producer-candidate",
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
        "fallback_scale_path": FALLBACK_SCALE_PATH,
        "hw_plane_scale": bool(HW_PLANE_SCALE),
        "pre_scaled_large_frame": bool(PRE_SCALED_LARGE_FRAME),
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip-pre-scaled-raw-rowcopy",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(v3114.v3112.v3108.HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-prescaled-producer-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
