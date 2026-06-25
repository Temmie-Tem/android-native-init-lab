#!/usr/bin/env python3
"""Build V3284 GPU H3 A640 non-zero init-magic block probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3282_gpu_h3_rb_dbg_eco_probe as previous

base = previous.base

CYCLE = "V3284"
INIT_VERSION = "0.11.68"
INIT_BUILD = "v3284-gpu-h3-a640-magic-block-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3284-gpu-h3-a640-magic-block-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3284_GPU_H3_A640_MAGIC_BLOCK_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3284_gpu_h3_a640_magic_block_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3284_gpu_h3_a640_magic_block_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3284_gpu_h3_a640_magic_block_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v600_gpu_h3_a640_magic_block_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3284"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3284.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3284.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3284"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3284-gpu-h3-a640-magic-block-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3284-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3284-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3284-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3284-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3284-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3284-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3284-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-a640-magic-block-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-a640-magic-block-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3282", "v3284")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3282", "v3284")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3282", "v3284")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3282", "v3284")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3282", "v3284")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3282", "v3284")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3282", "v3284")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3282", "v3284")
SFX_STREAM_MARKER = "a90.doomgeneric.v3284.audio=real-sfx-pcm-stream-gpu-h3-a640-magic-block-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-a640-magic-block-probe-v3284"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3284.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = (
    "first-triangle-h3-a640-nonzero-init-magic-block-flag-mrt-cffdump-color-target-"
    "varying-ij-vpc-linkage-clip-guardband-su-rasterizer-a6xx-output-routing-"
    "sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-"
    "window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-"
    "sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
)
PREVIOUS_SCOPE = previous.SCOPE
A640_MAGIC_SOURCE = "Mesa freedreno_devices.py A640/a6xx_gen2 non-zero magic_regs block"
A640_NONZERO_MAGIC_REGS = {
    "RB_DBG_ECO_CNTL": ("0x00008e04", "0x04100000"),
    "SP_CHICKEN_BITS": ("0x0000ae03", "0x00000420"),
    "TPL1_DBG_ECO_CNTL": ("0x0000b600", "0x00008000"),
    "VPC_DBG_ECO_CNTL": ("0x00009600", "0x02000000"),
    "RB_RBP_CNTL": ("0x00008e01", "0x00000001"),
    "PC_MODE_CNTL": ("0x00009804", "0x0000001f"),
    "PC_POWER_CNTL": ("0x00009805", "0x00000001"),
    "VFD_POWER_CNTL": ("0x0000a0f8", "0x00000001"),
    "UCHE_UNKNOWN_0E12": ("0x00000e12", "0x00000001"),
}
INIT_MAGIC_REG_WRITES_EXPECTED = 9
CMD_MAX_DWORDS = 384
PM4_DWORDS_EXPECTED = 329


def _rewrite_v3284_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3282": b"a90-doomgeneric-v3284",
        b"a90.doomgeneric.v3282": b"a90.doomgeneric.v3284",
        b"v3282": b"v3284",
        b"V3282": b"V3284",
        b"gpu-h3-rb-dbg-eco-probe": b"gpu-h3-a640-magic-block-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
        b"gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit":
            b"gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
        b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-rb-dbg-eco-cntl":
            b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-nonzero-magic-regs",
        b"gpu.h3.draw.a640_magic_mode=rb-dbg-eco-only":
            b"gpu.h3.draw.a640_magic_mode=nonzero-block",
        b"gpu.h3.draw.a640_magic_deferred_nonzero_block=sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_power,vfd_power,uche_unknown_0e12":
            b"gpu.h3.draw.a640_magic_nonzero_block=rb_dbg_eco,sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_mode,pc_power,vfd_power,uche_unknown_0e12",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3284_text(text: str) -> str:
    return _rewrite_v3284_bytes(text.encode("utf-8")).decode("utf-8")


GPU_H3_A640_MAGIC_BLOCK_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-nonzero-magic-regs",
    b"gpu.h3.draw.a640_magic_mode=nonzero-block",
    b"gpu.h3.draw.a640_magic_nonzero_block=rb_dbg_eco,sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_mode,pc_power,vfd_power,uche_unknown_0e12",
    b"gpu.h3.draw.sp_chicken_bits=0x%x",
    b"gpu.h3.draw.tpl1_dbg_eco_cntl=0x%x",
    b"gpu.h3.draw.vpc_dbg_eco_cntl=0x%x",
    b"gpu.h3.draw.rb_rbp_cntl=0x%x",
    b"gpu.h3.draw.pc_mode_cntl_magic=0x%x",
    b"gpu.h3.draw.pc_power_cntl=0x%x",
    b"gpu.h3.draw.vfd_power_cntl=0x%x",
    b"gpu.h3.draw.uche_unknown_0e12=0x%x",
    b"gpu.h3.draw.a640_init_magic_reg_writes=%u",
)

REQUIRED_STRINGS = tuple(_rewrite_v3284_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_A640_MAGIC_BLOCK_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3282-v3283-rb-dbg-eco-only-live-no-pixel-plus-a640-device-db-nonzero-magic-block",
        "scope": SCOPE,
        "a640_magic_source": A640_MAGIC_SOURCE,
        "a640_magic_mode": "nonzero-block",
        "a640_nonzero_magic_regs": A640_NONZERO_MAGIC_REGS,
        "cmd_max_dwords": CMD_MAX_DWORDS,
        "state_reg_writes_expected": 121,
        "init_magic_reg_writes_expected": INIT_MAGIC_REG_WRITES_EXPECTED,
        "vfd_reg_writes_expected": 14,
        "pm4_dwords_expected": PM4_DWORDS_EXPECTED,
        "readback": "expect changed color or flag buffer words if missing A640 non-zero init magic blocked RB/SP/VPC/PC/VFD writes",
        "next_live_validation": [
            "flash-v3284-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-a640-magic-block-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    })
    for stale_key in ("deferred_magic_regs", "rb_dbg_eco_source", "rb_dbg_eco_reg_value", "rb_dbg_eco_cntl_value"):
        manifest.pop(stale_key, None)
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3284 GPU H3 A640 Magic Block Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle A640 device-DB non-zero init-magic block probe before H4 readback proof.",
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
        "- Keeps the V3280 direct-render/sysmem/varying-IJ/RGBA8/flag-MRT baseline intact.",
        "- Keeps the V3282 `RB_DBG_ECO_CNTL=0x04100000` write and adds the rest of the non-zero A640/a6xx_gen2 device-DB magic block.",
        "- Places the block in the H3 context first-restore/init portion before shader and 3D draw state.",
        "- Raises the shared GPU command-buffer dword guard from `320` to `384` because this block raises expected H3 PM4 size to `329` dwords.",
        "- Expected 3D state register writes remain `121`; init-magic register writes are `9`; VFD draw-local writes remain `14`.",
        "",
        "## Source Basis",
        "",
        "- Operator-staged `/tmp/a90-mesa-gpu-src/a640_magic_regs.txt` records the A640/a6xx_gen2 non-zero magic register block from Mesa `freedreno_devices.py`.",
        "- This unit does not change `RB_CCU_CNTL`; that value stays the existing computed A640 sysmem CCU value.",
        "- `PC_POWER_CNTL` and `VFD_POWER_CNTL` here are GPU command-stream registers from the Mesa device DB block; this unit does not touch PMIC, GDSC, regulator, GPIO, sysfs power, or forbidden partitions.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3284 builder, shader audit, and focused source contract tests.",
        "- `unittest`: V3284 GPU H3 A640 magic-block source contract and H3 shader-byte audit.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3284 identity plus A640 magic-block telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-a640-magic-block-probe-candidate`.",
    ]) + "\n"


def v3284_adapter_source() -> str:
    return _rewrite_v3284_text(previous.v3282_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-a640-magic-block-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-a640-magic-block-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-a640-magic-block-live-validation",
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


def _overlay_preserved_v3284_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3282_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3282-ramdisk-overlay-v3284-init-helper-engine"
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
            "candidate_type": "gpu-h3-a640-magic-block-probe-candidate",
            "adoption_state": "pending-gpu-h3-a640-magic-block-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-a640-magic-block-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-a640-magic-block-live-validation"
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
        "candidate_type": "gpu-h3-a640-magic-block-probe-candidate",
        "adoption_state": "pending-gpu-h3-a640-magic-block-live-validation",
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


def _apply_v3284_overrides() -> None:
    previous._apply_v3282_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3284_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3284_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3284_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3284_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
