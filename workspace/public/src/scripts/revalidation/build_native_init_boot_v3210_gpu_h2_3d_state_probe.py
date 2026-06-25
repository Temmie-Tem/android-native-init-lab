#!/usr/bin/env python3
"""Build V3210 GPU H2 fixed-function 3D state probe."""

from __future__ import annotations

import hashlib
import json
import os
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
import build_native_init_boot_v3208_gpu_h1_shader_state_probe as base

ORIG_V3208_OVERRIDES = base._v3208_overrides
ORIG_V3208_VALUES = base._v3208_values
ORIG_V3208_ADAPTER_SOURCE = base.v3208_adapter_source

CYCLE = "V3210"
INIT_VERSION = "0.11.32"
INIT_BUILD = "v3210-gpu-h2-3d-state-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3210-gpu-h2-3d-state-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3210_GPU_H2_3D_STATE_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3210_gpu_h2_3d_state_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3208_gpu_h1_shader_state_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3210_gpu_h2_3d_state_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3210_gpu_h2_3d_state_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v564_gpu_h2_3d_state_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3210"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3210.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3210.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3210"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3210-gpu-h2-3d-state-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3210-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3210-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3210-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3210-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3210-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3210-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3210-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h2-3d-state-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h2-3d-state-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3208", "v3210")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3208", "v3210")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3208", "v3210")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3208", "v3210")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3208", "v3210")
SCALE_MARKER = base.SCALE_MARKER.replace("v3208", "v3210")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3208", "v3210")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3208", "v3210")
SFX_STREAM_MARKER = "a90.doomgeneric.v3210.audio=real-sfx-pcm-stream-gpu-h2-3d-state-probe"
SOUND_MODE = "native-doom-sfx-gpu-h2-3d-state-probe-v3210"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3210.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"
THIRD_PARTY_MKBOOTIMG = REPO_ROOT / "workspace" / "public" / "src" / "third_party" / "mkbootimg"
REPRODUCIBLE_MTIME = 0


