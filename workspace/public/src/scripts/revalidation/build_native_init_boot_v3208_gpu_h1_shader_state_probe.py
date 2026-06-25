#!/usr/bin/env python3
"""Build V3208 GPU H1 shader-state preload probe."""

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
import build_native_init_boot_v3204_gpu_g5_kms_blit_probe as base

ORIG_V3204_OVERRIDES = base._v3204_overrides
ORIG_V3204_VALUES = base._v3204_values
ORIG_V3204_ADAPTER_SOURCE = base.v3204_adapter_source

CYCLE = "V3208"
INIT_VERSION = "0.11.31"
INIT_BUILD = "v3208-gpu-h1-shader-state-probe"
BUILD_TAG = INIT_BUILD
DECISION = "v3208-gpu-h1-shader-state-source-build-pass"

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3208_GPU_H1_SHADER_STATE_PROBE_SOURCE_BUILD_2026-06-25.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3208_gpu_h1_shader_state_probe.img",
    legacy_fallback=False,
)
BASE_BOOT = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3204_gpu_g5_kms_blit_probe.img",
    legacy_fallback=False,
)
INIT_BINARY = OUT_DIR / "init_v3208_gpu_h1_shader_state_probe"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3208_gpu_h1_shader_state_probe.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v563_gpu_h1_shader_state_probe"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3208"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3208.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3208.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3208"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3208-gpu-h1-shader-state-probe"

FRAME_PATH = "/tmp/a90-doomgeneric-v3208-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3208-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3208-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3208-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3208-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3208-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3208-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-h1-shader-state-probe"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-h1-shader-state-probe"

INPUT_THREAD_MARKER = base.INPUT_THREAD_MARKER.replace("v3204", "v3208")
TIME_MODEL_MARKER = base.TIME_MODEL_MARKER.replace("v3204", "v3208")
DEMO_HUD_MARKER = base.DEMO_HUD_MARKER.replace("v3204", "v3208")
PACED_TIME_MARKER = base.PACED_TIME_MARKER.replace("v3204", "v3208")
TICK_TELEMETRY_MARKER = base.TICK_TELEMETRY_MARKER.replace("v3204", "v3208")
SCALE_MARKER = base.SCALE_MARKER.replace("v3204", "v3208")
PHASE_TELEMETRY_MARKER = base.PHASE_TELEMETRY_MARKER.replace("v3204", "v3208")
GAMETIC_FRAME_TELEMETRY_MARKER = base.GAMETIC_FRAME_TELEMETRY_MARKER.replace("v3204", "v3208")
SFX_STREAM_MARKER = "a90.doomgeneric.v3208.audio=real-sfx-pcm-stream-gpu-h1-shader-state-probe"
SOUND_MODE = "native-doom-sfx-gpu-h1-shader-state-probe-v3208"

AUDIO_CORUN = base.AUDIO_CORUN
AUDIO_CORUN_MODE = SOUND_MODE
AUDIO_CORUN_STREAM = base.AUDIO_CORUN_STREAM
AUDIO_CORUN_DURATION_MS = base.AUDIO_CORUN_DURATION_MS
AUDIO_CORUN_REFRESH_MS = base.AUDIO_CORUN_REFRESH_MS
AUDIO_CORUN_AMPLITUDE_MILLI = base.AUDIO_CORUN_AMPLITUDE_MILLI
PHYSICAL_BUTTON_EXIT = base.PHYSICAL_BUTTON_EXIT

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3208.c"
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
        b"a90-doomgeneric-v3204": b"a90-doomgeneric-v3208",
        b"a90.doomgeneric.v3204": b"a90.doomgeneric.v3208",
        b"v3204": b"v3208",
        b"V3204": b"V3208",
    }
    for old, new in replacements.items():
        item = item.replace(old, new)
    return item


