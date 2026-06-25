#!/usr/bin/env python3
"""Build V3247 GPU H3 RB render cntl probe."""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3244_gpu_h3_r0_output_probe as previous

base = previous.base

CYCLE = "V3247"
INIT_VERSION = "0.11.50"
INIT_BUILD = "v3247-gpu-h3-rb-render-cntl-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3247-gpu-h3-rb-render-cntl-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3247_GPU_H3_RB_RENDER_CNTL_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3247_gpu_h3_rb_render_cntl_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3247_gpu_h3_rb_render_cntl_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3247_gpu_h3_rb_render_cntl_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v579_gpu_h3_rb_render_cntl_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3247"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3247.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3247.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3247"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3247-gpu-h3-rb-render-cntl-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3247-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3247-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3247-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3247-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3247-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3247-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3247-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-rb-render-cntl-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-rb-render-cntl-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3210", "v3247")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3210", "v3247")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3210", "v3247")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3210", "v3247")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3210", "v3247")
SCALE_MARKER = base.SCALE_MARKER.replace("v3210", "v3247")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3210", "v3247")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3210", "v3247")
SFX_STREAM_MARKER = "a90.doomgeneric.v3247.audio=real-sfx-pcm-stream-gpu-h3-rb-render-cntl-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-rb-render-cntl-probe-v3247"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3247.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"


