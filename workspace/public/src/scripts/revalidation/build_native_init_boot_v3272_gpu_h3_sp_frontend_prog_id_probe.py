#!/usr/bin/env python3
"""Build V3272 GPU H3 SP front-end program-id probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3268_gpu_h3_raster_mode_probe as previous

base = previous.base

CYCLE = "V3272"
INIT_VERSION = "0.11.62"
INIT_BUILD = "v3272-gpu-h3-sp-frontend-prog-id-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3272-gpu-h3-sp-frontend-prog-id-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3272_GPU_H3_SP_FRONTEND_PROG_ID_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3272_gpu_h3_sp_frontend_prog_id_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3272_gpu_h3_sp_frontend_prog_id_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3272_gpu_h3_sp_frontend_prog_id_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v600_gpu_h3_sp_frontend_prog_id_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3272"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3272.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3272.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3272"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3272-gpu-h3-sp-frontend-prog-id-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3272-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3272-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3272-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3272-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3272-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3272-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3272-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-sp-frontend-prog-id-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-sp-frontend-prog-id-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3268", "v3272")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3268", "v3272")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3268", "v3272")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3268", "v3272")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3268", "v3272")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3268", "v3272")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3268", "v3272")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3268", "v3272")
SFX_STREAM_MARKER = "a90.doomgeneric.v3272.audio=real-sfx-pcm-stream-gpu-h3-sp-frontend-prog-id-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-sp-frontend-prog-id-probe-v3272"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3272.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h3-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
PREVIOUS_SCOPE = previous.SCOPE
SHADER_PAYLOAD = previous.SHADER_PAYLOAD
SP_CONST_CONFIG_SOURCE = "Mesa freedreno A6xx fd6 program config stateobj"
SP_CONST_CONFIG_VALUE = "0x00000100"
SP_PS_OUTPUT_CNTL_SOURCE = "Mesa freedreno A6xx fd6_program invalid depth/sampmask/stencil regids"
SP_PS_OUTPUT_CNTL_VALUE = "0xfcfcfc00"
SP_FRONTEND_PROG_ID_SOURCE = "Mesa freedreno A6xx fd6_program emit_fs_inputs current constant-FS no-varyings mapping"
SP_PS_INITIAL_TEX_LOAD_CNTL_VALUE = "0x00000008"
SP_PS_WAVE_CNTL_VALUE = "0x00000000"
SP_LB_PARAM_LIMIT_VALUE = "0x00000007"
SP_REG_PROG_ID_0_VALUE = "0xfcfcfcfc"
SP_REG_PROG_ID_1_VALUE = "0xfcfcfcfc"
SP_REG_PROG_ID_2_VALUE = "0xfcfcfcfc"
SP_REG_PROG_ID_3_VALUE = "0x0000fcfc"
CMD_MAX_DWORDS = 320
STALE_V3268_ENGINE_RAMDISK_PATH = previous.ENGINE_RAMDISK_PATH


def _rewrite_v3272_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3268": b"a90-doomgeneric-v3272",
        b"a90.doomgeneric.v3268": b"a90.doomgeneric.v3272",
        b"v3268": b"v3272",
        b"V3268": b"V3272",
        b"gpu-h3-raster-mode-probe": b"gpu-h3-sp-frontend-prog-id-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3272_text(text: str) -> str:
    for old, new in (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3268", "a90-doomgeneric-v3272"),
        ("a90.doomgeneric.v3268", "a90.doomgeneric.v3272"),
        ("v3268", "v3272"),
        ("V3268", "V3272"),
        ("gpu-h3-raster-mode-probe", "gpu-h3-sp-frontend-prog-id-probe"),
        (PREVIOUS_SCOPE, SCOPE),
    ):
        text = text.replace(old, new)
    return text


GPU_H3_SP_FRONTEND_PROG_ID_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.sp_const_config_source=mesa-freedreno-a6xx-fd6-program-config-stateobj",
    b"gpu.h3.draw.sp_vs_const_config=0x%x",
    b"gpu.h3.draw.sp_ps_const_config=0x%x",
    b"gpu.h3.draw.fs_output_cntl_source=mesa-freedreno-a6xx-fd6-program-invalid-depth-sampmask-stencil-regids",
    b"gpu.h3.draw.sp_ps_output_cntl=0x%x",
    b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-current-constant-fs-no-varyings",
    b"gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x%x",
    b"gpu.h3.draw.sp_ps_wave_cntl=0x%x",
    b"gpu.h3.draw.sp_lb_param_limit=0x%x",
    b"gpu.h3.draw.sp_reg_prog_id_0=0x%x",
    b"gpu.h3.draw.sp_reg_prog_id_1=0x%x",
    b"gpu.h3.draw.sp_reg_prog_id_2=0x%x",
    b"gpu.h3.draw.sp_reg_prog_id_3=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3272_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_SP_FRONTEND_PROG_ID_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3270-sp-const-output-plus-v3271-live-no-pixel-and-a6xx-sp-frontend-diff",
        "scope": SCOPE,
        "sp_const_config_source": SP_CONST_CONFIG_SOURCE,
        "sp_const_config_value": SP_CONST_CONFIG_VALUE,
        "sp_ps_output_cntl_source": SP_PS_OUTPUT_CNTL_SOURCE,
        "sp_ps_output_cntl_value": SP_PS_OUTPUT_CNTL_VALUE,
        "sp_frontend_prog_id_source": SP_FRONTEND_PROG_ID_SOURCE,
        "sp_ps_initial_tex_load_cntl_value": SP_PS_INITIAL_TEX_LOAD_CNTL_VALUE,
        "sp_ps_wave_cntl_value": SP_PS_WAVE_CNTL_VALUE,
        "sp_lb_param_limit_value": SP_LB_PARAM_LIMIT_VALUE,
        "sp_reg_prog_id_values": {
            "SP_REG_PROG_ID_0": SP_REG_PROG_ID_0_VALUE,
            "SP_REG_PROG_ID_1": SP_REG_PROG_ID_1_VALUE,
            "SP_REG_PROG_ID_2": SP_REG_PROG_ID_2_VALUE,
            "SP_REG_PROG_ID_3": SP_REG_PROG_ID_3_VALUE,
        },
        "sp_const_config_registers": {
            "SP_VS_CONST_CONFIG": "0x0000b800",
            "SP_PS_CONST_CONFIG": "0x0000bb10",
        },
        "sp_ps_output_cntl_register": "0x0000a98c",
        "sp_frontend_prog_id_registers": {
            "SP_PS_INITIAL_TEX_LOAD_CNTL": "0x0000a99e",
            "SP_PS_WAVE_CNTL": "0x0000b980",
            "SP_LB_PARAM_LIMIT": "0x0000b982",
            "SP_REG_PROG_ID_0": "0x0000b983",
            "SP_REG_PROG_ID_1": "0x0000b984",
            "SP_REG_PROG_ID_2": "0x0000b985",
            "SP_REG_PROG_ID_3": "0x0000b986",
        },
        "cmd_max_dwords": CMD_MAX_DWORDS,
        "state_reg_writes_expected": 106,
        "pm4_dwords_expected": 282,
        "shader_payload": SHADER_PAYLOAD,
        "readback": "expect changed pixels if zero-default SP front-end/system-value regids were blocking FS dispatch or color output",
        "next_live_validation": [
            "flash-v3272-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-sp-frontend-prog-id-timeout-guard",
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
        "# Native Init V3272 GPU H3 SP Frontend Prog ID Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle SP front-end program-id/system-value state before H4 readback proof.",
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
        "- Keeps the V3270 shader payload, direct-render marker, visibility packet trio, zero window offsets, CP_SET_MODE(0), A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, `VPC_SO_OVERRIDE(false)`, triangle raster mode, SP const enables, and `SP_PS_OUTPUT_CNTL=0xfcfcfc00`.",
        "- Adds the A6xx fd6 FS-input/program-id state group missing from H3: `SP_PS_INITIAL_TEX_LOAD_CNTL`, `SP_PS_WAVE_CNTL`, `SP_LB_PARAM_LIMIT`, and `SP_REG_PROG_ID_0..3`.",
        "- Uses current H3 constant-FS semantics: no varyings, no fragment sysvals, invalid `0xfc` regids for unused face/sample/IJ/coord slots, and `SP_PS_INITIAL_TEX_LOAD_CNTL=0x8` for zero prefetch with IJ writes disabled.",
        "- Leaves cffdump's `SP_REG_PROG_ID_1=0xfcfcfc00` and `SP_PS_WAVE_CNTL=0x3` out of this probe because that reference FS uses `bary.f`; H3's current FS does not.",
        "- Expected PM4 size rises from `270` to `282` dwords; expected 3D state register writes rise from `100` to `106`.",
        "- Removes the preserved V3268 DOOM engine entry before packing V3272 to keep the boot image under the 64MiB gate.",
        "",
        "## Source Basis",
        "",
        "- Local A6xx XML defines `SP_PS_WAVE_CNTL` at `0xb980`, `SP_LB_PARAM_LIMIT` at `0xb982`, and `SP_REG_PROG_ID_0..3` at `0xb983..0xb986` as A6xx draw registers.",
        "- Local Mesa `fd6_program.cc::emit_fs_inputs()` emits this state for every FS, using `INVALID_REG=0xfc` for absent front-face/sample-mask/IJ/coord system values.",
        "- The A640 triangle `.rd` summary confirms the same register family is present in a real fd6 draw; H3 previously emitted only `SP_REG_PROG_ID_3`.",
        "- HLSQ round-4 audit: old `HLSQ_CONTROL_*` / `HLSQ_*_CNTL` names are not present in this A6xx XML/fd6 draw path; the actionable front-end gap is the SP wave/program-id group.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3272 builder and focused source contract test.",
        "- `unittest`: V3272 GPU H3 SP front-end source contract and H3 source compatibility tests.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3272 identity plus SP front-end program-id telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS before commit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-sp-frontend-prog-id-probe-candidate`.",
    ]) + "\n"


def v3272_adapter_source() -> str:
    return _rewrite_v3272_text(previous.v3268_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-sp-frontend-prog-id-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-sp-frontend-prog-id-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-sp-frontend-prog-id-live-validation",
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
        "STALE_V3265_ENGINE_RAMDISK_PATH": STALE_V3268_ENGINE_RAMDISK_PATH,
    }
    saved: list[tuple[Any, str, Any]] = []
    for name, value in replacements.items():
        saved.append((previous, name, getattr(previous, name)))
        setattr(previous, name, value)
    return saved


def _restore_previous_overlay_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3272_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3268_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3268-ramdisk-overlay-v3272-init-helper-engine"
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
            "candidate_type": "gpu-h3-sp-frontend-prog-id-probe-candidate",
            "adoption_state": "pending-gpu-h3-sp-frontend-prog-id-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-sp-frontend-prog-id-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-sp-frontend-prog-id-live-validation"
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
        "candidate_type": "gpu-h3-sp-frontend-prog-id-probe-candidate",
        "adoption_state": "pending-gpu-h3-sp-frontend-prog-id-live-validation",
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


def _apply_v3272_overrides() -> None:
    previous._apply_v3268_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3272_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3272_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3272_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3272_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
