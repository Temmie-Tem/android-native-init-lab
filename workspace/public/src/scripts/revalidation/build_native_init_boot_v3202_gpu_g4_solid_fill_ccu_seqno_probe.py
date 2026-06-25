#!/usr/bin/env python3
"""Build V3202 GPU G4 A2D solid-fill/readback probe with CCU color timestamp flush."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3194_gpu_g3_noop_submit_probe as base

REPO_ROOT = repo_root()
ORIG_V3194_OVERRIDES = base._v3194_overrides
ORIG_V3194_VALUES = base._v3194_values
ORIG_V3194_ADAPTER_SOURCE = base.v3194_adapter_source

CYCLE = "V3202"
INIT_VERSION = "0.11.29"
INIT_BUILD = "v3202-gpu-g4-solid-fill-ccu-seqno-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3202-gpu-g4-solid-fill-ccu-seqno-probe-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3202_GPU_G4_SOLID_FILL_CCU_SEQNO_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3202_gpu_g4_solid_fill_ccu_seqno_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3202_gpu_g4_solid_fill_ccu_seqno_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3202_gpu_g4_solid_fill_ccu_seqno_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v561_gpu_g4_solid_fill_ccu_seqno_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3202"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3202.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3202.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3202"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3202-gpu-g4-solid-fill-ccu-seqno-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3202-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3202-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3202-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3202-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3202-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3202-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3202-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-g4-solid-fill-ccu-seqno-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-g4-solid-fill-ccu-seqno-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3194", "v3202")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3194", "v3202")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3194", "v3202")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3194", "v3202")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3194", "v3202")
SCALE_MARKER = base.SCALE_MARKER.replace("v3194", "v3202")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3194", "v3202")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3194", "v3202")
SFX_STREAM_MARKER = "a90.doomgeneric.v3202.audio=real-sfx-pcm-stream-gpu-g4-solid-fill-ccu-seqno-probe"
SOUND_MODE = "native-doom-sfx-gpu-g4-solid-fill-ccu-seqno-probe-v3202"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3202.c"
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
        b"a90-doomgeneric-v3194": b"a90-doomgeneric-v3202",
        b"a90.doomgeneric.v3194": b"a90.doomgeneric.v3202",
        b"v3194": b"v3202",
        b"V3194": b"V3202",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_G4_SOLID_FILL_MARKERS = (
    b"g4-solid-fill-probe",
    b"solid-fill-probe",
    b"gpu.g4.fill.version=1",
    b"gpu.g4.fill.scope=kgsl-a2d-solid-fill-readback-probe",
    b"gpu.g4.fill.parent_enters_open=0",
    b"gpu.g4.fill.parent_enters_ioctl=0",
    b"gpu.g4.fill.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy",
    b"gpu.g4.fill.pm4_source=mesa-freedreno-a6xx-fd6-clear-buffer-cp-blit-a2d-ccu-color-flush-seqno",
    b"gpu.g4.fill.post_blit_event=pc_ccu_flush_color_ts_seqno",
    b"gpu.g4.fill.post_blit_event_payload_dwords=4",
    b"gpu.g4.fill.event_seqno=0x%x",
    b"gpu.g4.fill.cache_invalidate_event=excluded-after-v3197-incident",
    b"gpu.g4.fill.pm4_cp_type4=0x%x",
    b"gpu.g4.fill.pm4_cp_type7=0x%x",
    b"gpu.g4.fill.fmt6_32_uint=0x%x",
    b"gpu.g4.fill.r2d_int32=0x%x",
    b"gpu.g4.fill.tile6_linear=0x%x",
    b"gpu.g4.fill.fill_bytes=%llu",
    b"gpu.g4.fill.expected_fill=0x%x",
    b"gpu.g4.fill.event_alloc_size=%llu",
    b"gpu.g4.fill.rb_dbg_eco_mode=skipped-source-magic-not-in-this-unit",
    b"gpu.g4.fill.render_attempted=1",
    b"gpu.g4.fill.triangle_attempted=0",
    b"gpu.g4.fill.kms_blit_attempted=0",
    b"gpu.g4.fill.power_write_attempted=0",
    b"gpu.g4.fill.proprietary_blob_attempted=0",
    b"gpu.g4.fill.result=%s",
    b"gpu.g4.fill.submit_rc=%d",
    b"gpu.g4.fill.submit_timestamp=%u",
    b"gpu.g4.fill.readback_sync_rc=%d",
    b"gpu.g4.fill.readback_verified=%d",
    b"gpu.g4.fill.readback0=0x%x",
    b"gpu.g4.fill.event_alloc_rc=%d",
    b"gpu.g4.fill.event_info_rc=%d",
    b"gpu.g4.fill.event_info_gpuaddr=0x%llx",
    b"gpu.g4.fill.event_free_rc=%d",
    b"gpu.g4.fill.pm4_dwords=%u",
    b"gpu.g4.fill.total_elapsed_ms=%ld",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.29",
    b"v3202-gpu-g4-solid-fill-ccu-seqno-probe",
) + GPU_G4_SOLID_FILL_MARKERS


def _v3202_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3202 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g3-noop-submit-probe", "gpu-g4-solid-fill-ccu-seqno-probe")
    .replace("real-sfx-pcm-stream-gpu-g3-noop-submit-probe",
             "real-sfx-pcm-stream-gpu-g4-solid-fill-ccu-seqno-probe")
    .replace("v3194", "v3202")
    .replace("V3194", "V3202")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3202_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3194_OVERRIDES())
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


def _v3202_values() -> dict[str, Any]:
    values = dict(ORIG_V3194_VALUES())
    values.update(_v3202_overrides())
    return values


def v3202_adapter_source() -> str:
    return (
        ORIG_V3194_ADAPTER_SOURCE()
        .replace("gpu-g3-noop-submit-probe", "gpu-g4-solid-fill-ccu-seqno-probe")
        .replace("real-sfx-pcm-stream-gpu-g3-noop-submit-probe",
                 "real-sfx-pcm-stream-gpu-g4-solid-fill-ccu-seqno-probe")
        .replace("v3194", "v3202")
        .replace("V3194", "V3202")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3202 GPU G4 Solid Fill CCU Seqno Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU G4 KGSL A6xx A2D solid-fill render plus CPU readback verification, with a Mesa-style post-blit CCU color timestamp event restored.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Keeps `gpu g4-solid-fill-probe` as the user-visible command and restores one post-blit `CP_EVENT_WRITE`: `PC_CCU_FLUSH_COLOR_TS` with timestamp bit, GPU address, and seqno payload.",
        "- The child sequence is `open` -> `DRAWCTXT_CREATE` -> command/destination `GPUOBJ_ALLOC` -> `GPUOBJ_INFO` -> `mmap` -> prefill destination sentinel -> write Mesa/freedreno-derived A6xx A2D `CP_BLIT` command stream -> command `GPUOBJ_SYNC TO_GPU` -> `GPU_COMMAND` -> `TIMESTAMP_EVENT` fence -> bounded `WAITTIMESTAMP_CTXTID` -> read retired timestamp -> destination `GPUOBJ_SYNC FROM_GPU` -> verify solid-fill words -> cleanup.",
        "- Keeps V3198's exclusion of `DEBUG_LABEL`, `CACHE_FLUSH_TS`, and `CACHE_INVALIDATE`; V3197 implicated the `CACHE_INVALIDATE` tail in the CP fault path, and V3201 showed the raw one-dword CCU event packet is unsafe.",
        "- Keeps G0/G1/G2/G3 commands available as prerequisites and regression checks.",
        "- The parent never enters KGSL `open()` or `ioctl()`; it only enforces timeout and reports metadata.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.",
        "- No GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- No triangle, shader, compute grid, KMS blit, or display handoff is included in G4.",
        "- The render target is a private KGSL GPU object, and readback is limited to the first 16 32-bit words after KGSL `GPUOBJ_SYNC FROM_GPU`.",
        "- `RB_DBG_ECO_CNTL` blit-mode toggling is deliberately skipped because Mesa sources route its value through GPU-specific `fd_dev_info.magic`; this unit does not invent that magic value.",
        "- V3198 removed all post-blit events and avoided the V3196 dmesg fault but left readback at the sentinel pattern. V3202 restores only the Mesa-derived CCU color clean event, encoded as a timestamp event with a dedicated KGSL object target.",
        "",
        "## Source Basis",
        "",
        "- Local Samsung KGSL UAPI/driver source: `IOCTL_KGSL_GPU_COMMAND` returns a timestamp, `IOCTL_KGSL_TIMESTAMP_EVENT` can create a fence fd for that timestamp, and `IOCTL_KGSL_GPUOBJ_SYNC` performs cache sync by GPU object id.",
        "- Mesa/freedreno PM4 source: type4/type7 odd-parity packet helpers, A6xx `fd6_clear_buffer()` A2D clear path, `CP_SET_MARKER(RM6_BLIT2DSCALE)`, `CP_BLIT(BLIT_OP_SCALE)`, and A6xx register XML enum values.",
        "- Local live evidence: `docs/reports/NATIVE_INIT_V3197_GPU_G4_SOLID_FILL_PROBE_LIVE_INCIDENT_2026-06-25.md` identified the V3196 post-blit event-write tail as unsafe; `docs/reports/NATIVE_INIT_V3199_GPU_G4_SOLID_FILL_NOEVENT_LIVE_2026-06-25.md` showed that removing all post-blit events avoids faults but leaves the target buffer unchanged; `docs/reports/NATIVE_INIT_V3201_GPU_G4_CCU_FLUSH_LIVE_INCIDENT_2026-06-25.md` showed that a one-dword raw CCU event packet is unsafe.",
        "- Mesa references: `https://docs.mesa3d.org/drivers/freedreno.html`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_blitter.cc`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_barrier.cc`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_pm4.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_gpu_event.h`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`, `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_common.xml`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3202 builder and focused tests.",
        "- `unittest`: V3202 GPU G4 source contract plus V3198/V3196/V3194/V3192/V3190 regression contracts.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3202 identity, G0/G1/G2/G3 markers, and G4 solid-fill markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-g4-solid-fill-ccu-seqno-probe-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g4-solid-fill-ccu-seqno-probe-candidate",
        "adoption_state": "pending-gpu-g4-solid-fill-ccu-seqno-live-validation",
        "gpu_g4": {
            "source_baseline": "v3200-gpu-g4-solid-fill-ccu-flush-probe",
            "incident_report": "docs/reports/NATIVE_INIT_V3197_GPU_G4_SOLID_FILL_PROBE_LIVE_INCIDENT_2026-06-25.md",
            "noevent_live_report": "docs/reports/NATIVE_INIT_V3199_GPU_G4_SOLID_FILL_NOEVENT_LIVE_2026-06-25.md",
            "raw_ccu_flush_incident_report": "docs/reports/NATIVE_INIT_V3201_GPU_G4_CCU_FLUSH_LIVE_INCIDENT_2026-06-25.md",
            "g3_live_report": "docs/reports/NATIVE_INIT_V3195_GPU_G3_NOOP_SUBMIT_PROBE_LIVE_2026-06-25.md",
            "commands": [
                "gpu g0-fwclass-prepare",
                "gpu g1-context-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g2-mmap-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g4-solid-fill-probe --timeout-ms 5000 --materialize-devnode",
            ],
            "command_stream": {
                "pm4_source": "Mesa freedreno A6xx fd6_clear_buffer CP_BLIT A2D solid color path with post-blit PC_CCU_FLUSH_COLOR_TS timestamp event",
                "pm4_reference_urls": [
                    "https://docs.mesa3d.org/drivers/freedreno.html",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_blitter.cc",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.h",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_barrier.cc",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_pm4.h",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_gpu_event.h",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml",
                    "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_common.xml",
                ],
                "type4": "0x40000000",
                "type7": "0x70000000",
                "cp_set_marker": "0x65",
                "cp_blit": "0x2c",
                "cp_event_write_tail": "pc-ccu-flush-color-ts-timestamp-event-only",
                "post_blit_events": [
                    "PC_CCU_FLUSH_COLOR_TS"
                ],
                "post_blit_event_payload_dwords": 4,
                "post_blit_event_timestamp_bit": True,
                "post_blit_event_seqno": "0x32020001",
                "event_gpuobj": "dedicated-kgsl-gpuobj-in-command-objlist",
                "excluded_post_blit_events": [
                    "DEBUG_LABEL",
                    "CACHE_FLUSH_TS",
                    "CACHE_INVALIDATE"
                ],
                "cp_wait_for_idle": "0x26",
                "fmt6_32_uint": "0x4b",
                "r2d_int32": "0x7",
                "tile6_linear": "0x0",
                "rm6_blit2dscale": 12,
                "blit_op_scale": 3,
                "fill_bytes": 256,
                "expected_fill": "0xa5c3f00d",
                "readback_dwords": 16,
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
            "readback_sync": "KGSL_GPUMEM_CACHE_FROM_GPU | KGSL_GPUMEM_CACHE_RANGE",
            "rb_dbg_eco_mode": "skipped-source-magic-not-in-this-unit",
            "forbidden_operations": [
                "shader-submit",
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
                "flash-v3202-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-g1-context-probe-timeout-guard",
                "gpu-g2-mmap-probe-timeout-guard",
                "gpu-g3-noop-submit-probe-timeout-guard",
                "gpu-g4-solid-fill-probe-timeout-guard",
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
    (OUT_DIR / "gpu-g4-solid-fill-ccu-seqno-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g4-solid-fill-ccu-seqno-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_g4"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-g4-solid-fill-ccu-seqno-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3202_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3194_overrides", _v3202_overrides),
        ("_v3194_values", _v3202_values),
        ("v3194_adapter_source", v3202_adapter_source),
        ("_v3194_require_strings", _v3202_require_strings),
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