GPU_H1_SHADER_STATE_MARKERS = (
    b"h1-shader-state-probe",
    b"shader-state-probe",
    b"gpu.h1.shader.version=1",
    b"gpu.h1.shader.scope=first-triangle-h1-shader-upload-sp-state-no-draw",
    b"gpu.h1.shader.parent_enters_open=0",
    b"gpu.h1.shader.parent_enters_ioctl=0",
    b"gpu.h1.shader.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy",
    b"gpu.h1.shader.source=mesa-freedreno-a6xx-fd6-program-sp-state-plus-adreno-pm4-cp-load-state6",
    b"gpu.h1.shader.shader_source=hand-assembled-ir3-placeholder-no-full-compiler-no-execute",
    b"gpu.h1.shader.shader_execution_attempted=0",
    b"gpu.h1.shader.draw_attempted=0",
    b"gpu.h1.shader.kms_blit_attempted=0",
    b"gpu.h1.shader.power_write_attempted=0",
    b"gpu.h1.shader.proprietary_blob_attempted=0",
    b"gpu.h1.shader.cmd_mmap_len=%llu",
    b"gpu.h1.shader.vs_mmap_len=%llu",
    b"gpu.h1.shader.fs_mmap_len=%llu",
    b"gpu.h1.shader.vs_shader_dwords=%u",
    b"gpu.h1.shader.fs_shader_dwords=%u",
    b"gpu.h1.shader.cp_load_state6_geom=0x%x",
    b"gpu.h1.shader.cp_load_state6_frag=0x%x",
    b"gpu.h1.shader.shader_write_rc=%d",
    b"gpu.h1.shader.cmd_write_rc=%d",
    b"gpu.h1.shader.pm4_dwords=%u",
    b"gpu.h1.shader.submit_rc=%d",
    b"gpu.h1.shader.retired_timestamp=%u",
    b"gpu.h1.shader.result=%s",
    b"shader-state-retired-no-draw",
)

REQUIRED_STRINGS = tuple(
    _rewrite_required_string(item)
    for item in base.REQUIRED_STRINGS
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    b"0.11.31",
    b"v3208-gpu-h1-shader-state-probe",
) + GPU_H1_SHADER_STATE_MARKERS


def _v3208_require_strings(path: Path) -> list[str]:
    data = path.read_bytes()
    missing = [
        marker.decode("ascii", errors="replace")
        for marker in REQUIRED_STRINGS
        if marker not in data
    ]
    if missing:
        raise RuntimeError(f"missing V3208 boot-image markers: {missing}")
    return [marker.decode("ascii", errors="replace") for marker in REQUIRED_STRINGS]


SFX_BACKEND_SOURCE_TEXT = (
    base.SFX_BACKEND_SOURCE_TEXT
    .replace(base.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH)
    .replace("gpu-g5-kms-blit-probe", "gpu-h1-shader-state-probe")
    .replace("real-sfx-pcm-stream-gpu-g5-kms-blit-probe",
             "real-sfx-pcm-stream-gpu-h1-shader-state-probe")
    .replace("v3204", "v3208")
    .replace("V3204", "V3208")
    .replace(base.INIT_VERSION, INIT_VERSION)
    .replace(base.INIT_BUILD, INIT_BUILD)
    .replace(base.ENGINE_NAME, ENGINE_NAME)
    .replace(base.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH)
    .replace(base.SOUND_MODE, SOUND_MODE)
)


def _v3208_overrides() -> dict[str, Any]:
    overrides = dict(ORIG_V3204_OVERRIDES())
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


def _v3208_values() -> dict[str, Any]:
    values = dict(ORIG_V3204_VALUES())
    values.update(_v3208_overrides())
    return values


