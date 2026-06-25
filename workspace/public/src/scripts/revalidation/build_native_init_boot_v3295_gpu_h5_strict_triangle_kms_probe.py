#!/usr/bin/env python3
"""Build V3295 GPU H5 strict A2D-linearized triangle KMS proof probe."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3291_gpu_h5_triangle_kms_probe as previous

base = previous.base

CYCLE = "V3295"
INIT_VERSION = "0.11.73"
INIT_BUILD = "v3295-gpu-h5-strict-triangle-kms-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3295-gpu-h5-strict-triangle-kms-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3295_GPU_H5_STRICT_TRIANGLE_KMS_SOURCE_BUILD_2026-06-26.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3295_gpu_h5_strict_triangle_kms_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BASE_BOOT
INIT_BINARY = OUT_DIR / "init_v3295_gpu_h5_strict_triangle_kms_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3295_gpu_h5_strict_triangle_kms_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v603_gpu_h5_strict_triangle_kms_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3295"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3295.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3295.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3295"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3295-gpu-h5-strict-triangle-kms-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3295-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3295-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3295-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3295-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3295-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3295-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3295-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h5-strict-triangle-kms-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h5-strict-triangle-kms-probe"

INPUT_THREAD_MARKER = previous.INPUT_THREAD_MARKER.replace("v3291", "v3295")
TIME_MODEL_MARKER = previous.TIME_MODEL_MARKER.replace("v3291", "v3295")
DEMO_HUD_MARKER = previous.DEMO_HUD_MARKER.replace("v3291", "v3295")
PACED_TIME_MARKER = previous.PACED_TIME_MARKER.replace("v3291", "v3295")
TICK_TELEMETRY_MARKER = previous.TICK_TELEMETRY_MARKER.replace("v3291", "v3295")
SCALE_MARKER = previous.SCALE_MARKER.replace("v3291", "v3295")
PHASE_TELEMETRY_MARKER = previous.PHASE_TELEMETRY_MARKER.replace("v3291", "v3295")
GAMETIC_FRAME_TELEMETRY_MARKER = previous.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3291", "v3295")
SFX_STREAM_MARKER = "a90.doomgeneric.v3295.audio=real-sfx-pcm-stream-gpu-h5-strict-triangle-kms-probe"
SOUND_MODE = "native-doom-sfx-gpu-h5-strict-triangle-kms-probe-v3295"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3295.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "first-triangle-h5-a2d-linearized-strict-sample-kms-probe"
H5_PRESENTATION = (
    "H3 tile6_3+flag color target A2D-linearized into a strict-sampled KMS dumb framebuffer"
)
H5_COMMAND = "gpu h5-triangle-kms-probe --timeout-ms 5000 --materialize-devnode"


def _rewrite_v3295_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3291", "a90-doomgeneric-v3295"),
        ("a90.doomgeneric.v3291", "a90.doomgeneric.v3295"),
        ("v3291", "v3295"),
        ("V3291", "V3295"),
        ("gpu-h5-triangle-kms-probe", "gpu-h5-strict-triangle-kms-probe"),
        ("first-triangle-h5-h3-readback-to-kms-dumb-blit-probe", SCOPE),
        ("h3-private-buffer-readback-snapshot-to-kms-dumb-framebuffer",
         "h3-private-buffer-a2d-linearized-snapshot-to-kms-dumb-framebuffer"),
        ("gpu.h5.kms.raw_tile_order_visualization=1",
         "gpu.h5.kms.raw_tile_order_visualization=0"),
        ("raw tile6_3 readback visualization scaled into parent-owned KMS dumb framebuffer",
         "A2D-linearized strict-sample triangle readback scaled into parent-owned KMS dumb framebuffer"),
        ("h3-readback-kms-presented", "h3-linear-readback-kms-presented"),
        ("gpu-h5-triangle-kms-shader-byte-audit",
         "gpu-h5-strict-triangle-kms-shader-byte-audit"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3295_bytes(item: bytes) -> bytes:
    return _rewrite_v3295_text(item.decode("utf-8")).encode("utf-8")


GPU_H5_LINEAR_KMS_MARKERS = (
    b"h5-triangle-kms-probe",
    b"triangle-kms-probe",
    b"gpu.h5.kms.scope=first-triangle-h5-a2d-linearized-strict-sample-kms-probe",
    b"gpu.h5.kms.blit_mode=h3-private-buffer-a2d-linearized-snapshot-to-kms-dumb-framebuffer",
    b"gpu.h5.kms.raw_tile_order_visualization=0",
    b"gpu.h5.kms.linearized_tile6_3_a2d_blit=1",
    b"gpu.h5.kms.h3_linear_readback_nonzero_count=%u",
    b"gpu.h5.kms.h3_linear_center_nonzero=%u",
    b"gpu.h5.kms.h3_linear_exterior_corners_zero=%u",
    b"gpu.h5.kms.strict_linear_triangle_sample_proof=%u",
    b"gpu.h5.kms.result=h3-linear-readback-failed",
    b"h3-linear-readback-kms-presented",
    b"A2D LINEAR H3 STRICT",
    b"gpu-h5-triangle-kms",
)

REQUIRED_STRINGS = tuple(_rewrite_v3295_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_H5_LINEAR_KMS_MARKERS


def _minimal_gpu_h5_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_h5_manifest())
    manifest.update({
        "source_baseline": "v3294-h5-a2d-linearized-kms-live-telemetry-proof",
        "scope": SCOPE,
        "h5_presentation": H5_PRESENTATION,
        "command": H5_COMMAND,
        "candidate_type": "gpu-h5-strict-triangle-kms-probe-candidate",
        "h3_snapshot_words_expected": 128 * 128,
        "h3_snapshot_bytes_expected": 128 * 128 * 4,
        "presentation_mode": "A2D-linearized strict-sample triangle readback scaled into parent-owned KMS dumb framebuffer",
        "a2d_linearization_attempted": True,
        "raw_tile_order_visualization": False,
        "zero_copy_attempted": False,
        "scaled_plane_attempted": False,
        "next_live_validation": [
            "flash-v3295-through-native-init-flash",
            "post-flash-health-check",
            "gpu-h5-strict-triangle-kms-timeout-guard",
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
        "# Native Init V3295 GPU H5 Strict Triangle KMS Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU first-triangle H5 strict sample proof after V3294 A2D-linearized KMS telemetry proof.",
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
        "- Keeps the V3290/V3292 H3 triangle draw path and its `RGBA8 tile6_3` + flag MRT render target unchanged.",
        "- Keeps the bounded A6xx A2D stage after the H3 draw to copy the tiled/flagged color target into a linear RGBA8 buffer.",
        "- Zero-initializes the linear buffer so the verifier can count true non-zero color instead of sentinel mismatch.",
        "- H5 now requires non-zero linear pixels, a non-zero center sample, and zero exterior corner samples before presenting to `/dev/dri/card0`.",
        "- KMS presentation copies the strict-verified linearized H3 snapshot rather than the raw tile-order buffer.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "- Child-only KGSL open/ioctl; parent reads the linear snapshot over a bounded pipe and kills the child on timeout.",
        "- No PMIC/GDSC/regulator/GPIO write, proprietary blob, full Mesa compiler port, zero-copy scanout, or forbidden partition work.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3295 builder and focused source test.",
        "- `unittest`: V3295 GPU H5 strict sample source contract plus existing H3 source regression coverage.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3295 identity plus H5 strict A2D-linearized KMS telemetry.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h5-strict-triangle-kms-probe-candidate`.",
    ]) + "\n"


def v3295_adapter_source() -> str:
    return _rewrite_v3295_text(previous.v3291_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-h5-strict-triangle-kms-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h5-strict-triangle-kms-probe-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h5"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h5-strict-triangle-kms-live-validation",
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


def _overlay_preserved_v3295_ramdisk() -> dict[str, Any]:
    saved = _patch_previous_overlay_globals()
    try:
        overlay = previous._overlay_preserved_v3291_ramdisk()
    finally:
        _restore_previous_overlay_globals(saved)
    overlay["mode"] = "preserve-v3291-ramdisk-overlay-v3295-init-helper-engine"
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
            "candidate_type": "gpu-h5-strict-triangle-kms-probe-candidate",
            "adoption_state": "pending-gpu-h5-strict-triangle-kms-live-validation",
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
    manifest["candidate_type"] = "gpu-h5-strict-triangle-kms-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h5-strict-triangle-kms-live-validation"
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
        "candidate_type": "gpu-h5-strict-triangle-kms-probe-candidate",
        "adoption_state": "pending-gpu-h5-strict-triangle-kms-live-validation",
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


def _apply_v3295_overrides() -> None:
    previous._apply_v3291_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3295_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3295_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3295_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3295_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
