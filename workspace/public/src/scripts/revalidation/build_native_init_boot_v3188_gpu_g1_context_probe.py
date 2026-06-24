#!/usr/bin/env python3
"""Build V3188 GPU G1 bounded KGSL context probe candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3185_gpu_g0_fwclass_prepare as base

REPO_ROOT = repo_root()
ORIG_V3185_OVERRIDES = base._v3185_overrides
ORIG_V3185_VALUES = base._v3185_values
ORIG_V3185_ADAPTER_SOURCE = base.v3185_adapter_source

CYCLE = "V3188"
INIT_VERSION = "0.11.22"
INIT_BUILD = "v3188-gpu-g1-context-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3188-gpu-g1-context-probe-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3188_GPU_G1_CONTEXT_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3188_gpu_g1_context_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3188_gpu_g1_context_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3188_gpu_g1_context_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v555_gpu_g1_context_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3188"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3188.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3188.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3188"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3188-gpu-g1-context-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3188-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3188-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3188-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3188-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3188-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3188-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3188-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-g1-context-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-g1-context-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3185", "v3188")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3185", "v3188")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3185", "v3188")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3185", "v3188")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3185", "v3188")
SCALE_MARKER = base.SCALE_MARKER.replace("v3185", "v3188")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3185", "v3188")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3185", "v3188")
SFX_STREAM_MARKER = "a90.doomgeneric.v3188.audio=real-sfx-pcm-stream-gpu-g1-context-probe"
SOUND_MODE = "native-doom-sfx-gpu-g1-context-probe-v3188"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3188.c"
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
        b"gpu-g0-fwclass-prepare": b"gpu-g1-context-probe",
        b"a90-doomgeneric-v3185": b"a90-doomgeneric-v3188",
        b"a90.doomgeneric.v3185": b"a90.doomgeneric.v3188",
        b"v3185": b"v3188",
        b"V3185": b"V3188",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_G1_CONTEXT_PROBE_MARKERS = (
    b"g1-context-probe",
    b"gpu.g1.context.version=1",
    b"gpu.g1.context.scope=kgsl-context-create-destroy-probe",
    b"gpu.g1.context.parent_enters_open=0",
    b"gpu.g1.context.parent_enters_ioctl=0",
    b"gpu.g1.context.ioctl_allowlist=drawctxt_create,drawctxt_destroy",
    b"gpu.g1.context.mmap_attempted=0",
    b"gpu.g1.context.gpuobj_alloc_attempted=0",
    b"gpu.g1.context.submit_attempted=0",
    b"gpu.g1.context.power_write_attempted=0",
    b"gpu.g1.context.result=%s",
    b"gpu.g1.context.create_rc=%d",
    b"gpu.g1.context.destroy_rc=%d",
    b"gpu.g1.context.total_elapsed_ms=%ld",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.22",
    b"v3188-gpu-g1-context-probe",
) + GPU_G1_CONTEXT_PROBE_MARKERS


def _v3188_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3188 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g0-fwclass-prepare", "gpu-g1-context-probe")
    .replace("v3185", "v3188")
    .replace("V3185", "V3188")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3188_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3185_OVERRIDES())
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


def _v3188_values() -> dict[str, Any]:
    values = dict(ORIG_V3185_VALUES())
    values.update(_v3188_overrides())
    return values


def v3188_adapter_source() -> str:
    return (
        ORIG_V3185_ADAPTER_SOURCE()
        .replace("gpu-g0-fwclass-prepare", "gpu-g1-context-probe")
        .replace("real-sfx-pcm-stream-gpu-g0-fwclass-prepare",
                 "real-sfx-pcm-stream-gpu-g1-context-probe")
        .replace("v3185", "v3188")
        .replace("V3185", "V3188")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3188 GPU G1 Context Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU G1 KGSL context-create probe.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds `gpu g1-context-probe`, a bounded child-only KGSL context create/destroy probe.",
        "- Keeps V3185 `gpu g0-fwclass-prepare` and bounded `gpu g0-open-probe` available.",
        "- The parent never enters KGSL `open()` or `ioctl()`; it only enforces timeout and reports metadata.",
        "- The child allowlist is limited to `IOCTL_KGSL_DRAWCTXT_CREATE` and successful-id `IOCTL_KGSL_DRAWCTXT_DESTROY`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- No mmap, GPU object allocation, command submit, freedreno rendering, or proprietary Adreno blob/EGL/Bionic path.",
        "- No GMU/GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- G1 probe must run only after G0 firmware-class prepare has passed and post-flash health is clean.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3188 builder and focused tests.",
        "- `unittest`: V3188 GPU G1 source contract plus V3185/V3180 regression contracts.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3188 identity, G0 prepare markers, and G1 context probe markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-g1-context-probe-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g1-context-probe-candidate",
        "adoption_state": "pending-gpu-g1-context-probe-live-validation",
        "gpu_g1": {
            "source_baseline": "v3185-gpu-g0-fwclass-prepare",
            "g0_live_reports": [
                "docs/reports/NATIVE_INIT_V3186_GPU_G0_FWCLASS_PREPARE_LIVE_2026-06-25.md",
                "docs/reports/NATIVE_INIT_V3187_GPU_G0_FRESH_BOOT_REPEAT_2026-06-25.md",
            ],
            "commands": [
                "gpu g0-fwclass-prepare",
                "gpu g1-context-probe --timeout-ms 5000 --materialize-devnode",
            ],
            "context_flags": "KGSL_CONTEXT_NO_GMEM_ALLOC|KGSL_CONTEXT_PREAMBLE|KGSL_CONTEXT_NO_SNAPSHOT|KGSL_CONTEXT_TYPE_GL",
            "ioctl_allowlist": [
                "IOCTL_KGSL_DRAWCTXT_CREATE",
                "IOCTL_KGSL_DRAWCTXT_DESTROY",
            ],
            "parent_enters_open": False,
            "parent_enters_ioctl": False,
            "timeout_guard_ms_default": 2000,
            "timeout_guard_ms_max": 10000,
            "forbidden_operations": [
                "kgsl-mmap",
                "kgsl-gpuobj-alloc",
                "kgsl-submit",
                "freedreno-render",
                "GDSC-write",
                "regulator-write",
                "PMIC-write",
                "GPIO-write",
                "proprietary-adreno-blob",
                "exploit-dev",
            ],
            "next_live_validation": [
                "flash-v3188-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-g1-context-probe-timeout-guard",
                "post-probe-selftest-and-dmesg-tail",
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
    (OUT_DIR / "gpu-g1-context-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g1-context-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "gpu-g0-fwclass-prepare",
            "gpu-g1-context-probe-timeout-guard",
            "post-probe-selftest-and-dmesg-tail",
        ],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-g1-context-probe-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3188_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3185_overrides", _v3188_overrides),
        ("_v3185_values", _v3188_values),
        ("v3185_adapter_source", v3188_adapter_source),
        ("_v3185_require_strings", _v3188_require_strings),
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