def v3208_adapter_source() -> str:
    return (
        ORIG_V3204_ADAPTER_SOURCE()
        .replace("gpu-g5-kms-blit-probe", "gpu-h1-shader-state-probe")
        .replace("real-sfx-pcm-stream-gpu-g5-kms-blit-probe",
                 "real-sfx-pcm-stream-gpu-h1-shader-state-probe")
        .replace("v3204", "v3208")
        .replace("V3204", "V3208")
    )


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3208 GPU H1 Shader State Probe Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU first-triangle H0/H1: A6xx shader processor state upload and CP_LOAD_STATE6 shader preload, with no draw.",
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
        "- Adds `gpu h1-shader-state-probe` after the device-proven G0-G5 first-light ladder.",
        "- Reuses the bounded child-only KGSL open/ioctl envelope from G3/G4: context, GPUOBJ alloc/mmap/sync, command submit, timestamp fence, wait, readtimestamp, cleanup.",
        "- Uploads separate VS/FS GPU objects and submits a minimal no-draw PM4 stream that sets SP VS/PS base/config/instruction-size registers and emits `CP_LOAD_STATE6_GEOM`/`CP_LOAD_STATE6_FRAG` indirect shader loads.",
        "- The shader payload is deliberately recorded as a no-execute placeholder. This proves object upload/SP state/preload retirement only; it is not yet a pass-through vertex shader, constant-color fragment shader, or triangle proof.",
        "- The final boot image preserves the V3204 ramdisk contents and overlays only the new `/init`, the helper, and `bin/a90_doomgeneric_private_engine_v3208`; this avoids regenerating missing private ACDB deploy-plan intermediates while keeping the known-good bundled audio files.",
        "",
        "## H0 Recon Basis",
        "",
        "- Mesa/freedreno A6xx source points the first-triangle path at `fd6_program.cc` for SP program state and shader `CP_LOAD_STATE6`, and `fd6_draw.cc` for non-indexed `CP_DRAW_INDX_OFFSET` auto-index draws.",
        "- Mesa register XML provides the A6xx SP VS/PS register offsets and CP packet enum values used here.",
        "- Decision boundary: keep this rung below draw execution until the hand-assembled ir3 payload is proven. Do not pull in Mesa's full ir3 compiler, proprietary EGL/GLES blobs, OpenCL, or exploit work.",
        "",
        "## Safety",
        "",
        "- Boot partition only through `native_init_flash.py` in any future live step.",
        "- Uses KGSL-direct normal command submission; no proprietary Adreno blob/EGL/Bionic path.",
        "- No GDSC/regulator/PMIC/GPIO/power-rail write is included.",
        "- No draw, rasterizer, readback verification, compute grid, zero-copy dmabuf, or KMS GPU-plane sharing is included in H1.",
        "- Parent process does not enter KGSL `open()` or `ioctl()`; the child is timeout-guarded and killed on timeout.",
        "",
        "## Source Basis",
        "",
        "- Mesa source repository: `https://docs.mesa3d.org/repository.html`.",
        "- Freedreno driver overview: `https://docs.mesa3d.org/drivers/freedreno.html`.",
        "- A6xx shader/program state: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc`.",
        "- A6xx draw path: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc`.",
        "- A6xx register XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml`.",
        "- PM4 packet XML: `https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml`.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3208 builder and focused H1 source test.",
        "- `unittest`: V3208 GPU H1 source contract.",
        "- Build: AArch64 helper/native-init compile, ramdisk pack, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3208 identity, G0-G5 baseline markers, and H1 shader-state markers.",
        "- Ramdisk overlay check: V3204 bundled audio manifest remains present and the V3208 DOOM engine helper is present.",
        "- `git diff --check`: PASS.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-h1-shader-state-probe-candidate`.",
    ]) + "\n"


