#!/usr/bin/env python3
"""Build V3185 GPU G0 firmware-class prepare candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3180_gpu_g0_fwpath_status as base

REPO_ROOT = repo_root()
ORIG_V3180_OVERRIDES = base._v3180_overrides
ORIG_V3180_VALUES = base._v3180_values

CYCLE = "V3185"
INIT_VERSION = "0.11.21"
INIT_BUILD = "v3185-gpu-g0-fwclass-prepare"
BUILD_TAG = INIT_BUILD
DECISION = "v3185-gpu-g0-fwclass-prepare-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3185_GPU_G0_FWCLASS_PREPARE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3185_gpu_g0_fwclass_prepare.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3185_gpu_g0_fwclass_prepare"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3185_gpu_g0_fwclass_prepare.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v554_gpu_g0_fwclass_prepare"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3185"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3185.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3185.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3185"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3185-gpu-g0-fwclass-prepare"

FRAME_PATH = "/tmp/a90-doomgeneric-v3185-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3185-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3185-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3185-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3185-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3185-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3185-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-g0-fwclass-prepare"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-g0-fwclass-prepare"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3180", "v3185")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3180", "v3185")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3180", "v3185")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3180", "v3185")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3180", "v3185")
SCALE_MARKER = base.SCALE_MARKER.replace("v3180", "v3185")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3180", "v3185")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3180", "v3185")
SFX_STREAM_MARKER = "a90.doomgeneric.v3185.audio=real-sfx-pcm-stream-gpu-g0-fwclass-prepare"
SOUND_MODE = "native-doom-sfx-gpu-g0-fwclass-prepare-v3185"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3185.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_METRICS_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_STORAGE_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_TEXT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES = base.VIDEO_PLAYER_HUD_FULL_REPAINT_INTERVAL_FRAMES
VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS = base.VIDEO_PLAYER_HUD_TELEMETRY_MIN_SLACK_NS
VIDEO_PLAYER_HUD_LIVE_TELEMETRY = base.VIDEO_PLAYER_HUD_LIVE_TELEMETRY
VIDEO_PLAYER_HUD_DYNAMIC_TEXT = base.VIDEO_PLAYER_HUD_DYNAMIC_TEXT

SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g0-fwpath-status", "gpu-g0-fwclass-prepare")
    .replace("v3180", "v3185")
    .replace("V3180", "V3185")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def rel(path: Path) -> str:
    return base.rel(path)


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"gpu-g0-fwpath-status": b"gpu-g0-fwclass-prepare",
        b"a90-doomgeneric-v3180": b"a90-doomgeneric-v3185",
        b"a90.doomgeneric.v3180": b"a90.doomgeneric.v3185",
        b"v3180": b"v3185",
        b"V3180": b"V3185",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


_RETIRED_MARKERS = (
    b"gpu [g0-status|g0-open-probe",
)

GPU_G0_FWCLASS_PREPARE_MARKERS = (
    b"gpu [g0-status|g0-fwclass-prepare|g0-open-probe",
    b"g0-fwclass-prepare",
    b"gpu.g0.fwclass_prepare.version=1",
    b"gpu.g0.fwclass_prepare.runtime_dir=%s",
    b"/cache/a90-runtime/pkg/gpu-g0-fw",
    b"gpu.g0.fwclass_prepare.requires_private_sqe_gmu_staged=1",
    b"gpu.g0.fwclass_prepare.no_private_payload_in_ramdisk=1",
    b"gpu.g0.fwclass_prepare.no_power_writes=1",
    b"gpu.g0.fwclass_prepare.%s.expected_size=%ld",
    b"gpu.g0.fwclass_prepare.%s.copy_rc=%d",
    b"gpu.g0.fwclass_prepare.fwpath.write_rc=%d",
    b"gpu.g0.fwclass_prepare.fwpath.readback=%s",
    b"gpu.g0.fwclass_prepare.result=ok",
    b"fw_cache_a630_sqe",
    b"fw_cache_a640_gmu",
    b"fw_cache_a640_zap_mdt",
    b"a630_sqe.fw",
    b"a640_gmu.bin",
    b"a640_zap.mdt",
    b"a640_zap.b00",
    b"a640_zap.b01",
    b"a640_zap.b02",
)


REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
    if not any(marker in item for marker in _RETIRED_MARKERS)
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.21",
    b"v3185-gpu-g0-fwclass-prepare",
) + GPU_G0_FWCLASS_PREPARE_MARKERS


def _v3185_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3185 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


def _v3185_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3180_OVERRIDES())
    overrides.update({
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
        "INIT_BINARY": INIT_BINARY,
        "RAMDISK_CPIO": RAMDISK_CPIO,
        "HELPER_BINARY": HELPER_BINARY,
        "ENGINE_BINARY": ENGINE_BINARY,
        "ENGINE_ADAPTER_SOURCE": ENGINE_ADAPTER_SOURCE,
        "ENGINE_ADAPTER_OBJECT": ENGINE_ADAPTER_OBJECT,
        "ENGINE_RAMDISK_PATH": ENGINE_RAMDISK_PATH,
        "ENGINE_REMOTE_PATH": ENGINE_REMOTE_PATH,
        "ENGINE_NAME": ENGINE_NAME,
        "FRAME_PATH": FRAME_PATH,
        "SHARED_FRAME_PATH": SHARED_FRAME_PATH,
        "INPUT_STATE_PATH": INPUT_STATE_PATH,
        "INPUT_SOCKET_PATH": INPUT_SOCKET_PATH,
        "PACE_SOCKET_PATH": PACE_SOCKET_PATH,
        "TICK_TELEMETRY_PATH": TICK_TELEMETRY_PATH,
        "AUDIO_PCM_STREAM_PATH": AUDIO_PCM_STREAM_PATH,
        "FRAME_SCALE": FRAME_SCALE,
        "FRAME_IPC": FRAME_IPC,
        "INPUT_THREAD_MARKER": INPUT_THREAD_MARKER,
        "TIME_MODEL_MARKER": TIME_MODEL_MARKER,
        "DEMO_HUD_MARKER": DEMO_HUD_MARKER,
        "PACED_TIME_MARKER": PACED_TIME_MARKER,
        "TICK_TELEMETRY_MARKER": TICK_TELEMETRY_MARKER,
        "SCALE_MARKER": SCALE_MARKER,
        "PHASE_TELEMETRY_MARKER": PHASE_TELEMETRY_MARKER,
        "GAMETIC_FRAME_TELEMETRY_MARKER": GAMETIC_FRAME_TELEMETRY_MARKER,
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": SFX_BACKEND_SOURCE_TEXT,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
    })
    return overrides


def _v3185_values() -> dict[str, Any]:
    values = dict(ORIG_V3180_VALUES())
    values.update(_v3185_overrides())
    return values


def v3185_adapter_source() -> str:
    return (
        base.BASE_ADAPTER_SOURCE_TEXT
        .replace("real-sfx-pcm-stream-badapple-nyan-silence-tail",
                 "real-sfx-pcm-stream-gpu-g0-fwclass-prepare")
        .replace("badapple-nyan-silence-tail", "gpu-g0-fwclass-prepare")
        .replace("v3175", "v3185")
        .replace("V3175", "V3185")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3185 GPU G0 Firmware-Class Prepare Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU G0 KGSL open-hang diagnosis.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds `gpu g0-fwclass-prepare` after V3184 proved unified firmware visibility makes bounded KGSL first-open return.",
        "- The command expects private `a630_sqe.fw` and `a640_gmu.bin` to already be staged under `/cache/a90-runtime/pkg/gpu-g0-fw`.",
        "- It copies the runtime-visible `a640_zap.*` files from `/vendor/firmware_mnt/image` into that same cache directory.",
        "- It verifies exact expected file sizes before changing `/sys/module/firmware_class/parameters/path`.",
        "- `gpu g0-status` now reports the cache firmware files as well as the legacy vendor/root paths.",
        "- No private firmware payload is bundled into the public source tree or boot ramdisk.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- No KGSL ioctl, mmap, freedreno submit, G1 allocation, proprietary Adreno blob/EGL/Bionic path, or exploit work.",
        "- No GMU/GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- The only sysfs write is the firmware search path used by kernel `request_firmware()`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3185 builder and focused tests.",
        "- `unittest`: V3185 GPU G0 firmware-class prepare source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3185 identity, `g0-fwclass-prepare`, cache firmware path/status markers, and bounded open markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-g0-fwclass-prepare-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g0-fwclass-prepare-candidate",
        "adoption_state": "pending-fresh-boot-gpu-g0-fwclass-prepare-validation",
        "gpu_g0": {
            "source_baseline": "v3180-gpu-g0-fwpath-status",
            "live_unlock_report": "docs/reports/NATIVE_INIT_V3184_GPU_G0_FWCLASS_LIVE_OPEN_SUCCESS_2026-06-25.md",
            "commands": [
                "gpu g0-status",
                "gpu g0-fwclass-prepare",
                "gpu g0-open-probe --timeout-ms 5000 --materialize-devnode",
            ],
            "runtime_firmware_cache": "/cache/a90-runtime/pkg/gpu-g0-fw",
            "staged_private_inputs_required": [
                "a630_sqe.fw",
                "a640_gmu.bin",
            ],
            "ramdisk_private_firmware_payloads": 0,
            "zap_source": "/vendor/firmware_mnt/image/a640_zap.*",
            "open_probe_parent_enters_open": False,
            "open_probe_timeout_guard_ms_default": 2000,
            "open_probe_timeout_guard_ms_max": 10000,
            "forbidden_operations": [
                "kgsl-ioctl",
                "kgsl-mmap",
                "kgsl-gpuobj-alloc",
                "freedreno-submit",
                "GDSC-write",
                "regulator-write",
                "PMIC-write",
                "GPIO-write",
                "proprietary-adreno-blob",
                "exploit-dev",
            ],
            "next_live_validation": [
                "flash-v3185-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-g0-open-probe-timeout-guard",
                "fresh-boot-dmesg-modem-ssr-correlation-check",
            ],
        },
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
    (OUT_DIR / "gpu-g0-fwclass-prepare-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g0-fwclass-prepare-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "gpu-g0-fwclass-prepare",
            "gpu-g0-open-probe-timeout-guard",
            "fresh-boot-modem-ssr-correlation",
        ],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-fresh-boot-gpu-g0-fwclass-prepare-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3185_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3180_overrides", _v3185_overrides),
        ("_v3180_values", _v3185_values),
        ("_v3180_adapter_source_from_patched_v3148", v3185_adapter_source),
        ("v3180_adapter_source", v3185_adapter_source),
        ("_v3180_require_strings", _v3185_require_strings),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((base, name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_base_module(saved: list[tuple[Any, str, Any, bool]]) -> None:
    for module, name, value, existed in reversed(saved):
        if existed:
            setattr(module, name, value)
        else:
            delattr(module, name)


def main() -> int:
    saved = _patch_base_module()
    try:
        return base.main()
    finally:
        _restore_base_module(saved)


if __name__ == "__main__":
    raise SystemExit(main())
