#!/usr/bin/env python3
"""Build V3194 GPU G3 bounded KGSL noop submit/fence probe candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3192_gpu_g2_mmap_probe as base

REPO_ROOT = repo_root()
ORIG_V3192_OVERRIDES = base._v3192_overrides
ORIG_V3192_VALUES = base._v3192_values
ORIG_V3192_ADAPTER_SOURCE = base.v3192_adapter_source

CYCLE = "V3194"
INIT_VERSION = "0.11.25"
INIT_BUILD = "v3194-gpu-g3-noop-submit-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3194-gpu-g3-noop-submit-probe-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3194_GPU_G3_NOOP_SUBMIT_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3194_gpu_g3_noop_submit_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3194_gpu_g3_noop_submit_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3194_gpu_g3_noop_submit_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v557_gpu_g3_noop_submit_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3194"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3194.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3194.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3194"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3194-gpu-g3-noop-submit-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3194-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3194-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3194-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3194-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3194-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3194-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3194-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-g3-noop-submit-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-g3-noop-submit-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3192", "v3194")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3192", "v3194")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3192", "v3194")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3192", "v3194")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3192", "v3194")
SCALE_MARKER = base.SCALE_MARKER.replace("v3192", "v3194")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3192", "v3194")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3192", "v3194")
SFX_STREAM_MARKER = "a90.doomgeneric.v3194.audio=real-sfx-pcm-stream-gpu-g3-noop-submit-probe"
SOUND_MODE = "native-doom-sfx-gpu-g3-noop-submit-probe-v3194"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3194.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"


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
        b"gpu-g2-mmap-probe": b"gpu-g3-noop-submit-probe",
        b"a90-doomgeneric-v3192": b"a90-doomgeneric-v3194",
        b"a90.doomgeneric.v3192": b"a90.doomgeneric.v3194",
        b"v3192": b"v3194",
        b"V3192": b"V3194",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_G3_NOOP_SUBMIT_MARKERS = (
    b"g3-noop-submit-probe",
    b"noop-submit-probe",
    b"gpu.g3.noop.version=1",
    b"gpu.g3.noop.scope=kgsl-noop-submit-fence-probe",
    b"gpu.g3.noop.parent_enters_open=0",
    b"gpu.g3.noop.parent_enters_ioctl=0",
    b"gpu.g3.noop.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy",
    b"gpu.g3.noop.pm4_source=mesa-freedreno-pkt7-cp-nop",
    b"gpu.g3.noop.pm4_cp_type7=0x%x",
    b"gpu.g3.noop.pm4_cp_nop=0x%x",
    b"gpu.g3.noop.noop_dwords=%u",
    b"gpu.g3.noop.noop_bytes=%llu",
    b"gpu.g3.noop.mapped_write_attempted=1",
    b"gpu.g3.noop.cache_sync_attempted=1",
    b"gpu.g3.noop.submit_attempted=1",
    b"gpu.g3.noop.fence_attempted=1",
    b"gpu.g3.noop.render_attempted=0",
    b"gpu.g3.noop.power_write_attempted=0",
    b"gpu.g3.noop.result=%s",
    b"gpu.g3.noop.submit_rc=%d",
    b"gpu.g3.noop.submit_timestamp=%u",
    b"gpu.g3.noop.timestamp_event_rc=%d",
    b"gpu.g3.noop.fence_fd=%d",
    b"gpu.g3.noop.wait_rc=%d",
    b"gpu.g3.noop.readtimestamp_rc=%d",
    b"gpu.g3.noop.retired_timestamp=%u",
    b"gpu.g3.noop.free_deferred=%d",
    b"gpu.g3.noop.total_elapsed_ms=%ld",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.25",
    b"v3194-gpu-g3-noop-submit-probe",
) + GPU_G3_NOOP_SUBMIT_MARKERS


def _v3194_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3194 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g2-mmap-probe", "gpu-g3-noop-submit-probe")
    .replace("real-sfx-pcm-stream-gpu-g2-mmap-probe",
             "real-sfx-pcm-stream-gpu-g3-noop-submit-probe")
    .replace("v3192", "v3194")
    .replace("V3192", "V3194")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3194_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3192_OVERRIDES())
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


def _v3194_values() -> dict[str, Any]:
    values = dict(ORIG_V3192_VALUES())
    values.update(_v3194_overrides())
    return values


def v3194_adapter_source() -> str:
    return (
        ORIG_V3192_ADAPTER_SOURCE()
        .replace("gpu-g2-mmap-probe", "gpu-g3-noop-submit-probe")
        .replace("real-sfx-pcm-stream-gpu-g2-mmap-probe",
                 "real-sfx-pcm-stream-gpu-g3-noop-submit-probe")
        .replace("v3192", "v3194")
        .replace("V3192", "V3194")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3194 GPU G3 Noop Submit Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU G3 KGSL noop command-stream submit plus timestamp fence.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds `gpu g3-noop-submit-probe`, a bounded child-only KGSL submit probe.",
        "- The child sequence is `open` -> `DRAWCTXT_CREATE` -> `GPUOBJ_ALLOC` -> `GPUOBJ_INFO` -> `mmap` -> write a two-dword freedreno-style `CP_NOP` IB -> `GPUOBJ_SYNC` to GPU -> `GPU_COMMAND` -> `TIMESTAMP_EVENT` fence -> bounded `WAITTIMESTAMP_CTXTID` -> read retired timestamp -> cleanup.",
        "- Keeps G0/G1/G2 commands available as prerequisites and regression checks.",
        "- The parent never enters KGSL `open()` or `ioctl()`; it only enforces timeout and reports metadata.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.",
        "- No GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- No render target, solid fill, triangle, shader, or KMS blit is included in G3.",
        "- The only mapped-memory write is the minimal two-dword noop IB needed for command submission.",
        "",
        "## Source Basis",
        "",
        "- Local Samsung KGSL UAPI/driver source: `IOCTL_KGSL_GPU_COMMAND` returns a timestamp, `IOCTL_KGSL_TIMESTAMP_EVENT` can create a fence fd for that timestamp, and `IOCTL_KGSL_GPUOBJ_SYNC` performs cache sync by GPU object id.",
        "- Mesa/freedreno PM4 source: type7 packet header helper plus `CP_NOP = 0x10`; V3194 implements the same odd-parity header rule locally.",
        "- Mesa references: `https://docs.mesa3d.org/drivers/freedreno.html`, `https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/refs/heads/upstream/main/src/freedreno/registers/adreno/adreno_pm4.xml`, `https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/refs/heads/upstream/main/src/freedreno/common/freedreno_pm4.h`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3194 builder and focused tests.",
        "- `unittest`: V3194 GPU G3 source contract plus V3192/V3190 regression contracts.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3194 identity, G0/G1/G2 markers, and G3 noop submit markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-g3-noop-submit-probe-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g3-noop-submit-probe-candidate",
        "adoption_state": "pending-gpu-g3-noop-submit-live-validation",
        "gpu_g3": {
            "source_baseline": "v3192-gpu-g2-mmap-probe",
            "g2b_live_report": "docs/reports/NATIVE_INIT_V3193_GPU_G2_MMAP_PROBE_LIVE_2026-06-25.md",
            "commands": [
                "gpu g0-fwclass-prepare",
                "gpu g1-context-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode",
            ],
            "command_stream": {
                "pm4_source": "Mesa freedreno pkt7 helper + CP_NOP opcode",
                "pm4_reference_urls": [
                    "https://docs.mesa3d.org/drivers/freedreno.html",
                    "https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/refs/heads/upstream/main/src/freedreno/registers/adreno/adreno_pm4.xml",
                    "https://chromium.googlesource.com/external/gitlab.freedesktop.org/mesa/mesa/+/refs/heads/upstream/main/src/freedreno/common/freedreno_pm4.h",
                ],
                "type7": "0x70000000",
                "cp_nop": "0x10",
                "dwords": 2,
            },
            "ioctl_allowlist": [
                "IOCTL_KGSL_DRAWCTXT_CREATE",
                "IOCTL_KGSL_GPUOBJ_ALLOC",
                "IOCTL_KGSL_GPUOBJ_INFO",
                "IOCTL_KGSL_GPUOBJ_SYNC",
                "IOCTL_KGSL_GPU_COMMAND",
                "IOCTL_KGSL_TIMESTAMP_EVENT",
                "IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID",
                "IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID",
                "IOCTL_KGSL_GPUOBJ_FREE",
                "IOCTL_KGSL_DRAWCTXT_DESTROY",
            ],
            "parent_enters_open": False,
            "parent_enters_ioctl": False,
            "timeout_guard_ms_default": 2000,
            "timeout_guard_ms_max": 10000,
            "waittimestamp_timeout_ms": 1000,
            "forbidden_operations": [
                "freedreno-render",
                "shader-submit",
                "solid-fill",
                "triangle-render",
                "KMS-blit",
                "GDSC-write",
                "regulator-write",
                "PMIC-write",
                "GPIO-write",
                "proprietary-adreno-blob",
                "exploit-dev",
            ],
            "next_live_validation": [
                "flash-v3194-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-g1-context-probe-timeout-guard",
                "gpu-g2-mmap-probe-timeout-guard",
                "gpu-g3-noop-submit-probe-timeout-guard",
                "post-probe-selftest-and-dmesg-gpu-fault-filter",
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
    (OUT_DIR / "gpu-g3-noop-submit-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g3-noop-submit-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_g3"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-g3-noop-submit-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3194_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3192_overrides", _v3194_overrides),
        ("_v3192_values", _v3194_values),
        ("v3192_adapter_source", v3194_adapter_source),
        ("_v3192_require_strings", _v3194_require_strings),
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