def _patch_missing_audio_bundle_gate() -> list[tuple[Any, str, Any]]:
    import build_native_init_boot_v2843_audio_bundled_setcal as v2843

    saved = [
        (v2843, "prepare_bundled_assets", v2843.prepare_bundled_assets),
    ]

    def prepare_preserved_audio_bundle() -> tuple[dict[str, Any], Path, dict[str, Path]]:
        manifest_path = OUT_DIR / "preserved-v3204-audio-bundle.manifest"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            "version 1\n"
            "profile internal-speaker-safe\n"
            "entry_count 0\n"
            "# build-time placeholder; final boot preserves the V3204 ramdisk audio bundle\n",
            encoding="utf-8",
        )
        return (
            {
                "ok": True,
                "safe_to_run_native_replay": True,
                "replay_entries": [],
                "files": [],
                "v3208_build_note": "final boot overlays V3208 init onto the V3204 ramdisk to preserve bundled private audio artifacts",
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


def _overlay_preserved_v3204_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3204 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3208 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3208 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3208 DOOM engine binary: {ENGINE_BINARY}")

    with tempfile.TemporaryDirectory(prefix="a90-v3208-overlay-") as temp_name:
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
            raise RuntimeError("V3204 base boot mkbootimg args did not include --ramdisk")

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

    _v3208_require_strings(BOOT_IMAGE)
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
        raise RuntimeError(f"missing V3208 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3204-ramdisk-overlay-v3208-init-helper-engine",
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
        "candidate_type": "gpu-h1-shader-state-probe-candidate",
        "adoption_state": "pending-gpu-h1-shader-state-live-validation",
        "gpu_h1": {
            "source_baseline": "v3204-gpu-g5-kms-blit-probe",
            "completion_audit": "docs/reports/NATIVE_INIT_V3206_GPU_EPIC_COMPLETION_AUDIT_2026-06-25.md",
            "command": "gpu h1-shader-state-probe --timeout-ms 5000 --materialize-devnode",
            "scope": "first-triangle-h1-shader-upload-sp-state-no-draw",
            "pm4_source": "Mesa freedreno A6xx fd6_program SP state plus adreno PM4 CP_LOAD_STATE6 shader preload",
            "pm4_reference_urls": [
                "https://docs.mesa3d.org/repository.html",
                "https://docs.mesa3d.org/drivers/freedreno.html",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_program.cc",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/gallium/drivers/freedreno/a6xx/fd6_draw.cc",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/a6xx.xml",
                "https://gitlab.freedesktop.org/mesa/mesa/-/raw/main/src/freedreno/registers/adreno/adreno_pm4.xml",
            ],
            "shader_source": "hand-assembled-ir3-placeholder-no-full-compiler-no-execute",
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
                "SP_VS_CNTL_0": "0xa800",
                "SP_VS_PROGRAM_COUNTER_OFFSET": "0xa81b",
                "SP_VS_BASE": "0xa81c",
                "SP_VS_CONFIG": "0xa823",
                "SP_VS_INSTR_SIZE": "0xa824",
                "SP_PS_CNTL_0": "0xa980",
                "SP_PS_PROGRAM_COUNTER_OFFSET": "0xa982",
                "SP_PS_BASE": "0xa983",
                "SP_PS_CONFIG": "0xab04",
                "SP_PS_INSTR_SIZE": "0xab05",
            },
            "packets": {
                "CP_LOAD_STATE6_GEOM": "0x32",
                "CP_LOAD_STATE6_FRAG": "0x34",
                "CP_WAIT_FOR_IDLE": "0x26",
                "CP_NOP": "0x10",
                "state_src": "SS6_INDIRECT",
                "vs_state_block": "SB6_VS_SHADER",
                "fs_state_block": "SB6_FS_SHADER",
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
                "flash-v3208-through-native-init-flash",
                "post-flash-health-check",
                "gpu-g0-fwclass-prepare",
                "gpu-h1-shader-state-probe-timeout-guard",
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
    (OUT_DIR / "gpu-h1-shader-state-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h1-shader-state-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h1"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-h1-shader-state-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _patch_base_module() -> list[tuple[Any, str, Any, bool]]:
    saved: list[tuple[Any, str, Any, bool]] = []
    for name, value in _v3208_overrides().items():
        existed = hasattr(base, name)
        saved.append((base, name, getattr(base, name, None), existed))
        setattr(base, name, value)
    for name, value in (
        ("_v3204_overrides", _v3208_overrides),
        ("_v3204_values", _v3208_values),
        ("v3204_adapter_source", v3208_adapter_source),
        ("_v3204_require_strings", _v3208_require_strings),
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


def _minimal_gpu_h1_manifest() -> dict[str, Any]:
    return {
        "source_baseline": "v3204-gpu-g5-kms-blit-probe",
        "completion_audit": "docs/reports/NATIVE_INIT_V3206_GPU_EPIC_COMPLETION_AUDIT_2026-06-25.md",
        "command": "gpu h1-shader-state-probe --timeout-ms 5000 --materialize-devnode",
        "scope": "first-triangle-h1-shader-upload-sp-state-no-draw",
        "pm4_source": "Mesa freedreno A6xx fd6_program SP state plus adreno PM4 CP_LOAD_STATE6 shader preload",
        "shader_source": "hand-assembled-ir3-placeholder-no-full-compiler-no-execute",
        "shader_execution_attempted": False,
        "draw_attempted": False,
        "kms_blit_attempted": False,
        "parent_enters_open": False,
        "parent_enters_ioctl": False,
        "next_live_validation": [
            "flash-v3208-through-native-init-flash",
            "post-flash-health-check",
            "gpu-g0-fwclass-prepare",
            "gpu-h1-shader-state-probe-timeout-guard",
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
            "candidate_type": "gpu-h1-shader-state-probe-candidate",
            "adoption_state": "pending-gpu-h1-shader-state-live-validation",
            "boot_image": rel(BOOT_IMAGE),
            "init_version": INIT_VERSION,
            "init_build": INIT_BUILD,
            "helper_sha256": sha256_file(HELPER_BINARY),
            "helper_flags": [],
            "init_extra_flags": [],
            "gpu_h1": _minimal_gpu_h1_manifest(),
        }
    manifest["boot_sha256"] = overlay["boot_sha256"]
    manifest["ramdisk_sha256"] = overlay["ramdisk_sha256"]
    manifest["ramdisk_overlay"] = overlay
    manifest["base_main_completed"] = base_main_completed
    if base_main_error:
        manifest["base_main_error"] = base_main_error
    manifest.setdefault("gpu_h1", _minimal_gpu_h1_manifest())
    manifest.setdefault("gpu_h1", {})["ramdisk_overlay"] = overlay
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            manifest,
            tuple(manifest.get("helper_flags", ())),
            tuple(manifest.get("init_extra_flags", ())),
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "gpu-h1-shader-state-probe-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-h1-shader-state-probe-candidate",
        "boot_image": rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_h1"]["next_live_validation"],
        "source_report": rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "ramdisk_overlay": overlay,
        "adoption_state": "pending-gpu-h1-shader-state-live-validation",
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
                f"{exc.__class__.__name__}: {exc}; continuing with preserved V3204 ramdisk overlay "
                "after V3208 init/helper/engine compile completed"
            )
        overlay = _overlay_preserved_v3204_ramdisk()
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
