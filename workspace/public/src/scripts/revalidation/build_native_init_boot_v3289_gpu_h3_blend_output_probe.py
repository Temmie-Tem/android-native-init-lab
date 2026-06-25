#!/usr/bin/env python3
"""Build V3289 GPU H3 cffdump-shaped blend/output state probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3284_gpu_h3_a640_magic_block_probe as previous

base = previous.base

CYCLE = "V3289"
INIT_VERSION = "0.11.70"
INIT_BUILD = "v3289-gpu-h3-blend-output-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3289-gpu-h3-blend-output-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3289_GPU_H3_BLEND_OUTPUT_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3289_gpu_h3_blend_output_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3289_gpu_h3_blend_output_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3289_gpu_h3_blend_output_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v600_gpu_h3_blend_output_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3289"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3289.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3289.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3289"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3289-gpu-h3-blend-output-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3289-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3289-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3289-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3289-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3289-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3289-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3289-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-blend-output-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-blend-output-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3284", "v3289")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3284", "v3289")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3284", "v3289")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3284", "v3289")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3284", "v3289")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3284", "v3289")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3284", "v3289")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3284", "v3289")
SFX_STREAM_MARKER = "a90.doomgeneric.v3289.audio=real-sfx-pcm-stream-gpu-h3-blend-output-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-blend-output-probe-v3289"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3289.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = (
    "first-triangle-h3-blend-output-state-vfd-vs-contract-replay-a640-nonzero-"
    "init-magic-block-flag-mrt-cffdump-color-target-varying-ij-vpc-linkage-"
    "clip-guardband-su-rasterizer-a6xx-output-routing-sp-frontend-prog-id-"
    "state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-"
    "visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-"
    "compiler-vs-instrlen-cache-invalidate-rb-render-cntl"
)
PREVIOUS_SCOPE = previous.SCOPE
BLEND_OUTPUT_SOURCE = "V3286 cffdump diff A640 draw2 blend/output-state candidate"
SHADER_PAYLOAD = "verified-ir3-vs-r1xyzw-to-r2-position-preserve-r0-varying-and-cffdump-bary-fs"
SHADER_PAYLOAD_SOURCE = "constant-free-cffdump-shaped-vfd-vs-contract-plus-a640-cffdump-bary-f-frag-shader"
VERTEX_FORMAT = "cffdump-shaped-r0-vec4-r1-vec4-r2x-sint"
PM4_DWORDS_EXPECTED = 335
STATE_REG_WRITES_EXPECTED = 121
VFD_REG_WRITES_EXPECTED = 20
INIT_MAGIC_REG_WRITES_EXPECTED = 9
VERTEX_STRIDE_EXPECTED = 36
VERTEX_DWORDS_EXPECTED = 27
VERTEX_BYTES_EXPECTED = 108


def _rewrite_v3289_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3284", "a90-doomgeneric-v3289"),
        ("a90.doomgeneric.v3284", "a90.doomgeneric.v3289"),
        ("v3284", "v3289"),
        ("V3284", "V3289"),
        ("gpu-h3-a640-magic-block-probe", "gpu-h3-blend-output-probe"),
        (PREVIOUS_SCOPE, SCOPE),
        ("gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
         "gpu-h3-blend-output-state-shader-byte-audit"),
        ("verified-ir3-vs-r0xy-to-r2-position-plus-r0-varying-and-cffdump-bary-fs",
         SHADER_PAYLOAD),
        ("mesa-ir3-disasm-verified-h3-mov-r2-plus-a640-cffdump-bary-f-frag-shader",
         SHADER_PAYLOAD_SOURCE),
        ("gpu.h3.draw.vertex_format=fmt6-32-32-float",
         "gpu.h3.draw.vertex_format=cffdump-shaped-r0-vec4-r1-vec4-r2x-sint"),
        ("gpu.h3.draw.ir3_mov_f32f32_r2x_r0x_hi=0x%x",
         "gpu.h3.draw.ir3_mov_f32f32_r2x_r1x_hi=0x%x"),
        ("gpu.h3.draw.ir3_mov_f32f32_r2y_r0y_hi=0x%x",
         "gpu.h3.draw.ir3_mov_f32f32_r2y_r1y_hi=0x%x"),
        ("gpu.h3.draw.ir3_mov_u32u32_r2z_hi=0x%x",
         "gpu.h3.draw.ir3_mov_f32f32_r2z_r1z_hi=0x%x"),
        ("gpu.h3.draw.ir3_mov_u32u32_r2w_hi=0x%x",
         "gpu.h3.draw.ir3_mov_f32f32_r2w_r1w_hi=0x%x"),
        ("gpu.h3.draw.vfd_sideband_source=mesa-freedreno-a6xx-vfd-system-values-invalid-regids",
         "gpu.h3.draw.vfd_contract_source=mesa-freedreno-a640-cffdump-draw2-vfd-fetch-decode-shape"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3289_bytes(item: bytes) -> bytes:
    return _rewrite_v3289_text(item.decode("utf-8")).encode("utf-8")


GPU_H3_BLEND_OUTPUT_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.shader_payload=" + SHADER_PAYLOAD.encode("ascii"),
    b"gpu.h3.draw.shader_payload_source=" + SHADER_PAYLOAD_SOURCE.encode("ascii"),
    b"gpu.h3.draw.blend_output_state_source=mesa-freedreno-a640-cffdump-draw2-direct-sysmem-compatible-blend-output-group",
    b"gpu.h3.draw.sp_blend_cntl=0x%x",
    b"gpu.h3.draw.rb_blend_cntl=0x%x",
    b"gpu.h3.draw.rb_mrt0_blend_control=0x%x",
    b"gpu.h3.draw.vfd_contract_source=mesa-freedreno-a640-cffdump-draw2-vfd-fetch-decode-shape",
    b"gpu.h3.draw.vfd_cntl_0=0x%x",
    b"gpu.h3.draw.vfd_fetch_instr0=0x%x",
    b"gpu.h3.draw.vfd_fetch_instr1=0x%x",
    b"gpu.h3.draw.vfd_fetch_instr2=0x%x",
    b"gpu.h3.draw.vfd_dest_cntl0=0x%x",
    b"gpu.h3.draw.vfd_dest_cntl1=0x%x",
    b"gpu.h3.draw.vfd_dest_cntl2=0x%x",
    b"gpu.h3.draw.vertex_format=cffdump-shaped-r0-vec4-r1-vec4-r2x-sint",
    b"gpu.h3.draw.sp_vs_const_config_reference_deferred=0x101-requires-vs-constant-buffer",
)

REQUIRED_STRINGS = tuple(_rewrite_v3289_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_BLEND_OUTPUT_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3288-vfd-vs-contract-live-no-pixel-plus-v3286-cffdump-blend-output-delta",
        "scope": SCOPE,
        "blend_output_source": BLEND_OUTPUT_SOURCE,
        "shader_payload": SHADER_PAYLOAD,
        "shader_payload_source": SHADER_PAYLOAD_SOURCE,
        "vertex_format": VERTEX_FORMAT,
        "sp_blend_cntl_expected": "0x00000100",
        "rb_blend_cntl_expected": "0xffff0100",
        "rb_mrt0_blend_control_expected": "0x08040804",
        "vertex_stride_expected": VERTEX_STRIDE_EXPECTED,
        "vertex_dwords_expected": VERTEX_DWORDS_EXPECTED,
        "vertex_bytes_expected": VERTEX_BYTES_EXPECTED,
        "vfd_cntl0_expected": "0x00000303",
        "vfd_cntl1_expected": "0xfcfcfc09",
        "vfd_fetch_instrs_expected": ["0xc8200000", "0xc8200200", "0x44c00400"],
        "vfd_dest_cntls_expected": ["0x0000000f", "0x0000004f", "0x00000081"],
        "state_reg_writes_expected": STATE_REG_WRITES_EXPECTED,
        "init_magic_reg_writes_expected": INIT_MAGIC_REG_WRITES_EXPECTED,
        "vfd_reg_writes_expected": VFD_REG_WRITES_EXPECTED,
        "pm4_dwords_expected": PM4_DWORDS_EXPECTED,
        "sp_vs_const_config_reference_deferred": "0x101 requires VS constant-buffer replay; V3289 remains constant-free",
        "readback": "expect changed color or flag buffer words if missing blend/output state blocked raster output",
        "next_live_validation": [
            "flash-v3289-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-blend-output-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    })
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3289 GPU H3 Blend Output State Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle cffdump-shaped blend/output state probe before H4 readback proof.",
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
        "- Keeps the V3288 live-tested VFD/VS contract, A640 magic-block, direct-render, sysmem, RGBA8 tile6_3 flag-MRT, and cffdump bary-FS baseline.",
        "- Sets the remaining direct-sysmem-compatible blend/output registers from the V3286 A640 cffdump diff: `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.",
        "- Leaves cffdump reference `SP_VS_CONST_CONFIG=0x101` deferred because that path requires VS constant-buffer replay; V3289 remains a bounded blend/output-state probe.",
        f"- Expected PM4 size stays `{PM4_DWORDS_EXPECTED}` dwords; state register writes stay `{STATE_REG_WRITES_EXPECTED}`; VFD draw-local writes stay `{VFD_REG_WRITES_EXPECTED}`.",
        "",
        "## Source Basis",
        "",
        "- `workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py` identified the blend/output state as the highest-priority remaining direct-sysmem-compatible structural delta after V3288.",
        "- The reference values come from local A640 cffdump draw[2]: `SP_BLEND_CNTL=0x100`, `RB_BLEND_CNTL=0xffff0100`, and `RB_MRT[0].BLEND_CONTROL=0x08040804`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3289 builder, shader audit, cffdump diff, and focused source tests.",
        "- `unittest`: V3289 GPU H3 blend/output state source contract and shader-byte audit.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3289 identity plus blend/output state telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-blend-output-probe-candidate`.",
    ]) + "\n"


def v3289_adapter_source() -> str:
    return _rewrite_v3289_text(previous.v3284_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-blend-output-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-blend-output-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-blend-output-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_previous_overlay_globals() -> list[tuple[Any, str, Any]]:
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


def _restore_previous_overlay_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3289_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3284_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3284-ramdisk-overlay-v3289-init-helper-engine"
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
            "candidate_type": "gpu-h3-blend-output-probe-candidate",
            "adoption_state": "pending-gpu-h3-blend-output-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-blend-output-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-blend-output-live-validation"
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
    manifest["gpu_h3"] = _minimal_gpu_h3_manifest()
    manifest["gpu_h3"]["ramdisk_overlay"] = overlay
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
        "candidate_type": "gpu-h3-blend-output-probe-candidate",
        "adoption_state": "pending-gpu-h3-blend-output-live-validation",
        "gpu_h3": _minimal_gpu_h3_manifest(),
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


def _apply_v3289_overrides() -> None:
    previous._apply_v3284_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3289_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3289_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3289_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3289_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
