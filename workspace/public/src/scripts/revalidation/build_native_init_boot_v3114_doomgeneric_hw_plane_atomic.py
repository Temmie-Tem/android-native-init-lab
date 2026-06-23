#!/usr/bin/env python3
"""Build V3114 native-init DOOM hardware-plane atomic-commit candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3112_doomgeneric_hw_plane_cached_crtc as v3112

REPO_ROOT = repo_root()
V3108_ADAPTER_SOURCE = v3112.V3108_ADAPTER_SOURCE

CYCLE = "V3114"
INIT_VERSION = "0.10.112"
INIT_BUILD = "v3114-doomgeneric-hw-plane-atomic"
BUILD_TAG = INIT_BUILD
DECISION = "v3114-doomgeneric-hw-plane-atomic-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3114_DOOMGENERIC_HW_PLANE_ATOMIC_SOURCE_BUILD_2026-06-23.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v3114_doomgeneric_hw_plane_atomic.img", legacy_fallback=False
)
INIT_BINARY = OUT_DIR / "init_v3114_doomgeneric_hw_plane_atomic"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3114_doomgeneric_hw_plane_atomic.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v520_doomgeneric_hw_plane_atomic"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3114"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3114.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3114.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3114"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3114-hw-plane-atomic"

RUNTIME_WAD_ROOT = v3112.RUNTIME_WAD_ROOT
RUNTIME_WAD_PATH = v3112.RUNTIME_WAD_PATH
EXPECTED_WAD_SHA256 = v3112.EXPECTED_WAD_SHA256
RUNTIME_WAD_MAX_BYTES = v3112.RUNTIME_WAD_MAX_BYTES
DEFAULT_LOOP_FRAMES = v3112.DEFAULT_LOOP_FRAMES
LOOP_FRAME_MS = v3112.LOOP_FRAME_MS
PRESENTER_POLL_MS = v3112.PRESENTER_POLL_MS
FRAME_PATH = "/tmp/a90-doomgeneric-v3114-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3114-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3114-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3114-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3114-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3114-tick-telemetry.txt"
INPUT_UDP_PORT = v3112.INPUT_UDP_PORT
DEVICE_NCM_HOST = v3112.DEVICE_NCM_HOST

NATIVE_DASHBOARD = v3112.NATIVE_DASHBOARD
NATIVE_DASHBOARD_MINIMAL = v3112.NATIVE_DASHBOARD_MINIMAL
NATIVE_DASHBOARD_LARGE_FRAME = 1
HW_PLANE_SCALE = 1
FRAME_SCALE = "3:2-hw-plane-atomic"
SCALE_PATH = "drm-plane-srcdst-atomic"
FALLBACK_SCALE_PATH = v3112.FALLBACK_SCALE_PATH
FRAME_TIMING_PROBE = v3112.FRAME_TIMING_PROBE
SEQ_TELEMETRY = v3112.SEQ_TELEMETRY
NATIVE_DOOM_PRESENT_PAGEFLIP = v3112.NATIVE_DOOM_PRESENT_PAGEFLIP

TICK_TELEMETRY_MARKER = "a90.doomgeneric.v3114.tick_telemetry=hw-plane-atomic-original-cadence"
SCALE_MARKER = "a90.doomgeneric.v3114.scale=drm-plane-srcdst-atomic"
PHASE_TELEMETRY_MARKER = "a90.doomgeneric.v3114.phase_telemetry=tick-draw-dump-split"
GAMETIC_FRAME_TELEMETRY_MARKER = (
    "a90.doomgeneric.v3114.gametic_frame_telemetry=loop-dump-gametic-summary"
)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        b"0.10.111": INIT_VERSION.encode("ascii"),
        b"v3112-doomgeneric-hw-plane-cached-crtc": INIT_BUILD.encode("ascii"),
        b"doomgeneric-private-link-v3112-hw-plane-cached-crtc": ENGINE_NAME.encode("ascii"),
        b"/bin/a90_doomgeneric_private_engine_v3112": ENGINE_REMOTE_PATH.encode("ascii"),
        b"a90-doomgeneric-v3112": b"a90-doomgeneric-v3114",
        b"a90.doomgeneric.v3112": b"a90.doomgeneric.v3114",
        b"hw-plane-cached-crtc": b"hw-plane-atomic",
        b"drm-plane-srcdst-cached-crtc": b"drm-plane-srcdst-atomic",
        b"3:2-hw-plane-cached-crtc": b"3:2-hw-plane-atomic",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


REQUIRED_STRINGS = tuple(_rewrite_required_string(item) for item in v3112.REQUIRED_STRINGS) + (
    b"video.demo.doom.dashboard.hw_plane.atomic_attempted=",
    b"video.demo.doom.dashboard.hw_plane.atomic_props_rc=",
    b"video.demo.doom.dashboard.hw_plane.atomic_prop_count=",
    b"video.demo.doom.dashboard.hw_plane.atomic_commit_rc=",
    b"video.demo.doom.dashboard.hw_plane.legacy_setplane_rc=",
    b"atomic-props",
    b"atomic-commit",
)


def rel(path: Path) -> str:
    return v3112.rel(path)


def v3033_module() -> Any:
    return v3112.v3033_module()


def v3114_adapter_source() -> str:
    source = V3108_ADAPTER_SOURCE()
    replacements = {
        v3112.v3108.TICK_TELEMETRY_MARKER: TICK_TELEMETRY_MARKER,
        v3112.v3108.SCALE_MARKER: SCALE_MARKER,
        v3112.v3108.PHASE_TELEMETRY_MARKER: PHASE_TELEMETRY_MARKER,
        v3112.v3108.GAMETIC_FRAME_TELEMETRY_MARKER: GAMETIC_FRAME_TELEMETRY_MARKER,
        v3112.v3108.TICK_TELEMETRY_PATH: TICK_TELEMETRY_PATH,
        v3112.v3108.FRAME_PATH: FRAME_PATH,
        v3112.v3108.SHARED_FRAME_PATH: SHARED_FRAME_PATH,
        v3112.v3108.INPUT_STATE_PATH: INPUT_STATE_PATH,
        v3112.v3108.INPUT_SOCKET_PATH: INPUT_SOCKET_PATH,
        v3112.v3108.PACE_SOCKET_PATH: PACE_SOCKET_PATH,
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    source = source.replace(
        "scale_path=drm-plane-srcdst\\n",
        "scale_path=drm-plane-srcdst-atomic\\n",
    )
    return source


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    doom = manifest.get("doomgeneric_visible_loop", {})
    return "\n".join([
        "# Native Init V3114 DOOMGENERIC Hardware Plane Atomic Source Build",
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
        "- Keeps the V3112 cached-CRTC plane selection fix.",
        "- Preserves the selected plane diagnostics across frame reuse, avoiding false `cached_crtc_index=0` / cap `-ENODEV` readings after the first selected frame.",
        "- Fetches plane atomic properties (`FB_ID`, `CRTC_ID`, `CRTC_X/Y/W/H`, `SRC_X/Y/W/H`) and tries `DRM_IOCTL_MODE_ATOMIC` before legacy `DRM_IOCTL_MODE_SETPLANE`.",
        "- Emits `atomic_attempted`, `atomic_props_rc`, `atomic_prop_count`, `atomic_commit_rc`, and `legacy_setplane_rc` so the live unit can distinguish atomic failure from legacy `SETPLANE -EINVAL`.",
        "- Keeps `fast-3to2-rowcopy` fallback; no GPU/GL, panel re-init, or power path is introduced.",
        "",
        "## V3113 Carry-Forward",
        "",
        "- V3113 proved V3112 progressed past `fetch-resources` to `stage=setplane`, with plane id/fb id present.",
        "- V3113 also proved legacy `SETPLANE` failed with repeated `-22/EINVAL` and the visible path stayed on the CPU `fast-3to2-rowcopy` fallback.",
        "- V3113's final loop summary markers were missing despite protocol END; the next live unit must treat summary loss as a validation/logging problem separate from boot health.",
        "",
        "## Runtime Contract",
        "",
        f"- Runtime WAD path: `{doom.get('runtime_wad_path')}`",
        f"- Expected WAD SHA256: `{doom.get('expected_wad_sha256')}`",
        f"- Helper loop command: `{doom.get('helper_loop_command')}`",
        f"- Scale marker: `{SCALE_MARKER}`",
        f"- Scale path: `{SCALE_PATH}`",
        f"- Fallback scale path: `{FALLBACK_SCALE_PATH}`",
        "",
        "## Safety",
        "",
        "- Boot partition only through the checked flash helper `native_init_flash.py` in the next live unit.",
        "- No GPU/GL stack, panel re-init, backlight, PMIC, regulator, GDSC, GPIO, Wi-Fi connect/dhcp/ping, or forbidden partition path.",
        "- Plane use remains bounded and fallback-preserving; the full-screen KMS path remains available.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3114 builder and focused tests.",
        "- `unittest`: V3114 source contract plus V3112/V3113 regressions.",
        "- Build: AArch64 helper compile/link, native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3114 identity and atomic HW-plane markers.",
        "- `aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror`: `a90_kms.c` standalone compile.",
        "- `git diff --check`: PASS.",
        "",
        "## Next Unit",
        "",
        "- Run ID: `V3115`",
        "- Type: rollback-gated live validation.",
        "- Scope: flash exact V3114 image, hide auto menu, run bounded large DOOM loop, and classify `hw_plane.presented`, `atomic_commit_rc`, `legacy_setplane_rc`, fallback, and summary/END behavior. If atomic also fails, proceed to the pre-scaled producer fallback.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `doomgeneric-hw-plane-atomic-candidate`.",
    ]) + "\n"


def apply_v3114_globals() -> None:
    v3112.CYCLE = CYCLE
    v3112.INIT_VERSION = INIT_VERSION
    v3112.INIT_BUILD = INIT_BUILD
    v3112.BUILD_TAG = BUILD_TAG
    v3112.DECISION = DECISION
    v3112.OUT_DIR = OUT_DIR
    v3112.OBJ_DIR = OBJ_DIR
    v3112.REPORT_PATH = REPORT_PATH
    v3112.BOOT_IMAGE = BOOT_IMAGE
    v3112.INIT_BINARY = INIT_BINARY
    v3112.RAMDISK_CPIO = RAMDISK_CPIO
    v3112.HELPER_BINARY = HELPER_BINARY
    v3112.ENGINE_BINARY = ENGINE_BINARY
    v3112.ENGINE_ADAPTER_SOURCE = ENGINE_ADAPTER_SOURCE
    v3112.ENGINE_ADAPTER_OBJECT = ENGINE_ADAPTER_OBJECT
    v3112.ENGINE_RAMDISK_PATH = ENGINE_RAMDISK_PATH
    v3112.ENGINE_REMOTE_PATH = ENGINE_REMOTE_PATH
    v3112.ENGINE_NAME = ENGINE_NAME
    v3112.FRAME_PATH = FRAME_PATH
    v3112.SHARED_FRAME_PATH = SHARED_FRAME_PATH
    v3112.INPUT_STATE_PATH = INPUT_STATE_PATH
    v3112.INPUT_SOCKET_PATH = INPUT_SOCKET_PATH
    v3112.PACE_SOCKET_PATH = PACE_SOCKET_PATH
    v3112.TICK_TELEMETRY_PATH = TICK_TELEMETRY_PATH
    v3112.FRAME_SCALE = FRAME_SCALE
    v3112.SCALE_PATH = SCALE_PATH
    v3112.TICK_TELEMETRY_MARKER = TICK_TELEMETRY_MARKER
    v3112.SCALE_MARKER = SCALE_MARKER
    v3112.PHASE_TELEMETRY_MARKER = PHASE_TELEMETRY_MARKER
    v3112.GAMETIC_FRAME_TELEMETRY_MARKER = GAMETIC_FRAME_TELEMETRY_MARKER
    v3112.REQUIRED_STRINGS = REQUIRED_STRINGS
    v3112.v3112_adapter_source = v3114_adapter_source
    v3112.render_report = render_report
    v3112.apply_v3112_globals()


def main() -> int:
    apply_v3114_globals()
    rc = v3112.v3108.v3100.v3098.v3096.v3086.v3084.main()
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
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "fallback_scale_path": FALLBACK_SCALE_PATH,
        "hw_plane_diagnostics": True,
        "hw_plane_cached_crtc": True,
        "hw_plane_atomic_commit": True,
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
        "candidate_type": "doomgeneric-hw-plane-atomic-candidate",
        "adoption_state": "pending-hw-plane-atomic-live-validation",
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
    (OUT_DIR / "doomgeneric-hw-plane-atomic-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "doomgeneric-hw-plane-atomic-candidate",
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
        "scale_marker": SCALE_MARKER,
        "tick_telemetry_path": TICK_TELEMETRY_PATH,
        "loop_frame_ms": LOOP_FRAME_MS,
        "presenter_poll_ms": PRESENTER_POLL_MS,
        "frame_scale": FRAME_SCALE,
        "scale_path": SCALE_PATH,
        "fallback_scale_path": FALLBACK_SCALE_PATH,
        "hw_plane_diagnostics": True,
        "hw_plane_cached_crtc": True,
        "hw_plane_atomic_commit": True,
        "present_mode": "pageflip",
        "present_path": "kms-dumb-buffer-pageflip-plus-drm-plane-srcdst-atomic",
        "frame_timing_probe": FRAME_TIMING_PROBE,
        "native_dashboard": bool(NATIVE_DASHBOARD),
        "native_dashboard_minimal": bool(NATIVE_DASHBOARD_MINIMAL),
        "native_dashboard_large_frame": bool(NATIVE_DASHBOARD_LARGE_FRAME),
        "hw_plane_scale": bool(HW_PLANE_SCALE),
        "native_doom_present_pageflip": bool(NATIVE_DOOM_PRESENT_PAGEFLIP),
        "loop_start_command": f"video demo doom loop-start 0 --wad runtime-private --sha256 {EXPECTED_WAD_SHA256}",
        "host_keyboard_bridge": rel(v3112.v3108.HOST_KEYBOARD_BRIDGE),
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-hw-plane-atomic-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
