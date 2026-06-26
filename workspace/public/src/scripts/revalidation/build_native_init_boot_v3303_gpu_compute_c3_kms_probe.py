#!/usr/bin/env python3
"""Build V3303 GPU compute C3 KMS visual probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3302_gpu_compute_c2_pattern_probe as previous

base = previous.base

CYCLE = "V3303"
INIT_VERSION = "0.11.77"
INIT_BUILD = "v3303-gpu-compute-c3-kms-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3303-gpu-compute-c3-kms-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3303_GPU_COMPUTE_C3_KMS_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3303_gpu_compute_c3_kms_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3303_gpu_compute_c3_kms_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3303_gpu_compute_c3_kms_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v607_gpu_compute_c3_kms_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3303"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3303.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3303.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3303"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3303-gpu-compute-c3-kms-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3303-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3303-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3303-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3303-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3303-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3303-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3303-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-compute-c3-kms-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-compute-c3-kms-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3302", "v3303").replace("v3297", "v3303")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace(
    "v3302", "v3303"
).replace(
    "v3297", "v3303"
)
SFX_STREAM_MARKER = "a90.doomgeneric.v3303.audio=real-sfx-pcm-stream-gpu-compute-c3-kms-probe"
SOUND_MODE = "native-doom-sfx-gpu-compute-c3-kms-probe-v3303"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3303.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "visible-compute-c3-c2-uav-pattern-to-kms-held"
C3_COMMAND = "gpu c3-compute-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode"
SHADER_SHA256 = "9259cd6e225aba4d1e86fb88527494404617b2aaf753c948379ade2edb18a6d1"
ASM_SHA256 = "1f7f223c66a97975e416dce96b0a960933b7fa21b7bf4c6d380b3eb63e31b0d6"


def _rewrite_v3303_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3297", "a90-doomgeneric-v3303"),
        ("a90.doomgeneric.v3297", "a90.doomgeneric.v3303"),
        ("a90-doomgeneric-v3301", "a90-doomgeneric-v3303"),
        ("a90.doomgeneric.v3301", "a90.doomgeneric.v3303"),
        ("a90-doomgeneric-v3302", "a90-doomgeneric-v3303"),
        ("a90.doomgeneric.v3302", "a90.doomgeneric.v3303"),
        ("v3297", "v3303"),
        ("V3297", "V3303"),
        ("v3301", "v3303"),
        ("V3301", "V3303"),
        ("v3302", "v3303"),
        ("V3302", "V3303"),
        ("gpu-h5-visual-triangle-hold-probe", "gpu-compute-c3-kms-probe"),
        ("gpu-compute-c1-invocationid-probe", "gpu-compute-c3-kms-probe"),
        ("gpu-compute-c2-pattern-probe", "gpu-compute-c3-kms-probe"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3303_bytes(item: bytes) -> bytes:
    return _rewrite_v3303_text(item.decode("utf-8")).encode("utf-8")


GPU_C3_KMS_MARKERS = (
    b"c3-compute-kms-probe",
    b"compute-kms-probe",
    b"gpu.c3.kms.scope=visible-compute-c3-c2-uav-pattern-to-kms-held",
    b"gpu.c3.kms.compute_source=c2-workgroup-id-uav-readback-snapshot",
    b"gpu.c3.kms.blit_mode=c2-private-uav-snapshot-to-kms-dumb-framebuffer",
    b"gpu.c3.kms.result=compute-pattern-presented",
    b"gpu.c3.vis.result=compute-pattern-presented-held",
    b"gpu.c3.kms.snapshot_expected_match_count=%u",
    b"gpu.c3.kms.snapshot_mismatch_count=%u",
    b"gpu.c3.kms.snapshot_readback16383=%u",
    b"gpu.c2.compute.snapshot_write_rc=%d",
    b"gpu.c2.compute.snapshot_write_bytes=%llu",
    b"GPU C3 COMPUTE VISUAL",
    b"128X128 UAV PATTERN FROM GPU",
)

REQUIRED_STRINGS = tuple(_rewrite_v3303_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_C3_KMS_MARKERS


def _minimal_gpu_c3_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3302-compute-c2-pattern-live-readback-proof",
        "scope": SCOPE,
        "command": C3_COMMAND,
        "candidate_type": "gpu-compute-c3-kms-probe-candidate",
        "shader_sha256": SHADER_SHA256,
        "asm_sha256": ASM_SHA256,
        "uav_words": 16384,
        "pattern_width": 128,
        "pattern_height": 128,
        "expected_readback_samples": {
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3,
            "31": 31,
            "127": 127,
            "128": 128,
            "4096": 4096,
            "8192": 8192,
            "16383": 16383,
        },
        "cp_exec_cs": "0x33",
        "cp_set_marker": "RM6_COMPUTE",
        "kms_present_attempted": True,
        "proprietary_blob_attempted": False,
        "power_write_attempted": False,
        "next_live_validation": [
            "flash-v3303-through-native-init-flash",
            "post-flash-health-check",
            "gpu-c3-compute-kms-probe-timeout-and-hold-guard",
            "c2-uav-snapshot-readback-16384-workgroup-id-pattern",
            "kms-present-compute-pattern-held",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3303 GPU Compute C3 KMS Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU compute demo C3, C2 compute-output snapshot presented through KMS.",
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
        "- Extends the C2 compute probe to write a bounded 64KiB UAV snapshot after readback.",
        "- Adds `gpu c3-compute-kms-probe`, which runs C2, verifies the snapshot, expands it to a KMS dumb framebuffer, presents, and holds.",
        "- Keeps the compute proof on the Mesa-style `SP_CS_*`, `LOAD_STATE6`, `RM6_COMPUTE`, and `CP_EXEC_CS` sequence inherited from C2.",
        "- Verifies the 16384-word 128x128 UAV readback contract before KMS presentation.",
        "",
        "## Safety",
        "",
        "- KGSL userspace plus KMS present only; no panel re-init or power-domain write.",
        "- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, or forbidden partition work.",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3303 builder and focused source test.",
        "- `unittest`: V3303 C3 source contract plus C2 shader-byte coverage.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3303 identity plus C3 KMS visual telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        f"- Shader SHA256: `{SHADER_SHA256}`",
        f"- ASM SHA256: `{ASM_SHA256}`",
        "- Candidate type: `gpu-compute-c3-kms-probe-candidate`.",
    ]) + "\n"


def v3303_adapter_source() -> str:
    return _rewrite_v3303_text(previous.v3302_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-compute-c3-kms-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-compute-c3-kms-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_c3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-compute-c3-live-validation",
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


def _overlay_preserved_v3303_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_builder_globals()
    try:
        overlay = previous._overlay_preserved_v3302_ramdisk()
    finally:
        _restore_previous_builder_globals(saved)
    overlay["mode"] = "preserve-v3297-ramdisk-overlay-v3303-init-helper-engine"
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
            "candidate_type": "gpu-compute-c3-kms-probe-candidate",
            "adoption_state": "pending-gpu-compute-c3-live-validation",
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
    manifest["candidate_type"] = "gpu-compute-c3-kms-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-compute-c3-live-validation"
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
    manifest["gpu_c3"] = _minimal_gpu_c3_manifest()
    manifest["gpu_c3"]["ramdisk_overlay"] = overlay
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
        "candidate_type": "gpu-compute-c3-kms-probe-candidate",
        "adoption_state": "pending-gpu-compute-c3-live-validation",
        "gpu_c3": _minimal_gpu_c3_manifest(),
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


def _apply_v3303_overrides() -> None:
    previous._apply_v3302_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3303_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3303_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3303_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3303_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
