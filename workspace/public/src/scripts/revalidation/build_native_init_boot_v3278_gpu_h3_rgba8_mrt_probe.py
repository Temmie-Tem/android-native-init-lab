#!/usr/bin/env python3
"""Build V3278 GPU H3 RGBA8 MRT VPC-linkage probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3274_gpu_h3_clip_guardband_su_probe as previous

base = previous.base

CYCLE = "V3278"
INIT_VERSION = "0.11.65"
INIT_BUILD = "v3278-gpu-h3-rgba8-mrt-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3278-gpu-h3-rgba8-mrt-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3278_GPU_H3_RGBA8_MRT_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3278_gpu_h3_rgba8_mrt_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3278_gpu_h3_rgba8_mrt_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3278_gpu_h3_rgba8_mrt_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v600_gpu_h3_rgba8_mrt_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3278"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3278.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3278.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3278"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3278-gpu-h3-rgba8-mrt-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3278-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3278-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3278-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3278-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3278-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3278-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3278-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-rgba8-mrt-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-rgba8-mrt-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3274", "v3278")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3274", "v3278")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3274", "v3278")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3274", "v3278")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3274", "v3278")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3274", "v3278")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3274", "v3278")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3274", "v3278")
SFX_STREAM_MARKER = "a90.doomgeneric.v3278.audio=real-sfx-pcm-stream-gpu-h3-rgba8-mrt-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-rgba8-mrt-probe-v3278"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3278.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h3-rgba8-mrt-cffdump-diff-varying-ij-vpc-linkage-clip-guardband-su-rasterizer-a6xx-output-routing-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
PREVIOUS_SCOPE = previous.SCOPE
SHADER_PAYLOAD = "verified-ir3-vs-r0xy-to-r2-position-plus-r0-varying-and-cffdump-bary-fs"
RGBA8_MRT_SOURCE = "Mesa freedreno A640 cffdump sysmem triangle SP_PS_MRT0 RGBA8 MRT color-target diff"
COLOR_FORMAT_VALUE = "0x00000030"
RB_MRT0_BUF_INFO_VALUE = "0x00000030"
SP_PS_CNTL0_VALUE = "0x81500100"
SP_VS_CNTL0_VALUE = "0x80100180"
GRAS_CL_INTERP_CNTL_VALUE = "0x00000001"
RB_INTERP_CNTL_VALUE = "0x00000401"
VPC_VS_CNTL_VALUE = "0x00ff0408"
VPC_PS_CNTL_VALUE = "0xff01ff04"
SP_PS_INITIAL_TEX_LOAD_CNTL_VALUE = "0x00007fc0"
SP_PS_WAVE_CNTL_VALUE = "0x00000003"
SP_REG_PROG_ID_1_VALUE = "0xfcfcfc00"
SP_PS_OUTPUT_REG0_VALUE = "0x00000002"
SP_VS_OUTPUT_REG0_VALUE = "0x0f000f08"
SP_VS_VPC_DEST_REG0_VALUE = "0x00000400"
PC_MODE_CNTL_VALUE = "0x0000001f"
PC_VS_CNTL_VALUE = "0x00000008"
VFD_SIDEband_VALUE = "0xfc-invalid-sideband-regids"
CMD_MAX_DWORDS = 320


def _rewrite_v3278_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3274": b"a90-doomgeneric-v3278",
        b"a90.doomgeneric.v3274": b"a90.doomgeneric.v3278",
        b"v3274": b"v3278",
        b"V3274": b"V3278",
        b"gpu-h3-clip-guardband-su-probe": b"gpu-h3-rgba8-mrt-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
        b"gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x":
            b"gpu.h3.draw.shader_payload=verified-ir3-vs-r0xy-to-r2-position-plus-r0-varying-and-cffdump-bary-fs",
        b"gpu.h3.draw.shader_payload_source=mesa-freedreno-tests-reference-crash_prefetch-minimal-vs-plus-v3246-ir3-disasm-fs":
            b"gpu.h3.draw.shader_payload_source=mesa-ir3-disasm-verified-h3-mov-r2-plus-a640-cffdump-bary-f-frag-shader",
        b"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero":
            b"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-cffdump-varying-ij",
        b"gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-emit-vpc-position-only-siv":
            b"gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-cffdump-vpc-position-plus-four-varyings",
        b"gpu.h3.draw.vs_output_regid=0x%x":
            b"gpu.h3.draw.vs_position_output_regid=0x%x",
        b"gpu.h3.draw.sp_fullregfootprint=%u":
            b"gpu.h3.draw.sp_vs_fullregfootprint=%u",
        b"gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x%x":
            b"gpu.h3.draw.ir3_mov_f32f32_r2x_r0x_hi=0x%x",
        b"gpu.h3.draw.fs_color_f32_bits=0x%x":
            b"gpu.h3.draw.ir3_bary_f_r0z_ij0_hi=0x%x",
        b"gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x%x":
            b"gpu.h3.draw.ir3_mov_u32u32_r2z_hi=0x%x",
        b"gpu.h3.draw.ir3_mov_u32u32_r0w_hi=0x%x":
            b"gpu.h3.draw.ir3_mov_u32u32_r2w_hi=0x%x",
        b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-current-constant-fs-no-varyings":
            b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-varying-ij-persp-pixel",
        b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-rgba8-mrt-persp-pixel":
            b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-varying-ij-persp-pixel",
        b"gpu.h3.draw.offscreen=f32-linear-128x128":
            b"gpu.h3.draw.offscreen=rgba8-linear-128x128",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3278_text(text: str) -> str:
    for old, new in (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3274", "a90-doomgeneric-v3278"),
        ("a90.doomgeneric.v3274", "a90.doomgeneric.v3278"),
        ("v3274", "v3278"),
        ("V3274", "V3278"),
        ("gpu-h3-clip-guardband-su-probe", "gpu-h3-rgba8-mrt-probe"),
        (PREVIOUS_SCOPE, SCOPE),
        (
            "gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x",
            "gpu.h3.draw.shader_payload=verified-ir3-vs-r0xy-to-r2-position-plus-r0-varying-and-cffdump-bary-fs",
        ),
        (
            "gpu.h3.draw.shader_payload_source=mesa-freedreno-tests-reference-crash_prefetch-minimal-vs-plus-v3246-ir3-disasm-fs",
            "gpu.h3.draw.shader_payload_source=mesa-ir3-disasm-verified-h3-mov-r2-plus-a640-cffdump-bary-f-frag-shader",
        ),
        (
            "gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero",
            "gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-cffdump-varying-ij",
        ),
        (
            "gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-emit-vpc-position-only-siv",
            "gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-cffdump-vpc-position-plus-four-varyings",
        ),
        ("gpu.h3.draw.vs_output_regid=0x%x", "gpu.h3.draw.vs_position_output_regid=0x%x"),
        ("gpu.h3.draw.sp_fullregfootprint=%u", "gpu.h3.draw.sp_vs_fullregfootprint=%u"),
        ("gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x%x", "gpu.h3.draw.ir3_mov_f32f32_r2x_r0x_hi=0x%x"),
        ("gpu.h3.draw.fs_color_f32_bits=0x%x", "gpu.h3.draw.ir3_bary_f_r0z_ij0_hi=0x%x"),
        ("gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x%x", "gpu.h3.draw.ir3_mov_u32u32_r2z_hi=0x%x"),
        ("gpu.h3.draw.ir3_mov_u32u32_r0w_hi=0x%x", "gpu.h3.draw.ir3_mov_u32u32_r2w_hi=0x%x"),
        (
            "gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-current-constant-fs-no-varyings",
            "gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-varying-ij-persp-pixel",
        ),
        (
            "gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-rgba8-mrt-persp-pixel",
            "gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-varying-ij-persp-pixel",
        ),
        (
            "gpu.h3.draw.offscreen=f32-linear-128x128",
            "gpu.h3.draw.offscreen=rgba8-linear-128x128",
        ),
    ):
        text = text.replace(old, new)
    return text


GPU_H3_RGBA8_MRT_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.shader_payload=verified-ir3-vs-r0xy-to-r2-position-plus-r0-varying-and-cffdump-bary-fs",
    b"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-cffdump-varying-ij",
    b"gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-mrt0",
    b"gpu.h3.draw.sp_ps_mrt_reg0=0x%x",
    b"gpu.h3.draw.rb_mrt0_buf_info=0x%x",
    b"gpu.h3.draw.offscreen=rgba8-linear-128x128",
    b"gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
    b"gpu.h3.draw.sp_vs_fullregfootprint=%u",
    b"gpu.h3.draw.sp_ps_fullregfootprint=%u",
    b"gpu.h3.draw.sp_ps_cntl0=0x%x",
    b"gpu.h3.draw.gras_cl_interp_cntl=0x%x",
    b"gpu.h3.draw.rb_interp_cntl=0x%x",
    b"gpu.h3.draw.sp_ps_output_reg0=0x%x",
    b"gpu.h3.draw.sp_ps_output_reg1_7=0x%x",
    b"gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x%x",
    b"gpu.h3.draw.sp_ps_wave_cntl=0x%x",
    b"gpu.h3.draw.sp_reg_prog_id_1=0x%x",
    b"gpu.h3.draw.vpc_ps_cntl=0x%x",
    b"gpu.h3.draw.sp_vs_output_cntl=0x%x",
    b"gpu.h3.draw.sp_vs_output_reg0=0x%x",
    b"gpu.h3.draw.sp_vs_vpc_dest_reg0=0x%x",
    b"gpu.h3.draw.pc_mode_cntl=0x%x",
    b"gpu.h3.draw.pc_vs_cntl=0x%x",
    b"gpu.h3.draw.vfd_sideband_source=mesa-freedreno-a6xx-vfd-system-values-invalid-regids",
    b"gpu.h3.draw.vfd_cntl_1=0x%x",
    b"gpu.h3.draw.ir3_bary_f_r0z_ij0_hi=0x%x",
    b"gpu.h3.draw.ir3_bary_f_r1y_ij3_ei_hi=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3278_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_RGBA8_MRT_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3276-varying-ij-live-no-pixel-plus-a640-cffdump-rgba8-mrt-color-target-diff",
        "scope": SCOPE,
        "shader_payload": SHADER_PAYLOAD,
        "rgba8_mrt_source": RGBA8_MRT_SOURCE,
        "color_format": "FMT6_8_8_8_8_UNORM",
        "sp_vs_cntl0_value": SP_VS_CNTL0_VALUE,
        "sp_ps_cntl0_value": SP_PS_CNTL0_VALUE,
        "gras_cl_interp_cntl_value": GRAS_CL_INTERP_CNTL_VALUE,
        "rb_interp_cntl_value": RB_INTERP_CNTL_VALUE,
        "vpc_vs_cntl_value": VPC_VS_CNTL_VALUE,
        "vpc_ps_cntl_value": VPC_PS_CNTL_VALUE,
        "sp_ps_initial_tex_load_cntl_value": SP_PS_INITIAL_TEX_LOAD_CNTL_VALUE,
        "sp_ps_wave_cntl_value": SP_PS_WAVE_CNTL_VALUE,
        "sp_reg_prog_id_1_value": SP_REG_PROG_ID_1_VALUE,
        "sp_ps_output_reg0_value": SP_PS_OUTPUT_REG0_VALUE,
        "sp_vs_output_reg0_value": SP_VS_OUTPUT_REG0_VALUE,
        "sp_vs_vpc_dest_reg0_value": SP_VS_VPC_DEST_REG0_VALUE,
        "pc_mode_cntl_value": PC_MODE_CNTL_VALUE,
        "pc_vs_cntl_value": PC_VS_CNTL_VALUE,
        "vfd_sideband_value": VFD_SIDEband_VALUE,
        "color_format_value": COLOR_FORMAT_VALUE,
        "rb_mrt0_buf_info_value": RB_MRT0_BUF_INFO_VALUE,
        "offscreen": "rgba8-linear-128x128",
        "fragment_input_state_source": "Mesa freedreno A6xx fd6_program emit_fs_inputs cffdump varying/IJ path retained from V3276",
        "hlsq_round4_audit": "local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
        "state_reg_writes_expected": 118,
        "vfd_reg_writes_expected": 14,
        "pm4_dwords_expected": 306,
        "readback": "expect changed pixels if the previous FMT6_32_FLOAT MRT format blocked fd6 cffdump-style RGBA8 color routing",
        "next_live_validation": [
            "flash-v3278-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-rgba8-mrt-timeout-guard",
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
        "# Native Init V3278 GPU H3 RGBA8 MRT Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle cffdump RGBA8 MRT color-target probe before H4 readback proof.",
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
        "- Keeps the V3276 direct-render/sysmem/rasterizer/varying-IJ baseline intact.",
        "- Changes H3 MRT0 color target from `FMT6_32_FLOAT` (`0x4a`) to the A640 cffdump sysmem triangle format `FMT6_8_8_8_8_UNORM` (`0x30`).",
        "- Adds explicit telemetry for `color_format_source`, `SP_PS_MRT[0].REG`, `RB_MRT0_BUF_INFO`, and `offscreen=rgba8-linear-128x128`.",
        "- Does not emit speculative A6XX HLSQ program-control registers: the local A6XX XML/generated headers expose only HLSQ load-state/static unknowns, and the local cffdump triangle does not show a legacy HLSQ control block.",
        "- Expected PM4 size remains `306` dwords; expected 3D state register writes remain `118`; VFD draw-local writes remain `14`.",
        "",
        "## Source Basis",
        "",
        "- Local A640 cffdump sysmem triangle uses `SP_PS_MRT[0].REG=0x00000030` and `RB_MRT[0].BUF_INFO` color format `0x30` for the RGBA8 MRT0 color target.",
        "- Local cffdump and `fd6_program.cc` agree that `RB_PS_OUTPUT_CNTL=0` is normal when depth/samplemask/stencil are not written, while `SP_PS_OUTPUT_CNTL=0xfcfcfc00` and `RB/SP_PS_MRT_CNTL=1` are already present in H3.",
        "- The shader bytes and current color-format contract are checked by the updated H3 shader audit using the local Mesa `ir3-disasm` path when present.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3278 builder, shader audit, and focused source contract tests.",
        "- `unittest`: V3278 GPU H3 RGBA8 MRT source contract and H3 shader-byte audit.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3278 identity plus RGBA8 MRT telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-rgba8-mrt-probe-candidate`.",
    ]) + "\n"


def v3278_adapter_source() -> str:
    return _rewrite_v3278_text(previous.v3274_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-rgba8-mrt-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-rgba8-mrt-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-rgba8-mrt-live-validation",
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


def _overlay_preserved_v3278_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3274_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3268-ramdisk-overlay-v3278-init-helper-engine"
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
            "candidate_type": "gpu-h3-rgba8-mrt-probe-candidate",
            "adoption_state": "pending-gpu-h3-rgba8-mrt-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-rgba8-mrt-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-rgba8-mrt-live-validation"
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
        "candidate_type": "gpu-h3-rgba8-mrt-probe-candidate",
        "adoption_state": "pending-gpu-h3-rgba8-mrt-live-validation",
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


def _apply_v3278_overrides() -> None:
    previous._apply_v3274_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3278_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3278_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3278_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3278_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
