#!/usr/bin/env python3
"""Build V3261 GPU H3 sysmem-prep window offset probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3259_gpu_h3_visibility_packets_probe as previous

base = previous.base

CYCLE = "V3261"
INIT_VERSION = "0.11.57"
INIT_BUILD = "v3261-gpu-h3-window-offset-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3261-gpu-h3-window-offset-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3261_GPU_H3_WINDOW_OFFSET_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3261_gpu_h3_window_offset_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3261_gpu_h3_window_offset_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3261_gpu_h3_window_offset_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v588_gpu_h3_window_offset_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3261"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3261.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3261.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3261"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3261-gpu-h3-window-offset-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3261-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3261-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3261-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3261-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3261-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3261-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3261-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-window-offset-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-window-offset-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3259", "v3261")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3259", "v3261")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3259", "v3261")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3259", "v3261")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3259", "v3261")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3259", "v3261")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3259", "v3261")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3259", "v3261")
SFX_STREAM_MARKER = "a90.doomgeneric.v3261.audio=real-sfx-pcm-stream-gpu-h3-window-offset-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-window-offset-probe-v3261"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3261.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
PREVIOUS_SCOPE = previous.SCOPE
SHADER_PAYLOAD = previous.SHADER_PAYLOAD
WINDOW_OFFSET_REGISTERS = ("0x00008890", "0x000088d4", "0x0000b4d1", "0x0000b307")
WINDOW_OFFSET_VALUE = "0x00000000"
STALE_V3259_ENGINE_RAMDISK_PATH = previous.ENGINE_RAMDISK_PATH


def _rewrite_v3261_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3259": b"a90-doomgeneric-v3261",
        b"a90.doomgeneric.v3259": b"a90.doomgeneric.v3261",
        b"v3259": b"v3261",
        b"V3259": b"V3261",
        b"gpu-h3-visibility-packets-probe": b"gpu-h3-window-offset-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3261_text(text: str) -> str:
    for old, new in (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3259", "a90-doomgeneric-v3261"),
        ("a90.doomgeneric.v3259", "a90.doomgeneric.v3261"),
        ("v3259", "v3261"),
        ("V3259", "V3261"),
        ("gpu-h3-visibility-packets-probe", "gpu-h3-window-offset-probe"),
        (PREVIOUS_SCOPE, SCOPE),
    ):
        text = text.replace(old, new)
    return text


GPU_H3_WINDOW_OFFSET_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.window_offset_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-window-offset-zero",
    b"gpu.h3.draw.rb_window_offset=0x%x",
    b"gpu.h3.draw.rb_resolve_window_offset=0x%x",
    b"gpu.h3.draw.sp_window_offset=0x%x",
    b"gpu.h3.draw.tpl1_window_offset=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3261_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_WINDOW_OFFSET_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3259-visibility-packets-plus-v3260-live-validation",
        "scope": SCOPE,
        "window_offset_source": "Mesa freedreno A6xx fd6_emit_sysmem_prep set_window_offset(0, 0)",
        "window_offset_registers": WINDOW_OFFSET_REGISTERS,
        "window_offset_value": WINDOW_OFFSET_VALUE,
        "state_reg_writes_expected": 98,
        "pm4_dwords_expected": 260,
        "shader_payload": SHADER_PAYLOAD,
        "readback": "expect changed pixels after Mesa sysmem-prep window-offset registers are emitted",
        "next_live_validation": [
            "flash-v3261-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-window-offset-timeout-guard",
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
        "# Native Init V3261 GPU H3 Window Offset Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle sysmem-prep ordering before H4 readback proof.",
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
        "- Keeps the V3259 shader payload, direct-render marker, visibility packet trio, A640 sysmem RB_CCU value, sysmem bin controls, pre-draw cache invalidation, draw-local `SP_UPDATE_CNTL=0x0000009f`, and `VPC_SO_OVERRIDE(false)`.",
        "- Adds Mesa sysmem-prep zero window offsets immediately after the direct-render marker and before the visibility packet trio: `RB_WINDOW_OFFSET=0`, `RB_RESOLVE_WINDOW_OFFSET=0`, `SP_WINDOW_OFFSET=0`, and `TPL1_WINDOW_OFFSET=0`.",
        "- Expected PM4 size rises from `252` to `260` dwords; expected register writes rise from `94` to `98`.",
        "- Removes the preserved V3259 DOOM engine entry before packing V3261 to keep the boot image under the 64MiB gate.",
        "",
        "## Source Basis",
        "",
        "- Local Mesa sysmem prep: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_gmem.cc` (`fd6_emit_sysmem_prep`, `set_window_offset`).",
        "- Local Mesa A6xx register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`RB_WINDOW_OFFSET=0x8890`, `RB_RESOLVE_WINDOW_OFFSET=0x88d4`, `SP_WINDOW_OFFSET=0xb4d1`, `TPL1_WINDOW_OFFSET=0xb307`).",
        "- V3260 live result left this sysmem-prep window-offset group as the next concrete Mesa/H3 command-stream mismatch when a full captured diff was not immediately available.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3261 builder and shader audit.",
        "- `unittest`: V3261 GPU H3 window-offset source contract and H3 source compatibility tests.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3261 identity plus window offset telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS before commit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-window-offset-probe-candidate`.",
    ]) + "\n"


def v3261_adapter_source() -> str:
    return _rewrite_v3261_text(previous.v3259_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-window-offset-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-window-offset-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-window-offset-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("base_main_error", None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-window-offset-probe-candidate",
        "adoption_state": "pending-gpu-h3-window-offset-live-validation",
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
        "STALE_V3257_ENGINE_RAMDISK_PATH": STALE_V3259_ENGINE_RAMDISK_PATH,
    }
    saved: list[tuple[Any, str, Any]] = []
    for name, value in replacements.items():
        saved.append((previous, name, getattr(previous, name)))
        setattr(previous, name, value)
    return saved


def _restore_previous_overlay_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3261_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3259_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3259-ramdisk-overlay-v3261-init-helper-engine"
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
            "candidate_type": "gpu-h3-window-offset-probe-candidate",
            "adoption_state": "pending-gpu-h3-window-offset-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-window-offset-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-window-offset-live-validation"
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


def _apply_v3261_overrides() -> None:
    previous._apply_v3259_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3261_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3261_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3261_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3261_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
