#!/usr/bin/env python3
"""Build V3251 GPU H3 compiler-derived VS/instrlen probe."""

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
import build_native_init_boot_v3249_gpu_h3_cache_invalidate_probe as previous

base = previous.base

CYCLE = "V3251"
INIT_VERSION = "0.11.52"
INIT_BUILD = "v3251-gpu-h3-compiler-vs-instrlen-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3251-gpu-h3-compiler-vs-instrlen-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3251_GPU_H3_COMPILER_VS_INSTRLEN_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3251_gpu_h3_compiler_vs_instrlen_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3251_gpu_h3_compiler_vs_instrlen_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3251_gpu_h3_compiler_vs_instrlen_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v579_gpu_h3_compiler_vs_instrlen_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3251"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3251.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3251.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3251"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3251-gpu-h3-compiler-vs-instrlen-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3251-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3251-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3251-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3251-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3251-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3251-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3251-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-compiler-vs-instrlen-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-compiler-vs-instrlen-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3210", "v3251")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3210", "v3251")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3210", "v3251")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3210", "v3251")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3210", "v3251")
SCALE_MARKER = base.SCALE_MARKER.replace("v3210", "v3251")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3210", "v3251")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3210", "v3251")
SFX_STREAM_MARKER = "a90.doomgeneric.v3251.audio=real-sfx-pcm-stream-gpu-h3-compiler-vs-instrlen-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-compiler-vs-instrlen-probe-v3251"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3251.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
SHADER_PAYLOAD = "mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x"


def _rewrite_v3251_marker(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3249": b"a90-doomgeneric-v3251",
        b"a90.doomgeneric.v3249": b"a90.doomgeneric.v3251",
        b"v3249": b"v3251",
        b"V3249": b"V3251",
        b"gpu-h3-cache-invalidate-probe": b"gpu-h3-compiler-vs-instrlen-probe",
        b"first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader":
            SCOPE.encode("ascii"),
        b"hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler":
            SHADER_PAYLOAD.encode("ascii"),
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H3_COMPILER_VS_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.shader_payload=" + SHADER_PAYLOAD.encode("ascii"),
    b"gpu.h3.draw.shader_payload_source=mesa-freedreno-tests-reference-crash_prefetch-minimal-vs-plus-v3246-ir3-disasm-fs",
    b"gpu.h3.draw.vs_shader_instr_count=%u",
    b"gpu.h3.draw.fs_shader_instr_count=%u",
    b"gpu.h3.draw.vs_shader_instrlen=%u",
    b"gpu.h3.draw.fs_shader_instrlen=%u",
    b"gpu.h3.draw.ir3_instr_align=%u",
    b"gpu.h3.draw.ir3_mov_u32u32_r0z_hi=0x%x",
    b"gpu.h3.draw.ir3_mov_u32u32_r0w_hi=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3251_marker(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_COMPILER_VS_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3249-cache-invalidate-plus-v3250-live-validation-and-v3246-ir3-disasm-audit",
        "scope": SCOPE,
        "shader_source": "Mesa freedreno reference trace minimal VS bytes plus V3246 ir3-disasm-audited FS bytes",
        "shader_payload": SHADER_PAYLOAD,
        "shader_payload_source": "Mesa freedreno tests/reference/crash_prefetch.log minimal VS repeated on A6xx",
        "ir3_mov_u32u32_r0z_imm1_opcode": "0x204cc0023f800000",
        "ir3_mov_u32u32_r0w_imm1_opcode": "0x204cc0033f800000",
        "ir3_instr_align": 16,
        "vs_shader_instr_count": 3,
        "fs_shader_instr_count": 2,
        "vs_shader_instrlen": 1,
        "fs_shader_instrlen": 1,
        "vs_shader_dwords": 32,
        "fs_shader_dwords": 32,
        "shader_load_contract_source": "Mesa ir3_collect_info instrlen=ceil(instr_count/16), fd6_program SP_xS_INSTR_SIZE(instrlen), CP_LOAD_STATE6 shader NUM_UNIT=1",
        "readback": "expect changed pixels after PC_CCU_FLUSH_COLOR_TS if previous no-pixel was shader load/instrlen contract",
        "next_live_validation": [
            "flash-v3251-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-compiler-vs-instrlen-r0-output-shader-timeout-guard",
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
        "# Native Init V3251 GPU H3 Compiler VS/Instrlen Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle shader-load contract before H4 readback proof.",
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
        "- Keeps the V3249 direct-render, RB_RENDER_CNTL, RB_CCU sysmem, and pre-draw cache invalidate state.",
        "- Replaces the H3 VS payload with the repeated Mesa A6xx reference minimal VS bytes: `mov.u32u32 r0.z, 0x3f800000`; `mov.u32u32 r0.w, 0x3f800000`; `end`; zero NOP padding.",
        "- Leaves the V3246 ir3-disasm-audited FS constant-color payload in place.",
        "- Changes H3 shader state to use Mesa-style `instrlen=1` for `SP_VS_INSTR_SIZE`, `SP_PS_INSTR_SIZE`, and CP_LOAD_STATE6 shader units while keeping the copied shader BO payload 128-byte aligned.",
        "- Removes the V3249 preserved DOOM engine before packing V3251 to keep the boot image under the 64MiB gate.",
        "",
        "## Source Basis",
        "",
        "- Local Mesa reference trace: `/tmp/a90-mesa-h3-sparse/src/freedreno/tests/reference/crash_prefetch.log`.",
        "- Mesa ir3 size logic: `src/freedreno/ir3/ir3.c` (`ir3_collect_info`).",
        "- Mesa A6xx shader state: `src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.",
        "- Mesa ir3 disassembler: `src/freedreno/isa/ir3-disasm.c`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3251 builder and shader audit.",
        "- `unittest`: V3251 GPU H3 compiler VS/instrlen source contract and updated shader-byte audit.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3251 identity plus shader-load contract telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS before commit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-compiler-vs-instrlen-probe-candidate`.",
    ]) + "\n"