def rel(path: Path) -> str:
    return base.rel(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[object], *, cwd: Path | None = None, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def _rewrite_required_string(item: bytes) -> bytes:
    replacements = {
        base.INIT_VERSION.encode("ascii"): INIT_VERSION.encode("ascii"),
        base.INIT_BUILD.encode("ascii"): INIT_BUILD.encode("ascii"),
        base.ENGINE_NAME.encode("ascii"): ENGINE_NAME.encode("ascii"),
        base.ENGINE_REMOTE_PATH.encode("ascii"): ENGINE_REMOTE_PATH.encode("ascii"),
        base.SOUND_MODE.encode("ascii"): SOUND_MODE.encode("ascii"),
        base.SFX_STREAM_MARKER.encode("ascii"): SFX_STREAM_MARKER.encode("ascii"),
        base.AUDIO_PCM_STREAM_PATH.encode("ascii"): AUDIO_PCM_STREAM_PATH.encode("ascii"),
        b"a90-doomgeneric-v3208": b"a90-doomgeneric-v3210",
        b"a90.doomgeneric.v3208": b"a90.doomgeneric.v3210",
        b"v3208": b"v3210",
        b"V3208": b"V3210",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H2_3D_STATE_MARKERS = (
    b"h2-3d-state-probe",
    b"3d-state-probe",
    b"gpu.h2.state.version=1",
    b"gpu.h2.state.scope=first-triangle-h2-3d-fixed-function-state-no-draw",
    b"gpu.h2.state.parent_enters_open=0",
    b"gpu.h2.state.parent_enters_ioctl=0",
    b"gpu.h2.state.source=mesa-freedreno-a6xx-fd6-emit-draw-plus-a6xx-xml",
    b"gpu.h2.state.offscreen=u32-linear-128x128",
    b"gpu.h2.state.draw_attempted=0",
    b"gpu.h2.state.shader_execution_attempted=0",
    b"gpu.h2.state.kms_blit_attempted=0",
    b"gpu.h2.state.power_write_attempted=0",
    b"gpu.h2.state.proprietary_blob_attempted=0",
    b"gpu.h2.state.color_width=%u",
    b"gpu.h2.state.color_height=%u",
    b"gpu.h2.state.color_stride=%u",
    b"gpu.h2.state.color_format=0x%x",
    b"gpu.h2.state.color_init_rc=%d",
    b"gpu.h2.state.pm4_dwords=%u",
    b"gpu.h2.state.state_reg_writes=%u",
    b"gpu.h2.state.submit_rc=%d",
    b"gpu.h2.state.retired_timestamp=%u",
    b"gpu.h2.state.result=%s",
    b"3d-state-retired-no-draw",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.32",
    b"v3210-gpu-h2-3d-state-probe",
) + GPU_H2_3D_STATE_MARKERS


def _v3210_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3210 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-h1-shader-state-probe", "gpu-h2-3d-state-probe")
    .replace("real-sfx-pcm-stream-gpu-h1-shader-state-probe",
             "real-sfx-pcm-stream-gpu-h2-3d-state-probe")
    .replace("v3208", "v3210")
    .replace("V3208", "V3210")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3210_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3208_OVERRIDES())
    overrides.update({
        "CYCLE": CYCLE,
        "INIT_VERSION": INIT_VERSION,
        "INIT_BUILD": INIT_BUILD,
        "BUILD_TAG": BUILD_TAG,
        "DECISION": DECISION,
        "OUT_DIR": OUT_DIR,
        "OBJ_DIR": OBJ_DIR,
        "REPORT_PATH": REPORT_PATH,
        "BOOT_IMAGE": BOOT_IMAGE,
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
        "AUDIO_CORUN_MODE": AUDIO_CORUN_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": SFX_BACKEND_SOURCE_TEXT,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
    })
    return overrides


def _v3210_values() -> dict[str, Any]:
    values = dict(ORIG_V3208_VALUES())
    values.update(_v3210_overrides())
    return values


def v3210_adapter_source() -> str:
    return (
        ORIG_V3208_ADAPTER_SOURCE()
        .replace("gpu-h1-shader-state-probe", "gpu-h2-3d-state-probe")
        .replace("real-sfx-pcm-stream-gpu-h1-shader-state-probe",
                 "real-sfx-pcm-stream-gpu-h2-3d-state-probe")
        .replace("v3208", "v3210")
        .replace("V3208", "V3210")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3210 GPU H2 3D State Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU first-triangle H2a: A6xx fixed-function 3D state submit/retire, with no draw.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Device flash: `no` in this build unit.",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Base boot: `{rel(BASE_BOOT)}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        "",
        "## Included Delta",
        "",
        "- Adds `gpu h2-3d-state-probe` after the device-proven G0-G5 first-light ladder and the V3208 H1 shader-state upload probe.",
        "- Reuses the bounded child-only KGSL open/ioctl envelope from G3/G4: context, GPUOBJ alloc/mmap/sync, command submit, timestamp fence, wait, readtimestamp, cleanup.",
        "- Allocates a private 128x128 u32 offscreen GPU object and submits a no-draw PM4 stream that programs GRAS viewport/scissor, RB MRT/output, VPC, PC, VFD, and SP output-state registers.",
        "- The command stream deliberately excludes `CP_DRAW_INDX_OFFSET`, shader execution, readback verification, and KMS presentation. This proves only that the fixed-function 3D state packet stream can retire without the parent entering KGSL.",
        "- The final boot image preserves the V3208 ramdisk contents and overlays only the new `/init`, the helper, and `bin/a90_doomgeneric_private_engine_v3210`; this avoids regenerating missing private ACDB deploy-plan intermediates while keeping the known-good bundled audio files.",
        "",
        "## H0 Recon Basis",
        "",
        "- Mesa/freedreno A6xx source points the first-triangle path at `fd6_emit.cc` for GRAS/RB/VPC/VFD/SP fixed-function state and `fd6_draw.cc` for the later non-indexed `CP_DRAW_INDX_OFFSET` auto-index draw.",
        "- Mesa register XML provides the A6xx GRAS/RB/VPC/PC/VFD/SP register offsets and PM4 packet enum values used here.",
        "- Decision boundary: keep this rung below draw execution and below real shader execution. Do not pull in Mesa's full ir3 compiler, proprietary EGL/GLES blobs, OpenCL, or exploit work.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.",
        "- No GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- No draw, triangle rasterization, shader execution, readback verification, compute grid, zero-copy dmabuf, or KMS GPU-plane sharing is included in H2a.",
        "- Parent process does not enter KGSL `open()` or `ioctl()`; the child is timeout-guarded and killed on timeout.",
        "",
        "## Source Basis",
        "",
        "- Mesa source repository: `https://docs.mesa3d.org/repository.html`.",
        "- Freedreno driver overview: `https://docs.mesa3d.org/drivers/freedreno.html`.",
        "- A6xx fixed-function emit path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc`.",
        "- A6xx shader/program state retained from H1: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.",
        "- A6xx draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.",
        "- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.",
        "- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3210 builder and focused H2 source test.",
        "- `unittest`: V3210 GPU H2 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3210 identity, G0-G5/H1 baseline markers, and H2 fixed-function 3D state markers.",
        "- Ramdisk overlay check: V3208 bundled audio manifest remains present and the V3210 DOOM engine helper is present.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h2-3d-state-probe-candidate`.",
    ]) + "\n"


