#!/usr/bin/env python3
"""Build V3190 GPU G2a bounded KGSL GPU object alloc/free probe candidate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import repo_root
from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3188_gpu_g1_context_probe as base

REPO_ROOT = repo_root()
ORIG_V3188_OVERRIDES = base._v3188_overrides
ORIG_V3188_VALUES = base._v3188_values
ORIG_V3188_ADAPTER_SOURCE = base.v3188_adapter_source

CYCLE = "V3190"
INIT_VERSION = "0.11.23"
INIT_BUILD = "v3190-gpu-g2-gpuobj-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3190-gpu-g2-gpuobj-probe-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3190_GPU_G2_GPUOBJ_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3190_gpu_g2_gpuobj_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3190_gpu_g2_gpuobj_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3190_gpu_g2_gpuobj_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v556_gpu_g2_gpuobj_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3190"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3190.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3190.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3190"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3190-gpu-g2-gpuobj-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3190-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3190-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3190-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3190-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3190-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3190-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3190-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-g2-gpuobj-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-g2-gpuobj-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3188", "v3190")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3188", "v3190")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3188", "v3190")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3188", "v3190")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3188", "v3190")
SCALE_MARKER = base.SCALE_MARKER.replace("v3188", "v3190")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3188", "v3190")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3188", "v3190")
SFX_STREAM_MARKER = "a90.doomgeneric.v3190.audio=real-sfx-pcm-stream-gpu-g2-gpuobj-probe"
SOUND_MODE = "native-doom-sfx-gpu-g2-gpuobj-probe-v3190"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3190.c"
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
        b"gpu-g1-context-probe": b"gpu-g2-gpuobj-probe",
        b"a90-doomgeneric-v3188": b"a90-doomgeneric-v3190",
        b"a90.doomgeneric.v3188": b"a90.doomgeneric.v3190",
        b"v3188": b"v3190",
        b"V3188": b"V3190",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_G2_GPUOBJ_PROBE_MARKERS = (
    b"g2-gpuobj-probe",
    b"gpu.g2.gpuobj.version=1",
    b"gpu.g2.gpuobj.scope=kgsl-gpuobj-alloc-free-probe",
    b"gpu.g2.gpuobj.parent_enters_open=0",
    b"gpu.g2.gpuobj.parent_enters_ioctl=0",
    b"gpu.g2.gpuobj.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_free,drawctxt_destroy",
    b"gpu.g2.gpuobj.alloc_size=%llu",
    b"gpu.g2.gpuobj.mmap_attempted=0",
    b"gpu.g2.gpuobj.submit_attempted=0",
    b"gpu.g2.gpuobj.power_write_attempted=0",
    b"gpu.g2.gpuobj.result=%s",
    b"gpu.g2.gpuobj.alloc_rc=%d",
    b"gpu.g2.gpuobj.free_rc=%d",
    b"gpu.g2.gpuobj.total_elapsed_ms=%ld",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.23",
    b"v3190-gpu-g2-gpuobj-probe",
) + GPU_G2_GPUOBJ_PROBE_MARKERS


def _v3190_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3190 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g1-context-probe", "gpu-g2-gpuobj-probe")
    .replace("v3188", "v3190")
    .replace("V3188", "V3190")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3190_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3188_OVERRIDES())
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


def _v3190_values() -> dict[str, Any]:
    values = dict(ORIG_V3188_VALUES())
    values.update(_v3190_overrides())
    return values


def v3190_adapter_source() -> str:
    return (
        ORIG_V3188_ADAPTER_SOURCE()
        .replace("gpu-g1-context-probe", "gpu-g2-gpuobj-probe")
        .replace("real-sfx-pcm-stream-gpu-g1-context-probe",
                 "real-sfx-pcm-stream-gpu-g2-gpuobj-probe")
        .replace("v3188", "v3190")
        .replace("V3188", "V3190")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3190 GPU G2 GPUOBJ Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU G2a KGSL GPU object alloc/free probe.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds `gpu g2-gpuobj-probe`, a bounded child-only KGSL GPU object allocation/free probe.",
        "- The child sequence is `open` -> `DRAWCTXT_CREATE` -> `GPUOBJ_ALLOC` (4096 bytes, flags 0) -> `GPUOBJ_FREE` -> `DRAWCTXT_DESTROY` -> `close`.",
        "- Keeps V3188 `gpu g1-context-probe`, V3185 `gpu g0-fwclass-prepare`, and bounded G0 open probe available.",
        "- The parent never enters KGSL `open()` or `ioctl()`; it only enforces timeout and reports metadata.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- No mmap, command submit, freedreno rendering, or proprietary Adreno blob/EGL/Bionic path.",
        "- No GMU/GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- G2a probe must run only after G0 firmware-class prepare and G1 context-create have passed and post-flash health is clean.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3190 builder and focused tests.",
        "- `unittest`: V3190 GPU G2a source contract plus V3188/V3185/V3180 regression contracts.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3190 identity, G0/G1 markers, and G2a GPUOBJ probe markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-g2-gpuobj-probe-candidate`.",
    ]) + "\n"


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g2-gpuobj-probe-candidate",
        "adoption_state": "pending-gpu-g2-gpuobj-probe-live-validation",
        "gpu_g2a": {
            "source_baseline": "v3188-gpu-g1-context-probe",
            "g1_live_report": "docs/reports/NATIVE_INIT_V3189_GPU_G1_CONTEXT_PROBE_LIVE_2026-06-25.md",
            "commands": [
                "gpu g0-fwclass-prepare",
                "gpu g1-context-probe --timeout-ms 5000 --materialize-devnode",
                "gpu g2-gpuobj-probe --timeout-ms 5000 --materialize-devnode",
            ],
            "context_flags": "KGSL_CONTEXT_NO_GMEM_ALLOC|KGSL_CONTEXT_PREAMBLE|KGSL_CONTEXT_NO_SNAPSHOT|KGSL_CONTEXT_TYPE_GL",
            "gpuobj_alloc_size": 4096,
            "gpuobj_alloc_flags": "0x0",
            "ioctl_allowlist": [
                "IOCTL_KGSL_DRAWCTXT_CREATE",
                "IOCTL_KGSL_GPUOBJ_ALLOC",
                "IOCTL_KGSL_GPUOBJ_FREE",
                "IOCTL_KGSL_DRAWCTXT_DESTROY",
            ],
            "parent_enters_open": False,
            "parent_enters_ioctl": False,
            "timeout_guard_ms_default": 2000,
            "timeout_guard_ms_max": 10000,
            "forbidden_operations": [
                "kgsl-mmap",
                "kgsl-gpu-command",
                "kgsl-submit",
                "kgsl-gpuobj-import",
                "freedreno-render",
                "GDSC-write",
                "regulator-write",
                "PMIC-write",
                "GPIO-write",
                "proprietary-adreno-blob",
                "exploit-dev",
            ],
            "next_live_validation": [
                "flash-v3190-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-g1-context-probe-timeout-guard",
                "gpu-g2-gpuobj-probe-timeout-guard",
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
    (OUT_DIR / "gpu-g2-gpuobj-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-g2-gpuobj-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": [
            "gpu-g0-fwclass-prepare",
            "gpu-g1-context-probe-timeout-guard",
            "gpu-g2-gpuobj-probe-timeout-guard",
            "post-probe-selftest-and-dmesg-tail",
        ],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-g2-gpuobj-probe-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3190_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3188_overrides", _v3190_overrides),
        ("_v3188_values", _v3190_values),
        ("v3188_adapter_source", v3190_adapter_source),
        ("_v3188_require_strings", _v3190_require_strings),
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