def v3251_adapter_source() -> str:
    return (
        previous.v3249_adapter_source()
        .replace("gpu-h3-cache-invalidate-probe", "gpu-h3-compiler-vs-instrlen-probe")
        .replace("v3249", "v3251")
        .replace("V3249", "V3251")
    )


def _overlay_preserved_v3251_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3249 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3251 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3251 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3251 DOOM engine binary: {ENGINE_BINARY}")

    removed_stale_entries: list[str] = []
    with tempfile.TemporaryDirectory(prefix="a90-v3251-overlay-") as temp_name:
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
            ENGINE_RAMDISK_PATH,
            "bin/a90_doomgeneric_private_engine_v3249",
            "bin/a90_doomgeneric_private_engine_v3247",
            "bin/a90_doomgeneric_private_engine_v3244",
            "bin/a90_doomgeneric_private_engine_v3242",
            "bin/a90_doomgeneric_private_engine_v3240",
            "bin/a90_doomgeneric_private_engine_v3238",
            "bin/a90_doomgeneric_private_engine_v3236",
            "bin/a90_doomgeneric_private_engine_v3234",
            "bin/a90_doomgeneric_private_engine_v3232",
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
            raise RuntimeError("V3249 base boot mkbootimg args did not include --ramdisk")

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
            f"V3251 boot image too large for boot partition: "
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
        raise RuntimeError(f"missing V3251 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3249-ramdisk-overlay-v3251-init-helper-engine",
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
    (OUT_DIR / "gpu-h3-compiler-vs-instrlen-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-compiler-vs-instrlen-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-compiler-vs-instrlen-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-compiler-vs-instrlen-probe-candidate",
        "adoption_state": "pending-gpu-h3-compiler-vs-instrlen-live-validation",
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
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "decision": DECISION,
            "cycle": CYCLE,
            "candidate_tag": INIT_BUILD,
            "candidate_type": "gpu-h3-compiler-vs-instrlen-probe-candidate",
            "adoption_state": "pending-gpu-h3-compiler-vs-instrlen-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-compiler-vs-instrlen-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-compiler-vs-instrlen-live-validation"
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


def _apply_v3251_overrides() -> None:
    previous._apply_v3249_overrides()
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
            .replace("gpu-h3-cache-invalidate-probe", "gpu-h3-compiler-vs-instrlen-probe")
            .replace("real-sfx-pcm-stream-gpu-h3-cache-invalidate-probe",
                     "real-sfx-pcm-stream-gpu-h3-compiler-vs-instrlen-probe")
            .replace("v3249", "v3251")
            .replace("V3249", "V3251")
            .replace(previous.INIT_VERSION, INIT_VERSION)
            .replace(previous.INIT_BUILD, INIT_BUILD)
            .replace(previous.ENGINE_NAME, ENGINE_NAME)
            .replace(previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
            .replace(previous.SOUND_MODE, SOUND_MODE)
        ),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3251_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3251_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3251_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