def _rewrite_v3247_marker(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3244": b"a90-doomgeneric-v3247",
        b"a90.doomgeneric.v3244": b"a90.doomgeneric.v3247",
        b"v3244": b"v3247",
        b"V3244": b"V3247",
        b"first-triangle-h3-r0-output-full-state-mov-f32-shader":
            b"first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H3_RB_RENDER_CNTL_MARKERS = (
    b"gpu.g0.materialize.fwclass_prepare_attempted=1",
    b"gpu.g0.materialize.fwclass_prepare_rc=%d",
    b"gpu.g0.fwclass_prepare.result=ok",
    b"gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader",
    b"gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map",
    b"gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler",
    b"gpu.h3.draw.vs_shader_dwords=%u",
    b"gpu.h3.draw.fs_shader_dwords=%u",
    b"gpu.h3.draw.vs_output_regid=0x%x",
    b"gpu.h3.draw.ps_output_regid=0x%x",
    b"gpu.h3.draw.sp_vs_output_reg0=0x%x",
    b"gpu.h3.draw.sp_fullregfootprint=%u",
    b"gpu.h3.draw.sample_location_source=mesa-freedreno-a6xx-fd6-context-sample-location-disable-stateobj",
    b"gpu.h3.draw.gras_sc_msaa_sample_pos_cntl=0x%x",
    b"gpu.h3.draw.rb_msaa_sample_pos_cntl=0x%x",
    b"gpu.h3.draw.tpl1_msaa_sample_pos_cntl=0x%x",
    b"gpu.h3.draw.render_marker_source=mesa-freedreno-a6xx-fd6-set-render-mode-rm6-direct-render",
    b"gpu.h3.draw.cp_set_marker=0x%x",
    b"gpu.h3.draw.rb_render_cntl_source=mesa-freedreno-a6xx-fd6-gmem-update-render-cntl-ccu-single-cacheline",
    b"gpu.h3.draw.rb_render_cntl=0x%x",
    b"gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2",
    b"gpu.h3.draw.rb_ccu_cntl=0x%x",
    b"gpu.h3.draw.rb_ccu_color_offset=0x%x",
    b"gpu.h3.draw.rb_ccu_depth_offset=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3247_marker(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_RB_RENDER_CNTL_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3244-r0-output-full-state-plus-v3246-shader-byte-audit",
        "command": "gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode",
        "scope": "first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader",
        "pm4_source": "Mesa freedreno A6xx fd6_draw direct CP_DRAW_INDX_OFFSET plus A6xx VFD register XML",
        "shader_source": "Mesa ir3 ISA XML hand encoding of cat1 mov.f32f32 plus cat0 end",
        "ir3_end_opcode": "0x0300000000000000",
        "ir3_mov_f32f32_r0x_r0x_opcode": "0x2004400000000000",
        "ir3_mov_f32f32_r0y_r0y_opcode": "0x2004400100000001",
        "ir3_mov_f32f32_r0x_opcode_hi": "0x20444000",
        "ir3_mov_f32f32_r0z_opcode_hi": "0x20444002",
        "ir3_mov_f32f32_r0w_opcode_hi": "0x20444003",
        "fs_color_f32_bits": "0x3f800000",
        "offscreen": "f32-linear-128x128",
        "color_format": "FMT6_32_FLOAT",
        "color_output_mask": "0xf",
        "vertex_format": "FMT6_32_32_FLOAT",
        "vertex_count": 3,
        "draw_attempted": True,
        "shader_payload": "hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler",
        "shader_output_source": "Mesa A6xx fd6 emit_vpc and emit_fs_outputs output regid maps",
        "vs_shader_dwords": 12,
        "fs_shader_dwords": 8,
        "vs_output_regid": "0x00",
        "ps_output_regid": "0x00",
        "sp_vs_output_reg0": "0x00000f00",
        "sp_fullregfootprint": 2,
        "shader_mode_source": "Mesa A6xx fd6 emit_shader_regs SP_MODE_CNTL and TPL1_MODE_CNTL",
        "sp_mode_cntl": "0x00000005",
        "tpl1_mode_cntl": "0x000000a2",
        "fragment_input_state_source": "Mesa A6xx fd6 emit_fs_inputs defaults for no-varying/no-fragcoord/no-sample fragment shader",
        "gras_cl_interp_cntl": "0x00000000",
        "rb_interp_cntl": "0x00000000",
        "rb_ps_input_cntl": "0x00000000",
        "rb_ps_samplefreq_cntl": "0x00000000",
        "gras_lrz_ps_input_cntl": "0x00000000",
        "gras_lrz_ps_samplefreq_cntl": "0x00000000",
        "vpc_lm_siv_source": "Mesa A6xx fd6 emit_vpc position-only linkage and SIV sentinels",
        "vpc_varying_lm_transfer_cntl0": "0xfffffff0",
        "vpc_varying_lm_transfer_cntl1": "0xffffffff",
        "vpc_varying_lm_transfer_cntl2": "0xffffffff",
        "vpc_varying_lm_transfer_cntl3": "0xffffffff",
        "vpc_vs_siv_cntl": "0x0000ffff",
        "vpc_vs_siv_cntl_v2": "0x0000ffff",
        "gras_su_vs_siv_cntl": "0x00000000",
        "static_context_source": "Mesa A6xx fd6_emit_static_context_regs no-op/disable defaults",
        "gras_su_conservative_ras_cntl": "0x00000000",
        "vpc_unknown_9210": "0x00000000",
        "vpc_so_override": "0x00000001",
        "vpc_rast_stream_cntl": "0x00000000",
        "pc_stereo_rendering_cntl": "0x00000000",
        "tpl1_ps_swizzle_cntl": "0x00000000",
        "sp_reg_prog_id_3": "0x0000fcfc",
        "state_reg_writes_expected": 92,
        "pm4_dwords_expected": 233,
        "sp_vs_cntl0": "0x00100100",
        "sp_ps_cntl0": "0x81000100",
        "sp_cntl0_source": "Mesa A6xx SP_VS_CNTL_0/SP_PS_CNTL_0 fullregfootprint=2 retained while probing RB render cntl regid, mergedregs, and FS inoutregoverlap fields",
        "raster_coverage_source": "Mesa A6xx GRAS/RB non-MSAA raster coverage defaults",
        "gras_sc_ras_msaa_cntl": "0x00000000",
        "gras_sc_dest_msaa_cntl": "0x00000004",
        "gras_sc_screen_scissor_cntl": "0x00000000",
        "sample_location_source": "Mesa A6xx fd6_context sample_locations_disable_stateobj",
        "gras_sc_msaa_sample_pos_cntl": "0x00000000",
        "rb_msaa_sample_pos_cntl": "0x00000000",
        "tpl1_msaa_sample_pos_cntl": "0x00000000",
        "render_marker_source": "Mesa A6xx fd6_set_render_mode CP_SET_MARKER RM6_DIRECT_RENDER",
        "cp_set_marker_opcode": "0x65",
        "cp_set_marker_payload": "0x00000001",
        "cp_set_marker_mode": "RM6_DIRECT_RENDER",
        "cp_set_marker_uses_gmem": False,
        "rb_render_cntl_source": "Mesa A6xx fd6_gmem update_render_cntl CCUSINGLECACHELINESIZE=2",
        "rb_render_cntl": "0x00000010",
        "rb_ccu_source": "Mesa A6xx fd6_emit_gmem_cache_cntl sysmem cache control",
        "rb_ccu_device_basis": "Adreno640v2 sysfs gpu_model plus Mesa GPUId(640) num_ccu=2",
        "rb_ccu_cntl": "0x10000000",
        "rb_ccu_color_offset": "0x00020000",
        "rb_ccu_depth_offset": "0x00000000",
        "vpc_linkage_source": "Mesa A6xx position/psizeloc and clip/cull sentinel linkage",
        "vpc_vs_cntl": "0x00ff0004",
        "vpc_vs_clip_cull_cntl": "0x00ffff00",
        "vpc_vs_clip_cull_cntl_v2": "0x00ffff00",
        "gras_cl_vs_clip_cull_distance": "0x00000000",
        "mrt_component_mask_source": "Mesa A6xx fd6 full RT0 component mask",
        "rb_ps_output_mask": "0x0000000f",
        "sp_ps_output_mask": "0x0000000f",
        "rb_mrt0_component_enable": "0x00000780",
        "shader_execution_attempted": True,
        "readback": "expect changed pixels after PC_CCU_FLUSH_COLOR_TS",
        "kms_blit_attempted": False,
        "parent_enters_open": False,
        "parent_enters_ioctl": False,
        "next_live_validation": [
            "flash-v3247-through-native-init-flash",
            "post-flash-health-check",
            "verify-fresh-boot-fwclass-path-before-h3",
            "gpu-h3-rb-render-cntl-r0-output-mov-f32-shader-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3247 GPU H3 RB_RENDER_CNTL Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle RB_RENDER_CNTL linkage before H4 readback proof.",
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
        "- Uses V3244 r0-output image as the preserved-ramdisk base and keeps the V3246 verified hand-assembled ir3 bytes unchanged.",
        "- Keeps the direct-render marker state: `CP_SET_MARKER` opcode `0x65` payload `0x00000001` immediately after the initial WFI and before H3 3D state.",
        "- Keeps the sysmem RB CCU cache-control state (`RB_CCU_CNTL=0x10000000`) derived from Adreno640v2 / Mesa `GPUId(640)` with `num_ccu=2`, color offset `0x20000`, and depth offset `0`.",
        "- Keeps the V3240 sample-location disable state, V3238 fresh-boot firmware-class materialize prep, and V3236 fullregfootprint=2 shader mode active.",
        "- Sets `RB_RENDER_CNTL=0x00000010`, matching Mesa A6xx `fd6_gmem.cc::update_render_cntl()` with `CCUSINGLECACHELINESIZE=2`.",
        "- Keeps VS/PS output regids at `0x00`, so telemetry should still show `sp_vs_output_reg0=0x00000f00`.",
        "- Expects H3 state emission to stay at 92 register writes and 233 PM4 dwords because this changes one existing register value.",
        "- Removes stale preserved-ramdisk DOOM engines before packing V3247 and gates the final boot image at 64MiB to protect the boot partition.",
        "- This isolates whether the no-pixel result is caused by the missing Mesa RB render-control CCU cacheline field before advancing to H4 interior/exterior readback proof.",
        "",
        "## Source Basis",
        "",
        "- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.",
        "- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.",
        "- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.",
        "- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.",
        "- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.",
        "- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.",
        "- A6xx PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml` (`CP_SET_MARKER`, `RM6_DIRECT_RENDER=1`).",
        "- Mesa/freedreno A6xx render-mode helper: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.h` (`fd6_set_render_mode`).",
        "- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`emit_shader_regs`, `emit_fs_inputs`, `emit_vpc`).",
        "- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.",
        "- Mesa/freedreno GMEM/CCU cache sizing helper: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/fd6_gmem_cache.h`.",
        "- Mesa/freedreno Adreno device table: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/common/freedreno_devices.py`.",
        "- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3247 builder and focused H3 source test.",
        "- `unittest`: V3247 GPU H3 RB render cntl source contract.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3247 identity plus RB render cntl H3 telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-rb-render-cntl-probe-candidate`.",
    ]) + "\n"


