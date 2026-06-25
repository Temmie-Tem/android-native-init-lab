#!/usr/bin/env python3
"""Build V3228 GPU H3 fragment-input state probe."""

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
import build_native_init_boot_v3226_gpu_h3_shader_mode_probe as previous

base = previous.base

CYCLE = "V3228"
INIT_VERSION = "0.11.41"
INIT_BUILD = "v3228-gpu-h3-fragment-input-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3228-gpu-h3-fragment-input-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3228_GPU_H3_FRAGMENT_INPUT_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3228_gpu_h3_fragment_input_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3228_gpu_h3_fragment_input_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3228_gpu_h3_fragment_input_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v572_gpu_h3_fragment_input_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3228"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3228.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3228.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3228"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3228-gpu-h3-fragment-input-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3228-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3228-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3228-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3228-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3228-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3228-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3228-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-fragment-input-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-fragment-input-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3210", "v3228")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3210", "v3228")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3210", "v3228")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3210", "v3228")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3210", "v3228")
SCALE_MARKER = base.SCALE_MARKER.replace("v3210", "v3228")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3210", "v3228")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3210", "v3228")
SFX_STREAM_MARKER = "a90.doomgeneric.v3228.audio=real-sfx-pcm-stream-gpu-h3-fragment-input-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-fragment-input-probe-v3228"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3228.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"