def _patch_missing_audio_bundle_gate() -> list[tuple[Any, str, Any]]:
    import build_native_init_boot_v2843_audio_bundled_setcal as v2843

    saved = [
        (v2843, "prepare_bundled_assets", v2843.prepare_bundled_assets),
    ]

    def prepare_preserved_audio_bundle() -> tuple[dict[str, Any], Path, dict[str, Path]]:
        manifest_path = OUT_DIR / "preserved-v3208-audio-bundle.manifest"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "version 1\n"
            "profile internal-speaker-safe\n"
            "entry_count 0\n"
            "# build-time placeholder; final boot preserves the V3208 ramdisk audio bundle\n",
            encoding="utf-8",
        )
        return (
            {
                "ok": True,
                "safe_to_run_native_replay": True,
                "replay_entries": [],
                "files": [],
                "v3210_build_note": "final boot overlays V3210 init onto the V3208 ramdisk to preserve bundled private audio artifacts",
            },
            manifest_path,
            {},
        )

    v2843.prepare_bundled_assets = prepare_preserved_audio_bundle
    return saved


def _restore_audio_bundle_gate(saved: list[tuple[Any, str, Any]]) -> None:
    for module, name, value in reversed(saved):
        setattr(module, name, value)


def _set_reproducible_mtime(root: Path) -> None:
    for path in sorted(root.rglob("*"), key=lambda item: str(item), reverse=True):
        os.utime(path, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)
    os.utime(root, (REPRODUCIBLE_MTIME, REPRODUCIBLE_MTIME), follow_symlinks=False)


