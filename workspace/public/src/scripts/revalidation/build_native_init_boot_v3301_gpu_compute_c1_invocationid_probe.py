#!/usr/bin/env python3
"""Build V3301 GPU compute C1 invocation-id UAV readback probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3297_gpu_h5_visual_triangle_hold_probe as previous

base = previous.base

CYCLE = "V3301"
INIT_VERSION = "0.11.75"
INIT_BUILD = "v3301-gpu-compute-c1-invocationid-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3301-gpu-compute-c1-invocationid-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3301_GPU_COMPUTE_C1_INVOCATIONID_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3301_gpu_compute_c1_invocationid_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3301_gpu_compute_c1_invocationid_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3301_gpu_compute_c1_invocationid_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v607_gpu_compute_c1_invocationid_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3301"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3301.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3301.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3301"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3301-gpu-compute-c1-invocationid-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3301-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3301-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3301-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3301-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3301-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3301-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3301-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-compute-c1-invocationid-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-compute-c1-invocationid-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3297", "v3301")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3297", "v3301")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3297", "v3301")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3297", "v3301")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3297", "v3301")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3297", "v3301")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3297", "v3301")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3297", "v3301"
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3301.audio=real-sfx-pcm-stream-gpu-compute-c1-invocationid-probe"
SOUND_MODE = "native-doom-sfx-gpu-compute-c1-invocationid-probe-v3301"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3301.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "visible-compute-c1-invocationid-uav-readback"
C1_COMMAND = "gpu c1-compute-invocationid-probe --timeout-ms 5000 --materialize-devnode"
SHADER_SHA256 = "7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a"
KERNEL_SHA256 = "1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a"


def _rewrite_v3301_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3297", "a90-doomgeneric-v3301"),
        ("a90.doomgeneric.v3297", "a90.doomgeneric.v3301"),
        ("v3297", "v3301"),
        ("V3297", "V3301"),
        ("gpu-h5-visual-triangle-hold-probe", "gpu-compute-c1-invocationid-probe"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3301_bytes(item: bytes) -> bytes:
    return _rewrite_v3301_text(item.decode("utf-8")).encode("utf-8")


GPU_C1_COMPUTE_MARKERS = (
    b"c1-compute-invocationid-probe",
    b"compute-invocationid-probe",
    b"gpu.c1.compute.scope=visible-compute-c1-invocationid-uav-readback",
    b"gpu.c1.compute.source=mesa-computerator-a6xx-kern_invocationid",
    b"gpu.c1.compute.shader_sha256=7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a",
    b"gpu.c1.compute.kernel_sha256=1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a",
    b"gpu.c1.compute.local_size=32,1,1",
    b"gpu.c1.compute.uav_words=%u",
    b"gpu.c1.compute.cp_exec_cs=0x%x",
    b"gpu.c1.compute.cp_set_marker=0x%x",
    b"gpu.c1.compute.sp_cs_const_config0=0x%x",
    b"gpu.c1.compute.expected_readback=0..31",
    b"gpu.c1.compute.result=invocationid-uav-readback-pass",
    b"gpu.c1.compute.readback31=%u",
    b"gpu.c1.compute.expected_match_count=%u",
    b"gpu.c1.compute.mismatch_count=%u",
    b"gpu.c1.compute.pass=%u",
    b"INVOCATIONID UAV READBACK",
)

REQUIRED_STRINGS = tuple(_rewrite_v3301_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_C1_COMPUTE_MARKERS


def _minimal_gpu_c1_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3300-compute-c1-verified-shader-bytes",
        "scope": SCOPE,
        "command": C1_COMMAND,
        "candidate_type": "gpu-compute-c1-invocationid-probe-candidate",
        "shader_sha256": SHADER_SHA256,
        "kernel_sha256": KERNEL_SHA256,
        "uav_words": 32,
        "expected_readback": list(range(32)),
        "cp_exec_cs": "0x33",
        "cp_set_marker": "RM6_COMPUTE",
        "kms_present_attempted": False,
        "proprietary_blob_attempted": False,
        "power_write_attempted": False,
        "next_live_validation": [
            "flash-v3301-through-native-init-flash",
            "post-flash-health-check",
            "gpu-c1-compute-invocationid-probe-timeout-guard",
            "uav-readback-buf-i-equals-i",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3301 GPU Compute C1 Invocationid Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU compute demo C1, first live compute dispatch/readback probe.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Embeds the V3300 verified FD640 `kern_invocationid.asm` CS words in native-init.",
        "- Adds `gpu c1-compute-invocationid-probe` with KGSL cmd/shader/UAV/descriptor/event objects.",
        "- Emits the Mesa computerator-style `SP_CS_*`, `LOAD_STATE6` shader/constants/UAV, `RM6_COMPUTE`, and `CP_EXEC_CS` sequence.",
        "- Verifies the 32-word UAV readback contract: `buf[i] == i` for `i=0..31`.",
        "",
        "## Safety",
        "",
        "- KGSL userspace path only; no KMS present in C1.",
        "- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3301 builder and focused source test.",
        "- `unittest`: V3301 C1 source contract plus V3300 shader-byte regression coverage.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3301 identity plus C1 compute readback telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        f"- Shader SHA256: `{SHADER_SHA256}`",
        f"- Kernel SHA256: `{KERNEL_SHA256}`",
        "- Candidate type: `gpu-compute-c1-invocationid-probe-candidate`.",
    ]) + "\n"


def v3301_adapter_source() -> str:
    return _rewrite_v3301_text(previous.v3297_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-compute-c1-invocationid-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-compute-c1-invocationid-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_c1"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-compute-c1-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_previous_builder_globals() -> list[tuple[Any, str, Any]]:
    replacements = {
        "BOOT_PARTITION_MAX_BYTES": BOOT_PARTITION_MAX_BYTES,
        "BASE_BOOT": BASE_BOOT,
        "BOOT_IMAGE": BOOT_IMAGE,
        "INIT_BINARY": INIT_BINARY,
        "RAMDISK_CPIO": RAMDISK_CPIO,
        "HELPER_BINARY": HELPER_BINARY,
        "ENGINE_BINARY": ENGINE_BINARY,
        "ENGINE_RAMDISK_PATH": ENGINE_RAMDISK_PATH,
    }
    saved: list[tuple[Any, str, Any]] = []
    for name, value in replacements.items():
        saved.append((previous, name, getattr(previous, name)))
        setattr(previous, name, value)
    return saved


def _restore_previous_builder_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3301_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_builder_globals()
    try:
        overlay = previous._overlay_preserved_v3297_ramdisk()
    finally:
        _restore_previous_builder_globals(saved)
    overlay["mode"] = "preserve-v3297-ramdisk-overlay-v3301-init-helper-engine"
    overlay["base_boot"] = base.rel(BASE_BOOT)
    overlay["base_boot_sha256"] = base.sha256_file(BASE_BOOT)
    overlay["overlay_entries"] = [
        "init",
        "bin/a90_android_execns_probe",
        ENGINE_RAMDISK_PATH,
    ]
    return overlay


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "decision": DECISION,
            "cycle": CYCLE,
            "candidate_tag": INIT_BUILD,
            "candidate_type": "gpu-compute-c1-invocationid-probe-candidate",
            "adoption_state": "pending-gpu-compute-c1-live-validation",
            "boot_image": base.rel(BOOT_IMAGE),
            "init_version": INIT_VERSION,
            "init_build": INIT_BUILD,
            "helper_sha256": base.sha256_file(HELPER_BINARY),
            "helper_flags": [],
            "init_extra_flags": [],
        }
    manifest["decision"] = DECISION
    manifest["cycle"] = CYCLE
    manifest["candidate_tag"] = INIT_BUILD
    manifest["candidate_type"] = "gpu-compute-c1-invocationid-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-compute-c1-live-validation"
    manifest["boot_image"] = base.rel(BOOT_IMAGE)
    manifest["init_version"] = INIT_VERSION
    manifest["init_build"] = INIT_BUILD
    manifest["boot_sha256"] = overlay["boot_sha256"]
    manifest["ramdisk_sha256"] = overlay["ramdisk_sha256"]
    manifest["ramdisk_overlay"] = overlay
    manifest["base_main_completed"] = base_main_completed
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    else:
        manifest.pop("base_main_error", None)
    manifest["gpu_c1"] = _minimal_gpu_c1_manifest()
    manifest["gpu_c1"]["ramdisk_overlay"] = overlay
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    _write_candidate_manifest(manifest)


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("base_main_error", None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-compute-c1-invocationid-probe-candidate",
        "adoption_state": "pending-gpu-compute-c1-live-validation",
        "gpu_c1": _minimal_gpu_c1_manifest(),
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
    _write_candidate_manifest(manifest)
    return manifest


def _apply_v3301_overrides() -> None:
    previous._apply_v3297_overrides()
    replacements = {
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
        "BASE_BOOT": BASE_BOOT,
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
        "AUDIO_CORUN_MODE": SOUND_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3301_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3301_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3301_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3301_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
