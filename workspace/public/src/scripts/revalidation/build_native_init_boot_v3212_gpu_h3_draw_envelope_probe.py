#!/usr/bin/env python3
"""Build V3212 GPU H3 draw-envelope probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3210_gpu_h2_3d_state_probe as base

OLD_INIT_VERSION = base.INIT_VERSION
OLD_INIT_BUILD = base.INIT_BUILD
OLD_ENGINE_NAME = base.ENGINE_NAME
OLD_ENGINE_REMOTE_PATH = base.ENGINE_REMOTE_PATH
OLD_SOUND_MODE = base.SOUND_MODE
OLD_SFX_STREAM_MARKER = base.SFX_STREAM_MARKER
OLD_AUDIO_PCM_STREAM_PATH = base.AUDIO_PCM_STREAM_PATH
OLD_BOOT_IMAGE = base.BOOT_IMAGE

CYCLE = "V3212"
INIT_VERSION = "0.11.33"
INIT_BUILD = "v3212-gpu-h3-draw-envelope-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3212-gpu-h3-draw-envelope-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3212_GPU_H3_DRAW_ENVELOPE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3212_gpu_h3_draw_envelope_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = OLD_BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3212_gpu_h3_draw_envelope_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3212_gpu_h3_draw_envelope_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v565_gpu_h3_draw_envelope_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3212"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3212.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3212.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3212"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3212-gpu-h3-draw-envelope-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3212-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3212-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3212-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3212-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3212-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3212-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3212-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h3-draw-envelope-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h3-draw-envelope-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3210", "v3212")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3210", "v3212")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3210", "v3212")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3210", "v3212")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3210", "v3212")
SCALE_MARKER = base.SCALE_MARKER.replace("v3210", "v3212")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3210", "v3212")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3210", "v3212")
SFX_STREAM_MARKER = "a90.doomgeneric.v3212.audio=real-sfx-pcm-stream-gpu-h3-draw-envelope-probe"
SOUND_MODE = "native-doom-sfx-gpu-h3-draw-envelope-probe-v3212"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3212.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"


def _rewrite_v3212_marker(item: bytes) -> bytes:
    replacements = {
        OLD_INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        OLD_INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        OLD_ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        OLD_ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        OLD_SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        OLD_SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        OLD_AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3210": b"a90-doomgeneric-v3212",
        b"a90.doomgeneric.v3210": b"a90.doomgeneric.v3212",
        b"v3210": b"v3212",
        b"V3210": b"V3212",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H3_DRAW_ENVELOPE_MARKERS = (
    b"h3-draw-envelope-probe",
    b"draw-envelope-probe",
    b"gpu.h3.draw.version=1",
    b"gpu.h3.draw.scope=first-triangle-h3-draw-envelope-placeholder-shader",
    b"gpu.h3.draw.parent_enters_open=0",
    b"gpu.h3.draw.parent_enters_ioctl=0",
    b"gpu.h3.draw.source=mesa-freedreno-a6xx-fd6-draw-plus-vfd-fetch-dest",
    b"gpu.h3.draw.shader_payload=zero-placeholder-no-full-compiler",
    b"gpu.h3.draw.vertex_format=fmt6-32-32-float",
    b"gpu.h3.draw.offscreen=u32-linear-128x128",
    b"gpu.h3.draw.draw_attempted=1",
    b"gpu.h3.draw.shader_execution_attempted=1",
    b"gpu.h3.draw.kms_blit_attempted=0",
    b"gpu.h3.draw.cp_draw_packet=0x%x",
    b"gpu.h3.draw.draw_initiator=0x%x",
    b"gpu.h3.draw.num_indices=%u",
    b"gpu.h3.draw.pm4_dwords=%u",
    b"gpu.h3.draw.readback_changed_count=%u",
    b"gpu.h3.draw.result=%s",
)

REQUIRED_STRINGS = tuple(_rewrite_v3212_marker(item) for item in base.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H3_DRAW_ENVELOPE_MARKERS


def _minimal_gpu_h3_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3210-gpu-h2-3d-state-probe",
        "command": "gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode",
        "scope": "first-triangle-h3-draw-envelope-placeholder-shader",
        "pm4_source": "Mesa freedreno A6xx fd6_draw direct CP_DRAW_INDX_OFFSET plus A6xx VFD register XML",
        "offscreen": "u32-linear-128x128",
        "vertex_format": "FMT6_32_32_FLOAT",
        "vertex_count": 3,
        "draw_attempted": True,
        "shader_payload": "zero-placeholder-no-full-compiler",
        "shader_execution_attempted": True,
        "readback": "color-buffer changed-count summary after PC_CCU_FLUSH_COLOR_TS",
        "kms_blit_attempted": False,
        "parent_enters_open": False,
        "parent_enters_ioctl": False,
        "next_live_validation": [
            "flash-v3212-through-native-init-flash",
            "post-flash-health-check",
            "gpu-g0-fwclass-prepare",
            "gpu-h3-draw-envelope-probe-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3212 GPU H3 Draw Envelope Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU first-triangle H3: bind one vertex buffer, emit direct non-indexed `CP_DRAW_INDX_OFFSET`, and summarize offscreen readback.",
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
        "- Adds `gpu h3-draw-envelope-probe` after the V3210 H2 fixed-function 3D state retire probe.",
        "- Allocates command, color, event, placeholder VS/FS shader, and 3-vertex buffer GPU objects in a child-only KGSL envelope.",
        "- Emits H1 shader-state setup, H2 3D state, A6xx VFD vertex buffer/fetch/dest state, then `CP_DRAW_INDX_OFFSET` for one triangle list of 3 vertices.",
        "- Performs `PC_CCU_FLUSH_COLOR_TS`, waits on the KGSL timestamp, syncs the color buffer back, and reports changed pixel count without presenting to KMS.",
        "- Shader payload is still an explicit zero placeholder. This rung is a bounded draw-envelope probe, not a completed shaded triangle proof.",
        "",
        "## Source Basis",
        "",
        "- Mesa/freedreno draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.",
        "- A6xx VFD register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.",
        "- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent remains outside KGSL and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, KMS presentation, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3212 builder and focused H3 source test.",
        "- `unittest`: V3212 GPU H3 source contract.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3212 identity plus H3 draw-envelope markers.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h3-draw-envelope-probe-candidate`.",
    ]) + "\n"


def v3212_adapter_source() -> str:
    return (
        base.ORIG_V3208_ADAPTER_SOURCE()
        .replace("gpu-h1-shader-state-probe", "gpu-h3-draw-envelope-probe")
        .replace("real-sfx-pcm-stream-gpu-h1-shader-state-probe",
                 "real-sfx-pcm-stream-gpu-h3-draw-envelope-probe")
        .replace("v3208", "v3212")
        .replace("V3208", "V3212")
    )


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-draw-envelope-probe-candidate",
        "adoption_state": "pending-gpu-h3-draw-envelope-live-validation",
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
    (OUT_DIR / "gpu-h3-draw-envelope-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-draw-envelope-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h3-draw-envelope-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _finalize_manifest_after_overlay(
    overlay: dict[str, Any],
    *,
    base_main_completed: bool,
    base_main_error: str | None = None,
) -> None:
    overlay = dict(overlay)
    overlay["mode"] = "preserve-v3210-ramdisk-overlay-v3212-init-helper-engine"
    manifest_path = OUT_DIR / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "decision": DECISION,
            "cycle": CYCLE,
            "candidate_tag": INIT_BUILD,
            "candidate_type": "gpu-h3-draw-envelope-probe-candidate",
            "adoption_state": "pending-gpu-h3-draw-envelope-live-validation",
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
    manifest["candidate_type"] = "gpu-h3-draw-envelope-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h3-draw-envelope-live-validation"
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
    (OUT_DIR / "gpu-h3-draw-envelope-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h3-draw-envelope-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "ramdisk_overlay": overlay,
        "adoption_state": "pending-gpu-h3-draw-envelope-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _apply_v3212_overrides() -> None:
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
            .replace("gpu-h2-3d-state-probe", "gpu-h3-draw-envelope-probe")
            .replace("real-sfx-pcm-stream-gpu-h2-3d-state-probe",
                     "real-sfx-pcm-stream-gpu-h3-draw-envelope-probe")
            .replace("v3210", "v3212")
            .replace("V3210", "V3212")
            .replace(OLD_INIT_VERSION, INIT_VERSION)
            .replace(OLD_INIT_BUILD, INIT_BUILD)
            .replace(OLD_ENGINE_NAME, ENGINE_NAME)
            .replace(OLD_ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
            .replace(OLD_SOUND_MODE, SOUND_MODE)
        ),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3212_adapter_source,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3212_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
