#!/usr/bin/env python3
"""Build V3282 GPU H3 A640 RB_DBG_ECO init-magic probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3280_gpu_h3_flag_mrt_probe as previous

base = previous.base

CYCLE = "V3282"
INIT_VERSION = "0.11.67"
INIT_BUILD = "v3282-gpu-h3-rb-dbg-eco-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3282-gpu-h3-rb-dbg-eco-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3282_GPU_H3_RB_DBG_ECO_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3282_gpu_h3_rb_dbg_eco_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3282_gpu_h3_rb_dbg_eco_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3282_gpu_h3_rb_dbg_eco_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v600_gpu_h3_rb_dbg_eco_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3282"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3282.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3282.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3282"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3282-gpu-h3-rb-dbg-eco-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3282-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3282-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3282-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3282-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3282-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3282-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3282-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-rb-dbg-eco-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-rb-dbg-eco-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3280", "v3282")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3280", "v3282")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3280", "v3282")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3280", "v3282")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3280", "v3282")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3280", "v3282")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3280", "v3282")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3280", "v3282")
SFX_STREAM_MARKER = "a90.doomgeneric.v3282.audio=real-sfx-pcm-stream-gpu-h3-rb-dbg-eco-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-rb-dbg-eco-probe-v3282"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3282.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = (
    "first-triangle-h3-rb-dbg-eco-init-magic-flag-mrt-cffdump-color-target-"
    "varying-ij-vpc-linkage-clip-guardband-su-rasterizer-a6xx-output-routing-"
    "sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-"
    "window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-"
    "sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
)
PREVIOUS_SCOPE = previous.SCOPE
RB_DBG_ECO_SOURCE = "Mesa freedreno_devices.py A640/a6xx_gen2 magic_regs RB_DBG_ECO_CNTL"
RB_DBG_ECO_REG_VALUE = "0x00008e04"
RB_DBG_ECO_CNTL_VALUE = "0x04100000"
INIT_MAGIC_REG_WRITES_EXPECTED = 1
CMD_MAX_DWORDS = 320


def _rewrite_v3282_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3280": b"a90-doomgeneric-v3282",
        b"a90.doomgeneric.v3280": b"a90.doomgeneric.v3282",
        b"v3280": b"v3282",
        b"V3280": b"V3282",
        b"gpu-h3-flag-mrt-probe": b"gpu-h3-rb-dbg-eco-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
        b"gpu-h3-flag-mrt-shader-byte-audit":
            b"gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3282_text(text: str) -> str:
    for old, new in (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3280", "a90-doomgeneric-v3282"),
        ("a90.doomgeneric.v3280", "a90.doomgeneric.v3282"),
        ("v3280", "v3282"),
        ("V3280", "V3282"),
        ("gpu-h3-flag-mrt-probe", "gpu-h3-rb-dbg-eco-probe"),
        (PREVIOUS_SCOPE, SCOPE),
        ("gpu-h3-flag-mrt-shader-byte-audit", "gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit"),
    ):
        text = text.replace(old, new)
    return text


GPU_H3_RB_DBG_ECO_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-rb-dbg-eco-cntl",
    b"gpu.h3.draw.a640_magic_mode=rb-dbg-eco-only",
    b"gpu.h3.draw.rb_dbg_eco_cntl=0x%x",
    b"gpu.h3.draw.rb_dbg_eco_cntl_reg=0x%x",
    b"gpu.h3.draw.a640_init_magic_reg_writes=%u",
    b"gpu.h3.draw.a640_magic_deferred_nonzero_block=sp_chicken_bits,tpl1_dbg_eco,vpc_dbg_eco,rb_rbp,pc_power,vfd_power,uche_unknown_0e12",
)

REQUIRED_STRINGS = tuple(_rewrite_v3282_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_RB_DBG_ECO_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3280-v3281-flag-mrt-live-no-pixel-plus-a640-device-db-rb-dbg-eco-magic",
        "scope": SCOPE,
        "rb_dbg_eco_source": RB_DBG_ECO_SOURCE,
        "rb_dbg_eco_reg_value": RB_DBG_ECO_REG_VALUE,
        "rb_dbg_eco_cntl_value": RB_DBG_ECO_CNTL_VALUE,
        "a640_magic_mode": "rb-dbg-eco-only",
        "deferred_magic_regs": [
            "SP_CHICKEN_BITS",
            "TPL1_DBG_ECO_CNTL",
            "VPC_DBG_ECO_CNTL",
            "RB_RBP_CNTL",
            "PC_POWER_CNTL",
            "VFD_POWER_CNTL",
            "UCHE_UNKNOWN_0E12",
        ],
        "state_reg_writes_expected": 121,
        "init_magic_reg_writes_expected": INIT_MAGIC_REG_WRITES_EXPECTED,
        "vfd_reg_writes_expected": 14,
        "pm4_dwords_expected": 313,
        "readback": "expect changed color or flag buffer words if missing A640 RB_DBG_ECO init magic blocked RB writes",
        "next_live_validation": [
            "flash-v3282-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-rb-dbg-eco-timeout-guard",
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
        "# Native Init V3282 GPU H3 RB_DBG_ECO Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle A640 device-DB RB_DBG_ECO init-magic probe before H4 readback proof.",
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
        "- Adds only `RB_DBG_ECO_CNTL=0x04100000` at register `0x8e04` from the A640/a6xx_gen2 freedreno device DB magic block.",
        "- Places the write in the H3 context first-restore/init portion before shader and 3D draw state.",
        "- Defers the rest of the non-zero A640 magic block to the next bounded probe.",
        "- Expected PM4 size is `313` dwords; 3D state register writes remain `121`; init-magic register writes are `1`; VFD draw-local writes remain `14`.",
        "",
        "## Source Basis",
        "",
        "- Operator-staged `/tmp/a90-mesa-gpu-src/a640_magic_regs.txt` records A640 `RB_DBG_ECO_CNTL off=0x8e04 val=0x04100000` from Mesa `freedreno_devices.py`.",
        "- This unit does not change `RB_CCU_CNTL`; that value stays the existing computed A640 sysmem CCU value.",
        "- This unit does not emit SP/TPL1/VPC/RBP/PC/VFD/UCHE magic values; probe order is RB_DBG_ECO first.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3282 builder, shader audit, and focused source contract tests.",
        "- `unittest`: V3282 GPU H3 RB_DBG_ECO source contract and H3 shader-byte audit.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3282 identity plus RB_DBG_ECO telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-rb-dbg-eco-probe-candidate`.",
    ]) + "\n"


def v3282_adapter_source() -> str:
    return _rewrite_v3282_text(previous.v3280_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-rb-dbg-eco-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-rb-dbg-eco-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-rb-dbg-eco-live-validation",
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


def _overlay_preserved_v3282_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3280_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3280-ramdisk-overlay-v3282-init-helper-engine"
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
            "candidate_type": "gpu-h3-rb-dbg-eco-probe-candidate",
            "adoption_state": "pending-gpu-h3-rb-dbg-eco-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-rb-dbg-eco-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-rb-dbg-eco-live-validation"
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
        "candidate_type": "gpu-h3-rb-dbg-eco-probe-candidate",
        "adoption_state": "pending-gpu-h3-rb-dbg-eco-live-validation",
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


def _apply_v3282_overrides() -> None:
    previous._apply_v3280_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3282_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3282_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3282_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3282_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
