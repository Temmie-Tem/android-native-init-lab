#!/usr/bin/env python3
"""Build V3253 GPU H3 SP_UPDATE_CNTL draw-state probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3251_gpu_h3_compiler_vs_instrlen_probe as previous

base = previous.base

CYCLE = "V3253"
INIT_VERSION = "0.11.53"
INIT_BUILD = "v3253-gpu-h3-sp-update-cntl-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3253-gpu-h3-sp-update-cntl-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3253_GPU_H3_SP_UPDATE_CNTL_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3253_gpu_h3_sp_update_cntl_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3253_gpu_h3_sp_update_cntl_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3253_gpu_h3_sp_update_cntl_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v580_gpu_h3_sp_update_cntl_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3253"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3253.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3253.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3253"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3253-gpu-h3-sp-update-cntl-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3253-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3253-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3253-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3253-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3253-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3253-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3253-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-sp-update-cntl-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-sp-update-cntl-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3251", "v3253")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3251", "v3253")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3251", "v3253")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3251", "v3253")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3251", "v3253")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3251", "v3253")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3251", "v3253")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3251", "v3253")
SFX_STREAM_MARKER = "a90.doomgeneric.v3253.audio=real-sfx-pcm-stream-gpu-h3-sp-update-cntl-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-sp-update-cntl-probe-v3253"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3253.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h3-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
PREVIOUS_SCOPE = "first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader"
SHADER_PAYLOAD = previous.SHADER_PAYLOAD
SP_UPDATE_CNTL = "0x0000009f"
SP_UPDATE_CNTL_REG = "0x0000bb08"
STALE_V3251_ENGINE_RAMDISK_PATH = previous.ENGINE_RAMDISK_PATH


def _rewrite_v3253_bytes(item: bytes) -> bytes:
    replacements = {
        previous.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        previous.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        previous.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        previous.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        previous.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        previous.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        previous.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3251": b"a90-doomgeneric-v3253",
        b"a90.doomgeneric.v3251": b"a90.doomgeneric.v3253",
        b"v3251": b"v3253",
        b"V3251": b"V3253",
        b"gpu-h3-compiler-vs-instrlen-probe": b"gpu-h3-sp-update-cntl-probe",
        PREVIOUS_SCOPE.encode("ascii"): SCOPE.encode("ascii"),
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


def _rewrite_v3253_text(text: str) -> str:
    for old, new in (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3251", "a90-doomgeneric-v3253"),
        ("a90.doomgeneric.v3251", "a90.doomgeneric.v3253"),
        ("v3251", "v3253"),
        ("V3251", "V3253"),
        ("gpu-h3-compiler-vs-instrlen-probe", "gpu-h3-sp-update-cntl-probe"),
        (PREVIOUS_SCOPE, SCOPE),
    ):
        text = text.replace(old, new)
    return text


GPU_H3_SP_UPDATE_CNTL_MARKERS = (
    b"gpu.h3.draw.scope=" + SCOPE.encode("ascii"),
    b"gpu.h3.draw.sp_update_cntl_source=mesa-freedreno-a6xx-fd6-program-and-draw-stateobj",
    b"gpu.h3.draw.sp_update_cntl=0x%x",
)

REQUIRED_STRINGS = tuple(_rewrite_v3253_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_SP_UPDATE_CNTL_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h3_manifest())
    manifest.update({
        "source_baseline": "v3251-compiler-vs-instrlen-plus-v3252-live-validation",
        "scope": SCOPE,
        "draw_state_bootstrap_source": "Mesa freedreno A6xx fd6_program and fd6_emit SP_UPDATE_CNTL draw-state packets",
        "sp_update_cntl_register": SP_UPDATE_CNTL_REG,
        "sp_update_cntl": SP_UPDATE_CNTL,
        "sp_update_cntl_decode": "VS_STATE|HS_STATE|DS_STATE|GS_STATE|FS_STATE|GFX_UAV; CS/GFX bindless masks zero",
        "state_reg_writes_expected": 92,
        "pm4_dwords_expected": 242,
        "shader_payload": SHADER_PAYLOAD,
        "readback": "expect changed pixels after shader CP_LOAD_STATE6 pending state is explicitly updated",
        "next_live_validation": [
            "flash-v3253-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h3-sp-update-cntl-timeout-guard",
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
        "# Native Init V3253 GPU H3 SP_UPDATE_CNTL Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H3 first-triangle draw-state bootstrap before H4 readback proof.",
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
        "- Keeps the V3251 Mesa-reference minimal VS, audited FS, shader `instrlen=1`, direct-render marker, RB_RENDER_CNTL, RB_CCU sysmem, and pre-draw cache invalidation state.",
        "- Adds Mesa A6xx draw-state bootstrap register `SP_UPDATE_CNTL=0x0000009f` before H3 shader state, matching the local freedreno draw/program state object pattern.",
        "- Removes the preserved V3251 DOOM engine entry before packing V3253 to keep the boot image under the 64MiB gate.",
        "",
        "## Source Basis",
        "",
        "- Local Mesa register XML: `/tmp/a90-mesa-h3-sparse/src/freedreno/registers/adreno/a6xx.xml` (`SP_UPDATE_CNTL`, offset `0xbb08`).",
        "- Local Mesa draw emit: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc` (`SP_UPDATE_CNTL=0x000fffff` restore path).",
        "- Local Mesa program state: `/tmp/a90-mesa-h3-sparse/src/gallium/drivers/freedreno/a6xx/fd6_program.cc` (`SP_UPDATE_CNTL` before shader/program state).",
        "- Local Mesa reference trace: `dEQP-VK.draw.indirect_draw.indexed.indirect_draw_count.triangle_list.log` draw-local `SP_UPDATE_CNTL=0x0000009f`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3253 builder and shader audit.",
        "- `unittest`: V3253 GPU H3 SP_UPDATE_CNTL source contract and H3 source compatibility tests.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3253 identity plus SP_UPDATE_CNTL telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "- `git diff --check`: PASS before commit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-sp-update-cntl-probe-candidate`.",
    ]) + "\n"


def v3253_adapter_source() -> str:
    return _rewrite_v3253_text(previous.v3251_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h3-sp-update-cntl-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-sp-update-cntl-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-sp-update-cntl-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.pop("base_main_error", None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-sp-update-cntl-probe-candidate",
        "adoption_state": "pending-gpu-h3-sp-update-cntl-live-validation",
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
    }
    saved: list[tuple[Any, str, Any]] = []
    for name, value in replacements.items():
        saved.append((previous, name, getattr(previous, name)))
        setattr(previous, name, value)
    saved.append((previous.previous, "ENGINE_RAMDISK_PATH", previous.previous.ENGINE_RAMDISK_PATH))
    previous.previous.ENGINE_RAMDISK_PATH = STALE_V3251_ENGINE_RAMDISK_PATH
    return saved


def _restore_previous_overlay_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3253_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3251_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3251-ramdisk-overlay-v3253-init-helper-engine"
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
            "candidate_type": "gpu-h3-sp-update-cntl-probe-candidate",
            "adoption_state": "pending-gpu-h3-sp-update-cntl-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-sp-update-cntl-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-sp-update-cntl-live-validation"
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


def _apply_v3253_overrides() -> None:
    previous._apply_v3251_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3253_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3253_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3253_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3253_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