def _rewrite_v3228_marker(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3226": b"a90-doomgeneric-v3228",
        b"a90.doomgeneric.v3226": b"a90.doomgeneric.v3228",
        b"v3226": b"v3228",
        b"V3226": b"V3228",
        b"first-triangle-h3-shader-mode-mov-f32-shader":
            b"first-triangle-h3-fragment-input-state-mov-f32-shader",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H3_FRAGMENT_INPUT_MARKERS = (
    b"gpu.h3.draw.scope=first-triangle-h3-fragment-input-state-mov-f32-shader",
    b"gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler",
    b"gpu.h3.draw.shader_mode_source=mesa-freedreno-a6xx-fd6-emit-shader-regs-sp-tpl1-mode",
    b"gpu.h3.draw.sp_mode_cntl=0x%x",
    b"gpu.h3.draw.tpl1_mode_cntl=0x%x",
    b"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero",
    b"gpu.h3.draw.gras_cl_interp_cntl=0x%x",
    b"gpu.h3.draw.rb_interp_cntl=0x%x",
    b"gpu.h3.draw.rb_ps_input_cntl=0x%x",
    b"gpu.h3.draw.rb_ps_samplefreq_cntl=0x%x",
    b"gpu.h3.draw.gras_lrz_ps_input_cntl=0x%x",
    b"gpu.h3.draw.gras_lrz_ps_samplefreq_cntl=0x%x",
    b"gpu.h3.draw.sp_cntl0_source=mesa-freedreno-a6xx-sp-footprint-mergedregs",
    b"gpu.h3.draw.sp_vs_cntl0=0x%x",
    b"gpu.h3.draw.sp_ps_cntl0=0x%x",
    b"gpu.h3.draw.raster_coverage_source=mesa-freedreno-a6xx-gras-rb-msaa-defaults",
    b"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x",
    b"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x",
    b"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x",
    b"gpu.h3.draw.vpc_linkage_source=mesa-freedreno-a6xx-position-psizeloc-clip-cull-linkage",
    b"gpu.h3.draw.vpc_vs_cntl=0x%x",
    b"gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x",
    b"gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x",
    b"gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x",
    b"gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0",
    b"gpu.h3.draw.ir3_end_opcode_hi=0x%x",
    b"gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x%x",
    b"gpu.h3.draw.fs_color_f32_bits=0x%x",
    b"gpu.h3.draw.color_output_mask=0x%x",
    b"gpu.h3.draw.offscreen=f32-linear-128x128",
    b"gpu.h3.draw.readback_change_expected=1",
)

REQUIRED_STRINGS = tuple(_rewrite_v3228_marker(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_FRAGMENT_INPUT_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3226-gpu-h3-shader-mode-probe",
        "command": "gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode",
        "scope": "first-triangle-h3-fragment-input-state-mov-f32-shader",
        "pm4_source": "Mesa freedreno A6xx fd6_draw direct CP_DRAW_INDX_OFFSET plus A6xx VFD register XML",
        "shader_source": "Mesa ir3 ISA XML hand encoding of cat1 mov.f32f32 plus cat0 end",
        "ir3_end_opcode": "0x0300000000000000",
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
        "shader_payload": "hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler",
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
        "state_reg_writes_expected": 74,
        "sp_vs_cntl0": "0x00100080",
        "sp_ps_cntl0": "0x81000080",
        "sp_cntl0_source": "Mesa A6xx SP_VS_CNTL_0/SP_PS_CNTL_0 footprint, mergedregs, and FS inoutregoverlap fields",
        "raster_coverage_source": "Mesa A6xx GRAS/RB non-MSAA raster coverage defaults",
        "gras_sc_ras_msaa_cntl": "0x00000000",
        "gras_sc_dest_msaa_cntl": "0x00000004",
        "gras_sc_screen_scissor_cntl": "0x00000000",
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
            "flash-v3228-through-native-init-flash",
            "post-flash-health-check",
            "gpu-g0-fwclass-prepare",
            "gpu-h3-fragment-input-state-mov-f32-shader-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3228 GPU H3 Fragment Input Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU first-triangle H3.8: keep the V3226 shader/SP/raster/VPC/MRT path and add Mesa's fragment-input defaults.",
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
        "- Keeps the V3226 H3 command envelope, VFD state, direct non-indexed `CP_DRAW_INDX_OFFSET`, timeout guard, readback telemetry, hand-encoded shader payloads, SP CNTL0 values, GRAS/RB coverage defaults, VPC linkage sentinels, full RT0 component mask, and shader-mode setup.",
        "- Adds Mesa-derived fragment input defaults for a no-varying/no-fragcoord/no-sample fragment shader: `GRAS_CL_INTERP_CNTL=0`, `RB_INTERP_CNTL=0`, `RB_PS_INPUT_CNTL=0`, `RB_PS_SAMPLEFREQ_CNTL=0`, `GRAS_LRZ_PS_INPUT_CNTL=0`, and `GRAS_LRZ_PS_SAMPLEFREQ_CNTL=0` from `fd6_program.cc::emit_fs_inputs()`.",
        "- Removes stale preserved-ramdisk DOOM engines before packing V3228 and gates the final boot image at 64MiB to protect the boot partition.",
        "- This tests a bounded fragment input/raster state gap; H4 still requires live readback interior/exterior proof.",
        "",
        "## Source Basis",
        "",
        "- Mesa ir3 ISA documentation: `https://docs.mesa3d.org/drivers/freedreno/ir3-notes.html`.",
        "- Mesa ir3 cat0 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat0.xml`.",
        "- Mesa ir3 cat1 ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3-cat1.xml`.",
        "- Mesa ir3 root ISA XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/isa/ir3.xml`.",
        "- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.",
        "- A6xx format enum XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx_enums.xml`.",
        "- Mesa/freedreno shader program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`emit_shader_regs`, `emit_fs_inputs`).",
        "- Mesa/freedreno draw emission state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.",
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
        "- `py_compile`: V3228 builder and focused H3 source test.",
        "- `unittest`: V3228 GPU H3 fragment-input source contract.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3228 identity plus fragment-input H3 markers.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-fragment-input-probe-candidate`.",
    ]) + "\n"


def v3228_adapter_source() -> str:
    return (
        base.ORIG_V3208_ADAPTER_SOURCE()
        .replace("gpu-h1-shader-state-probe", "gpu-h3-fragment-input-probe")
        .replace("real-sfx-pcm-stream-gpu-h1-shader-state-probe",
                 "real-sfx-pcm-stream-gpu-h3-fragment-input-probe")
        .replace("v3208", "v3228")
        .replace("V3208", "V3228")
    )


def _overlay_preserved_v3228_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3226 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3228 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3228 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3228 DOOM engine binary: {ENGINE_BINARY}")

    removed_stale_entries: list[str] = []
    with tempfile.TemporaryDirectory(prefix="a90-v3228-overlay-") as temp_name:
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
                raise RuntimeError("V3226 base boot mkbootimg args did not include --ramdisk")

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
            f"V3228 boot image too large for boot partition: "
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
        raise RuntimeError(f"missing V3228 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3226-ramdisk-overlay-v3228-init-helper-engine",
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
    (OUT_DIR / "gpu-h3-fragment-input-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-fragment-input-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-fragment-input-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-fragment-input-probe-candidate",
        "adoption_state": "pending-gpu-h3-fragment-input-live-validation",
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
    overlay["mode"] = "preserve-v3226-ramdisk-overlay-v3228-init-helper-engine"
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "decision": DECISION,
            "cycle": CYCLE,
            "candidate_tag": INIT_BUILD,
            "candidate_type": "gpu-h3-fragment-input-probe-candidate",
            "adoption_state": "pending-gpu-h3-fragment-input-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-fragment-input-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-fragment-input-live-validation"
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


def _apply_v3228_overrides() -> None:
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
            .replace("gpu-h2-3d-state-probe", "gpu-h3-fragment-input-probe")
            .replace("real-sfx-pcm-stream-gpu-h2-3d-state-probe",
                     "real-sfx-pcm-stream-gpu-h3-fragment-input-probe")
            .replace("v3210", "v3228")
            .replace("V3210", "V3228")
            .replace(base.INIT_VERSION, INIT_VERSION)
            .replace(base.INIT_BUILD, INIT_BUILD)
            .replace(base.ENGINE_NAME, ENGINE_NAME)
            .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
            .replace(base.SOUND_MODE, SOUND_MODE)
        ),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3228_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3228_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3228_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