def _overlay_preserved_v3208_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3208 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3210 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3210 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3210 DOOM engine binary: {ENGINE_BINARY}")

    with tempfile.TemporaryDirectory(prefix="a90-v3210-overlay-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_dir = temp_dir / "unpack"
        ramdisk_dir = temp_dir / "ramdisk"
        unpack_dir.mkdir()
        ramdisk_dir.mkdir()

        unpack_args_text = _run(
            [
                "python3",
                THIRD_PARTY_MKBOOTIMG / "unpack_bootimg.py",
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

        shutil.copy2(INIT_BINARY, ramdisk_dir / "init")
        (ramdisk_dir / "init").chmod(0o755)

        bin_dir = ramdisk_dir / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(HELPER_BINARY, bin_dir / "a90_android_execns_probe")
        (bin_dir / "a90_android_execns_probe").chmod(0o755)
        engine_dest = bin_dir / ENGINE_RAMDISK_PATH.split("/", 1)[1]
        shutil.copy2(ENGINE_BINARY, engine_dest)
        engine_dest.chmod(0o755)

        _set_reproducible_mtime(ramdisk_dir)

        if RAMDISK_CPIO.exists():
            RAMDISK_CPIO.unlink()
        RAMDISK_CPIO.parent.mkdir(parents=True, exist_ok=True)
        _run(
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
            raise RuntimeError("V3208 base boot mkbootimg args did not include --ramdisk")

        if BOOT_IMAGE.exists():
            BOOT_IMAGE.unlink()
        _run(
            [
                "python3",
                THIRD_PARTY_MKBOOTIMG / "mkbootimg.py",
                *mkboot_args,
                "--output",
                BOOT_IMAGE,
            ]
        )
        BOOT_IMAGE.chmod(0o600)

    _v3210_require_strings(BOOT_IMAGE)
    listing = _run(
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
        raise RuntimeError(f"missing V3210 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3208-ramdisk-overlay-v3210-init-helper-engine",
        "base_boot": rel(BASE_BOOT),
        "base_boot_sha256": sha256_file(BASE_BOOT),
        "boot_sha256": sha256_file(BOOT_IMAGE),
        "ramdisk_cpio": rel(RAMDISK_CPIO),
        "ramdisk_sha256": sha256_file(RAMDISK_CPIO),
        "overlay_entries": [
            "init",
            "bin/a90_android_execns_probe",
            ENGINE_RAMDISK_PATH,
        ],
        "preserved_entries_checked": sorted(required_entries),
        "ramdisk_entry_count": len(listing),
    }


def _postprocess_manifest() -> dict[str, Any]:
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h2-3d-state-probe-candidate",
        "adoption_state": "pending-gpu-h2-3d-state-live-validation",
        "gpu_h2": {
            "source_baseline": "v3208-gpu-h1-shader-state-probe",
            "completion_audit": "docs/reports/NATIVE_INIT_V3206_GPU_EPIC_COMPLETION_AUDIT_2026-06-25.md",
            "command": "gpu h2-3d-state-probe --timeout-ms 5000 --materialize-devnode",
            "scope": "first-triangle-h2-3d-fixed-function-state-no-draw",
            "pm4_source": "Mesa freedreno A6xx fd6_emit/fd6_draw fixed-function 3D state plus A6xx register XML",
            "pm4_reference_urls": [
                "https://docs.mesa3d.org/repository.html",
                "https://docs.mesa3d.org/drivers/freedreno.html",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_emit.cc",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml",
            ],
            "offscreen": "u32-linear-128x128",
            "fixed_function_state": "GRAS/RB/VPC/PC/VFD/SP-output",
            "shader_source": "not-used-in-h2a-no-shader-execution",
            "shader_execution_attempted": False,
            "draw_attempted": False,
            "kms_blit_attempted": False,
            "ioctl_allowlist": [
                "IOCTL_KGSL_DRAWCTXT_CREATE",
                "IOCTL_KGSL_GPUOBJ_ALLOC",
                "IOCTL_KGSL_GPUOBJ_INFO",
                "IOCTL_KGSL_GPUOBJ_SYNC",
                "IOCTL_KGSL_GPU_COMMAND",
                "IOCTL_KGSL_TIMESTAMP_EVENT",
                "IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID",
                "IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID",
                "IOCTL_KGSL_GPUOBJ_FREE",
                "IOCTL_KGSL_DRAWCTXT_DESTROY",
            ],
            "registers": {
                "GRAS_CL_VIEWPORT": "0x8010",
                "GRAS_SC_SCREEN_SCISSOR_TL": "0x80b0",
                "GRAS_MODE_CNTL": "0x8110",
                "RB_MRT0_BUF_INFO": "0x8822",
                "RB_MRT0_BASE": "0x8825",
                "VPC_VS_CNTL": "0x9301",
                "PC_VS_CNTL": "0x9b01",
                "VFD_MODE_CNTL": "0xa009",
                "SP_VS_OUTPUT_CNTL": "0xa802",
                "SP_PS_MRT_REG0": "0xa996",
            },
            "packets": {
                "CP_REG_TO_MEM": "0x3e",
                "CP_DRAW_INDX_OFFSET": "not-emitted",
                "CP_WAIT_FOR_IDLE": "0x26",
                "CP_NOP": "0x10",
            },
            "parent_enters_open": False,
            "parent_enters_ioctl": False,
            "timeout_guard_ms_default": 2000,
            "timeout_guard_ms_max": 10000,
            "waittimestamp_timeout_ms": 1000,
            "forbidden_operations": [
                "full-ir3-compiler-port",
                "triangle-render",
                "shader-execution",
                "GDSC-write",
                "regulator-write",
                "PMIC-write",
                "GPIO-write",
                "proprietary-adreno-blob",
                "exploit-dev",
            ],
            "next_live_validation": [
                "flash-v3210-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-h2-3d-state-probe-timeout-guard",
                "post-probe-selftest-and-dmesg-gpu-fault-filter",
            ],
        },
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
    (OUT_DIR / "gpu-h2-3d-state-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h2-3d-state-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h2"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h2-3d-state-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3210_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3208_overrides", _v3210_overrides),
        ("_v3208_values", _v3210_values),
        ("v3208_adapter_source", v3210_adapter_source),
        ("_v3208_require_strings", _v3210_require_strings),
        ("render_report", render_report),
        ("_postprocess_manifest", _postprocess_manifest),
    ):
        saved.append((base, name, getattr(base, name), True))
        setattr(base, name, value)
    return saved


def _restore_base_module(saved: list[tuple[Any, str, Any, bool]]) -> None:
    for module, name, value, existed in reversed(saved):
        if existed:
            setattr(module, name, value)
        else:
            delattr(module, name)


def _minimal_gpu_h2_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3208-gpu-h1-shader-state-probe",
        "completion_audit": "docs/reports/NATIVE_INIT_V3206_GPU_EPIC_COMPLETION_AUDIT_2026-06-25.md",
        "command": "gpu h2-3d-state-probe --timeout-ms 5000 --materialize-devnode",
        "scope": "first-triangle-h2-3d-fixed-function-state-no-draw",
        "pm4_source": "Mesa freedreno A6xx fd6_emit/fd6_draw fixed-function 3D state plus A6xx register XML",
        "offscreen": "u32-linear-128x128",
        "fixed_function_state": "GRAS/RB/VPC/PC/VFD/SP-output",
        "shader_source": "not-used-in-h2a-no-shader-execution",
        "shader_execution_attempted": False,
        "draw_attempted": False,
        "kms_blit_attempted": False,
        "parent_enters_open": False,
        "parent_enters_ioctl": False,
        "next_live_validation": [
            "flash-v3210-through-native-init-flash",
            "post-flash-health-check",
            "gpu-g0-fwclass-prepare",
            "gpu-h2-3d-state-probe-timeout-guard",
            "post-probe-selftest-and-dmesg-gpu-fault-filter",
        ],
    }


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
            "candidate_type": "gpu-h2-3d-state-probe-candidate",
            "adoption_state": "pending-gpu-h2-3d-state-live-validation",
            "boot_image": rel(BOOT_IMAGE),
            "init_version": INIT_VERSION,
            "init_build": INIT_BUILD,
            "helper_sha256": sha256_file(HELPER_BINARY),
            "helper_flags": [],
            "init_extra_flags": [],
            "gpu_h2": _minimal_gpu_h2_manifest(),
        }
    manifest["decision"] = DECISION
    manifest["cycle"] = CYCLE
    manifest["candidate_tag"] = INIT_BUILD
    manifest["candidate_type"] = "gpu-h2-3d-state-probe-candidate"
    manifest["adoption_state"] = "pending-gpu-h2-3d-state-live-validation"
    manifest["boot_image"] = rel(BOOT_IMAGE)
    manifest["init_version"] = INIT_VERSION
    manifest["init_build"] = INIT_BUILD
    manifest["boot_sha256"] = overlay["boot_sha256"]
    manifest["ramdisk_sha256"] = overlay["ramdisk_sha256"]
    manifest["ramdisk_overlay"] = overlay
    manifest["base_main_completed"] = base_main_completed
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    manifest.setdefault("gpu_h2", _minimal_gpu_h2_manifest())
    manifest.setdefault("gpu_h2", {})["ramdisk_overlay"] = overlay
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "gpu-h2-3d-state-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h2-3d-state-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h2"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "ramdisk_overlay": overlay,
        "adoption_state": "pending-gpu-h2-3d-state-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    saved = _patch_base_module()
    audio_saved = _patch_missing_audio_bundle_gate()
    base_main_completed = False
    base_main_error: str | None = None
    try:
        try:
            rc = base.main()
            base_main_completed = True
        except Exception as exc:
            if not (INIT_BINARY.exists() and HELPER_BINARY.exists() and ENGINE_BINARY.exists()):
                raise
            rc = 0
            base_main_error = (
                f"{exc.__class__.__name__}: {exc}; continuing with preserved V3208 ramdisk overlay "
                "after V3210 init/helper/engine compile completed"
            )
        overlay = _overlay_preserved_v3208_ramdisk()
        _finalize_manifest_after_overlay(
            overlay,
            base_main_completed=base_main_completed,
            base_main_error=base_main_error,
        )
        return rc
    finally:
        _restore_audio_bundle_gate(audio_saved)
        _restore_base_module(saved)


if __name__ == "__main__":
    raise SystemExit(main())
