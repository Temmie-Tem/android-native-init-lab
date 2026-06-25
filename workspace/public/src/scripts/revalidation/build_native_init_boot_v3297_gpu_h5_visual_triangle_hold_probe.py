#!/usr/bin/env python3
"""Build V3297 GPU H5 visual-close triangle hold probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3295_gpu_h5_strict_triangle_kms_probe as previous

base = previous.base

CYCLE = "V3297"
INIT_VERSION = "0.11.74"
INIT_BUILD = "v3297-gpu-h5-visual-triangle-hold-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3297-gpu-h5-visual-triangle-hold-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3297_GPU_H5_VISUAL_TRIANGLE_HOLD_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3297_gpu_h5_visual_triangle_hold_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3297_gpu_h5_visual_triangle_hold_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3297_gpu_h5_visual_triangle_hold_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v603_gpu_h5_visual_triangle_hold_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3297"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3297.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3297.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3297"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3297-gpu-h5-visual-triangle-hold-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3297-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3297-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3297-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3297-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3297-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3297-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3297-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h5-visual-triangle-hold-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h5-visual-triangle-hold-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3295", "v3297")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3295", "v3297")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3295", "v3297")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3295", "v3297")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3295", "v3297")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3295", "v3297")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3295", "v3297")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3295", "v3297")
SFX_STREAM_MARKER = "a90.doomgeneric.v3297.audio=real-sfx-pcm-stream-gpu-h5-visual-triangle-hold-probe"
SOUND_MODE = "native-doom-sfx-gpu-h5-visual-triangle-hold-probe-v3297"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3297.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h5-visual-close-held-kms-probe"
H5_PRESENTATION = "linearized H3 triangle mask centered, solid-filled, and held on KMS for visual confirmation"
H5_COMMAND = "gpu h5-triangle-kms-probe --timeout-ms 5000 --hold-ms 30000 --materialize-devnode"


def _rewrite_v3297_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3295", "a90-doomgeneric-v3297"),
        ("a90.doomgeneric.v3295", "a90.doomgeneric.v3297"),
        ("v3295", "v3297"),
        ("V3295", "V3297"),
        ("gpu-h5-strict-triangle-kms-probe", "gpu-h5-visual-triangle-hold-probe"),
        ("first-triangle-h5-a2d-linearized-strict-sample-kms-probe", SCOPE),
        ("h3-private-buffer-a2d-linearized-snapshot-to-kms-dumb-framebuffer",
         "h3-private-linear-snapshot-solid-triangle-mask-to-kms-dumb-framebuffer"),
        ("h3-linear-readback-kms-presented", "h3-visual-triangle-kms-presented"),
        ("A2D LINEAR H3 STRICT", "GPU H5 VISUAL CLOSE"),
        ("gpu-h5-strict-triangle-kms-shader-byte-audit",
         "gpu-h5-visual-triangle-hold-shader-byte-audit"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3297_bytes(item: bytes) -> bytes:
    return _rewrite_v3297_text(item.decode("utf-8")).encode("utf-8")


GPU_H5_VISUAL_KMS_MARKERS = (
    b"h5-triangle-kms-probe",
    b"gpu.h5.kms.scope=first-triangle-h5-visual-close-held-kms-probe",
    b"gpu.h5.vis.mode=linear-nonzero-mask-solid-fill-centered",
    b"gpu.h5.vis.source_bbox=%u,%u,%u,%u",
    b"gpu.h5.vis.hold_ms=%d",
    b"gpu.h5.vis.result=triangle-presented-held",
    b"h3-visual-triangle-kms-presented",
    b"GPU H5 VISUAL CLOSE",
    b"RECOGNIZABLE TRIANGLE HOLD",
)

REQUIRED_STRINGS = tuple(_rewrite_v3297_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H5_VISUAL_KMS_MARKERS


def _minimal_gpu_h5_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h5_manifest())
    manifest.update({
        "source_baseline": "v3296-h5-strict-triangle-kms-live-proof",
        "scope": SCOPE,
        "h5_presentation": H5_PRESENTATION,
        "command": H5_COMMAND,
        "candidate_type": "gpu-h5-visual-triangle-hold-probe-candidate",
        "presentation_mode": "solid filled visual triangle derived from the A2D-linearized nonzero mask",
        "a2d_linearization_attempted": True,
        "visual_hold_default_ms": 30000,
        "raw_tile_order_visualization": False,
        "zero_copy_attempted": False,
        "scaled_plane_attempted": False,
        "next_live_validation": [
            "flash-v3297-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h5-visual-triangle-hold-timeout-guard",
            "operator-panel-visual-confirmation",
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
        "# Native Init V3297 GPU H5 Visual Triangle Hold Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU H5 human visual close after V3296 strict telemetry proof.",
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
        "- Keeps the V3296 strict GPU proof path: H3 tiled color target, A2D linearization, nonzero/center/corner verifier.",
        "- Presents a recognizable centered triangle by scaling the linear nonzero mask bbox and filling it with a solid high-contrast color.",
        "- Stops autohud before KMS presentation so the proof screen is not immediately overwritten.",
        "- Adds a bounded visual hold with `gpu.h5.vis.result=triangle-presented-held` on success.",
        "",
        "## Safety",
        "",
        "- KMS present stays on the existing `/dev/dri/card0` path.",
        "- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, zero-copy scanout, or forbidden partition work.",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3297 builder and focused source test.",
        "- `unittest`: V3297 visual source contract plus existing H5 strict source regression coverage.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3297 identity plus H5 visual hold telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h5-visual-triangle-hold-probe-candidate`.",
    ]) + "\n"


def v3297_adapter_source() -> str:
    return _rewrite_v3297_text(previous.v3295_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h5-visual-triangle-hold-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h5-visual-triangle-hold-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h5"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h5-visual-triangle-hold-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_previous_builder_globals() -> list[tuple[Any, str, Any]]:
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


def _restore_previous_builder_globals(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _overlay_preserved_v3297_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_builder_globals()
    try:
        overlay = previous._overlay_preserved_v3295_ramdisk()
    finally:
        _restore_previous_builder_globals(saved)
    overlay["mode"] = "preserve-v3295-ramdisk-overlay-v3297-init-helper-engine"
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
            "candidate_type": "gpu-h5-visual-triangle-hold-probe-candidate",
            "adoption_state": "pending-gpu-h5-visual-triangle-hold-live-validation",
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
    manifest["candidate_type"] = "gpu-h5-visual-triangle-hold-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h5-visual-triangle-hold-live-validation"
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
    manifest["gpu_h5"] = _minimal_gpu_h5_manifest()
    manifest["gpu_h5"]["ramdisk_overlay"] = overlay
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
        "candidate_type": "gpu-h5-visual-triangle-hold-probe-candidate",
        "adoption_state": "pending-gpu-h5-visual-triangle-hold-live-validation",
        "gpu_h5": _minimal_gpu_h5_manifest(),
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


def _apply_v3297_overrides() -> None:
    previous._apply_v3295_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3297_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3297_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3297_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3297_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