def v3247_adapter_source() -> str:
    return (
        base.ORIG_V3208_ADAPTER_SOURCE()
        .replace("gpu-h1-shader-state-probe", "gpu-h3-rb-render-cntl-probe")
        .replace("real-sfx-pcm-stream-gpu-h1-shader-state-probe",
                 "real-sfx-pcm-stream-gpu-h3-rb-render-cntl-probe")
        .replace("v3208", "v3247")
        .replace("V3208", "V3247")
    )


def _overlay_preserved_v3247_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3244 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3247 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3247 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3247 DOOM engine binary: {ENGINE_BINARY}")

    removed_stale_entries: list[str] = []
    with tempfile.TemporaryDirectory(prefix="a90-v3247-overlay-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_dir = temp_dir / "unpack"
        ramdisk_dir = temp_dir / "ramdisk"
        unpack_dir.mkdir()
        ramdisk_dir.mkdir()

        unpack_args_text = base._run(
            [
                "python3",
                base.THIRD_PARTY_MKBOOTIMG / "unpack_bootimg.py",
                "--boot_img",
                BASE_BOOT,
                "--out",
                unpack_dir,
                "--format=mkbootimg",
            ],
            capture=True,
        ).stdout
        mkboot_args = shlex.split(unpack_args_text)

        with (unpack_dir / "ramdisk").open("rb") as handle:
            subprocess.run(
                ["cpio", "-idm", "--no-absolute-filenames"],
                cwd=ramdisk_dir,
                check=True,
                stdin=handle,
                text=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        stale_paths = {
            previous.ENGINE_RAMDISK_PATH,
            "bin/a90_doomgeneric_private_engine_v3228",
            "bin/a90_doomgeneric_private_engine_v3226",
            "bin/a90_doomgeneric_private_engine_v3224",
            "bin/a90_doomgeneric_private_engine_v3222",
            "bin/a90_doomgeneric_private_engine_v3220",
            "bin/a90_doomgeneric_private_engine_v3218",
            "bin/a90_doomgeneric_private_engine_v3216",
            "bin/a90_doomgeneric_private_engine_v3214",
            "bin/a90_doomgeneric_private_engine_v3212",
        }
        for stale in sorted(stale_paths):
            stale_path = ramdisk_dir / stale
            if stale_path.exists() and stale != ENGINE_RAMDISK_PATH:
                stale_path.unlink()
                removed_stale_entries.append(stale)

        shutil.copy2(INIT_BINARY, ramdisk_dir / "init")
        (ramdisk_dir / "init").chmod(0o755)

        bin_dir = ramdisk_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HELPER_BINARY, bin_dir / "a90_android_execns_probe")
        (bin_dir / "a90_android_execns_probe").chmod(0o755)
        engine_dest = bin_dir / ENGINE_RAMDISK_PATH.split("/", 1)[1]
        shutil.copy2(ENGINE_BINARY, engine_dest)
        engine_dest.chmod(0o755)

        base._set_reproducible_mtime(ramdisk_dir)

        if RAMDISK_CPIO.exists():
            RAMDISK_CPIO.unlink()
        RAMDISK_CPIO.parent.mkdir(parents=True, exist_ok=True)
        base._run(
            [
                "bash",
                "-lc",
                "find . | LC_ALL=C sort | cpio --reproducible -o -H newc > "
                + shlex.quote(str(RAMDISK_CPIO)),
            ],
            cwd=ramdisk_dir,
        )
        RAMDISK_CPIO.chmod(0o600)

        for index, item in enumerate(mkboot_args):
            if item == "--ramdisk":
                mkboot_args[index + 1] = str(RAMDISK_CPIO)
                break
        else:
                raise RuntimeError("V3244 base boot mkbootimg args did not include --ramdisk")

        if BOOT_IMAGE.exists():
            BOOT_IMAGE.unlink()
        base._run(
            [
                "python3",
                base.THIRD_PARTY_MKBOOTIMG / "mkbootimg.py",
                *mkboot_args,
                "--output",
                BOOT_IMAGE,
            ]
        )
        BOOT_IMAGE.chmod(0o600)

    image_size = BOOT_IMAGE.stat().st_size
    if image_size > BOOT_PARTITION_MAX_BYTES:
        raise RuntimeError(
            f"V3247 boot image too large for boot partition: "
            f"{image_size} > {BOOT_PARTITION_MAX_BYTES}"
        )

    base._v3210_require_strings(BOOT_IMAGE)
    listing = base._run(
        ["bash", "-lc", "cpio -it < " + shlex.quote(str(RAMDISK_CPIO))],
        capture=True,
    ).stdout.splitlines()
    required_entries = {
        "init",
        "bin/a90_android_execns_probe",
        ENGINE_RAMDISK_PATH,
        "a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest",
    }
    missing_entries = sorted(required_entries.difference(listing))
    if missing_entries:
        raise RuntimeError(f"missing V3247 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3244-ramdisk-overlay-v3247-init-helper-engine",
        "base_boot": base.rel(BASE_BOOT),
        "base_boot_sha256": base.sha256_file(BASE_BOOT),
        "boot_sha256": base.sha256_file(BOOT_IMAGE),
        "boot_image_size": image_size,
        "boot_partition_max_bytes": BOOT_PARTITION_MAX_BYTES,
        "ramdisk_cpio": base.rel(RAMDISK_CPIO),
        "ramdisk_sha256": base.sha256_file(RAMDISK_CPIO),
        "overlay_entries": [
            "init",
            "bin/a90_android_execns_probe",
            ENGINE_RAMDISK_PATH,
        ],
        "removed_stale_entries": removed_stale_entries,
        "preserved_entries_checked": sorted(required_entries),
        "ramdisk_entry_count": len(listing),
    }


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-rb-render-cntl-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-rb-render-cntl-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-rb-render-cntl-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-rb-render-cntl-probe-candidate",
        "adoption_state": "pending-gpu-h3-rb-render-cntl-live-validation",
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


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    overlay = dict(overlay)
    overlay["mode"] = "preserve-v3244-ramdisk-overlay-v3247-init-helper-engine"
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "decision": DECISION,
            "cycle": CYCLE,
            "candidate_tag": INIT_BUILD,
            "candidate_type": "gpu-h3-rb-render-cntl-probe-candidate",
            "adoption_state": "pending-gpu-h3-rb-render-cntl-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-rb-render-cntl-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-rb-render-cntl-live-validation"
    manifest["boot_image"] = base.rel(BOOT_IMAGE)
    manifest["init_version"] = INIT_VERSION
    manifest["init_build"] = INIT_BUILD
    manifest["boot_sha256"] = overlay["boot_sha256"]
    manifest["ramdisk_sha256"] = overlay["ramdisk_sha256"]
    manifest["ramdisk_overlay"] = overlay
    manifest["base_main_completed"] = base_main_completed
    if base_main_error:
        manifest["base_main_error"] = base_main_error
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


def _apply_v3247_overrides() -> None:
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
        "SFX_BACKEND_SOURCE_TEXT": (
            base.SFX_BACKEND_SOURCE_TEXT
            .replace("gpu-h2-3d-state-probe", "gpu-h3-rb-render-cntl-probe")
            .replace("real-sfx-pcm-stream-gpu-h2-3d-state-probe",
                     "real-sfx-pcm-stream-gpu-h3-rb-render-cntl-probe")
            .replace("v3210", "v3247")
            .replace("V3210", "V3247")
            .replace(base.INIT_VERSION, INIT_VERSION)
            .replace(base.INIT_BUILD, INIT_BUILD)
            .replace(base.ENGINE_NAME, ENGINE_NAME)
            .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
            .replace(base.SOUND_MODE, SOUND_MODE)
        ),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3247_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3247_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3247_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
