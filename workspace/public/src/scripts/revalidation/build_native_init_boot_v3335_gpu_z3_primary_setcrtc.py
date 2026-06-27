#!/usr/bin/env python3
"""Build V3335 GPU Z3 primary SETCRTC imported scanout candidate."""

from __future__ import annotations

import json
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
import build_native_init_boot_v3334_gpu_z3_atomic_allow_modeset as previous

base = previous.base

CYCLE = "V3335"
INIT_VERSION = "0.11.103"
INIT_BUILD = "v3335-gpu-z3-primary-setcrtc"
BUILD_TAG = INIT_BUILD
DECISION = "v3335-gpu-z3-primary-setcrtc-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3335_GPU_Z3_PRIMARY_SETCRTC_SOURCE_BUILD_2026-06-27.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3335_gpu_z3_primary_setcrtc.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3335_gpu_z3_primary_setcrtc"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3335_gpu_z3_primary_setcrtc.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v622_gpu_z3_primary_setcrtc"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3335"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3335.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3335.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3335"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3335-gpu-z3-primary-setcrtc"

FRAME_PATH = "/tmp/a90-doomgeneric-v3335-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3335-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3335-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3335-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3335-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3335-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3335-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-z3-primary-setcrtc"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-z3-primary-setcrtc"

SFX_STREAM_MARKER = "a90.doomgeneric.v3335.audio=real-sfx-pcm-stream-gpu-z3-primary-setcrtc"
SOUND_MODE = "native-doom-sfx-gpu-z3-primary-setcrtc-v3335"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3335.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

Z3_COMMAND = "gpu z3-imported-scanout-primary-probe --timeout-ms 60000 --hold-ms 12000 --materialize-devnode"


def _rewrite_v3335_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3334", "a90-doomgeneric-v3335"),
        ("a90.doomgeneric.v3334", "a90.doomgeneric.v3335"),
        ("v3334", "v3335"),
        ("V3334", "V3335"),
        ("gpu-z3-atomic-allow-modeset", "gpu-z3-primary-setcrtc"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3335_bytes(item: bytes) -> bytes:
    return _rewrite_v3335_text(item.decode("utf-8")).encode("utf-8")


REQUIRED_STRINGS = tuple(_rewrite_v3335_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"z3-imported-scanout-primary-probe",
    b"gpu.z3.scanout.scope=gpu-z3-imported-scanout-primary-setcrtc",
    b"gpu.z3.scanout.target=panel-fullscreen-from-kms-mode",
    b"gpu.z3.scanout.present_mode=primary-setcrtc-fullscreen",
    b"gpu.z3.scanout.present_order=primary-setcrtc-then-restore-base-fb",
    b"gpu.z3.scanout.primary_setcrtc_attempted=1",
    b"gpu.z3.scanout.kms.base_fb_id=",
    b"restore_rc=",
    b"target_size=",
    b"z3-imported-scanout-primary-setcrtc-pass",
)


def _minimal_gpu_z3_manifest() -> dict[str, Any]:
    manifest = dict(previous._minimal_gpu_z3_manifest())
    manifest["baseline"] = "v3334-overlay-plane-atomic-allow-modeset-still-einval"
    manifest["redirect"] = "stop-overlay-variants-use-primary-setcrtc-fullscreen-scanout"
    manifest["primary_setcrtc_fix"] = "render-directly-into-fullscreen-kms-dumb-fb-and-setcrtc"
    manifest["command"] = Z3_COMMAND
    manifest["expected_result"] = "z3-imported-scanout-primary-setcrtc-pass"
    manifest["present_mode"] = "primary-setcrtc-fullscreen"
    manifest["pass_requirements"] = [
        "kms-dumb-fullscreen-create-map-prime-export",
        "kgsl-dmabuf-import-of-same-scanout-bo",
        "gpu-render-semantic-64-of-64",
        "primary-setcrtc-present-rc-0",
        "base-fb-restore-rc-0",
        "kms-copy-attempted-0",
        "post-probe-selftest-fail-0",
    ]
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    return "\n".join([
        "# Native Init V3335 GPU Z3 Primary SETCRTC Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{boot_image}`",
        f"- Boot SHA256: `{boot_sha}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        "",
        "## Change",
        "",
        "- Stops the overlay-plane variant loop and adds `gpu z3-imported-scanout-primary-probe`.",
        "- Creates a full-panel KMS dumb scanout framebuffer, exports it as PRIME, imports the same BO into KGSL, and renders the monitor graph directly into that scanout target.",
        "- Presents the imported framebuffer through the primary CRTC with `SETCRTC`, holds it for visual confirmation, then restores the previous base framebuffer before cleanup.",
        "- Makes the GPU 2D present sampler stride-aware so panel pitch padding is handled without a CPU copy.",
        "",
        "## Validation Contract",
        "",
        f"- Command: `{Z3_COMMAND}`",
        "- PASS requires full-panel KMS dumb create/map, PRIME export, KGSL import, GPU render semantic proof, `kms.present_rc=0`, `kms.restore_rc=0`, no KMS copy, positive hold, clean RMFB/dumb cleanup, and post-probe `selftest fail=0`.",
        "- No PMIC/GDSC/regulator/GPIO/backlight write, proprietary blob, EGL/GLES/OpenCL, forbidden partition, or raw flash path is introduced.",
        "",
        "## Static Validation",
        "",
        "- `py_compile`: V3335 builder and focused source test.",
        "- Unit tests: V3335 focused source contract plus Z3 regression contracts.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3335 identity plus primary SETCRTC telemetry.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `gpu-z3-primary-setcrtc-candidate`.",
    ]) + "\n"


def v3335_adapter_source() -> str:
    return _rewrite_v3335_text(previous.v3334_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-z3-primary-setcrtc-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-z3-primary-setcrtc-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_z3"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-z3-primary-setcrtc-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _overlay_preserved_v3335_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3335 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3335 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3335 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3335 DOOM engine binary: {ENGINE_BINARY}")

    removed_obsolete_engines = [
        "a90_doomgeneric_private_engine_v3204",
        "a90_doomgeneric_private_engine_v3208",
        "a90_doomgeneric_private_engine_v3210",
        "a90_doomgeneric_private_engine_v3303",
        "a90_doomgeneric_private_engine_v3310",
        "a90_doomgeneric_private_engine_v3311",
        "a90_doomgeneric_private_engine_v3312",
        "a90_doomgeneric_private_engine_v3313",
        "a90_doomgeneric_private_engine_v3314",
        "a90_doomgeneric_private_engine_v3315",
        "a90_doomgeneric_private_engine_v3317",
        "a90_doomgeneric_private_engine_v3318",
        "a90_doomgeneric_private_engine_v3319",
        "a90_doomgeneric_private_engine_v3320",
        "a90_doomgeneric_private_engine_v3321",
        "a90_doomgeneric_private_engine_v3325",
        "a90_doomgeneric_private_engine_v3326",
        "a90_doomgeneric_private_engine_v3327",
        "a90_doomgeneric_private_engine_v3328",
        "a90_doomgeneric_private_engine_v3329",
        "a90_doomgeneric_private_engine_v3330",
        "a90_doomgeneric_private_engine_v3331",
        "a90_doomgeneric_private_engine_v3332",
        "a90_doomgeneric_private_engine_v3333",
        "a90_doomgeneric_private_engine_v3334",
    ]

    with tempfile.TemporaryDirectory(prefix="a90-v3335-overlay-") as temp_name:
        temp_dir = Path(temp_name)
        unpack_dir = temp_dir / "unpack"
        ramdisk_dir = temp_dir / "ramdisk"
        unpack_dir.mkdir()
        ramdisk_dir.mkdir()

        unpack_args_text = base._run(
            [
                "python3",
                base.THIRD_PARTY_MKBOOTIMG / "unpack_bootimg.py",
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
        for old_engine in removed_obsolete_engines:
            (bin_dir / old_engine).unlink(missing_ok=True)
        engine_dest = bin_dir / ENGINE_RAMDISK_PATH.split("/", 1)[1]
        shutil.copy2(ENGINE_BINARY, engine_dest)
        engine_dest.chmod(0o755)

        base._set_reproducible_mtime(ramdisk_dir)

        if RAMDISK_CPIO.exists():
            RAMDISK_CPIO.unlink()
        RAMDISK_CPIO.parent.mkdir(parents=True, exist_ok=True)
        base._run(
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
            raise RuntimeError("V3335 base boot mkbootimg args did not include --ramdisk")

        if BOOT_IMAGE.exists():
            BOOT_IMAGE.unlink()
        base._run(
            [
                "python3",
                base.THIRD_PARTY_MKBOOTIMG / "mkbootimg.py",
                *mkboot_args,
                "--output",
                BOOT_IMAGE,
            ]
        )
        BOOT_IMAGE.chmod(0o600)

    image_size = BOOT_IMAGE.stat().st_size
    if image_size > BOOT_PARTITION_MAX_BYTES:
        raise RuntimeError(
            f"V3335 boot image too large for boot partition: "
            f"{image_size} > {BOOT_PARTITION_MAX_BYTES}"
        )

    base._v3210_require_strings(BOOT_IMAGE)
    listing = base._run(
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
        raise RuntimeError(f"missing V3335 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3334-ramdisk-overlay-v3335-init-helper-engine",
        "base_boot": base.rel(BASE_BOOT),
        "base_boot_sha256": base.sha256_file(BASE_BOOT),
        "boot_sha256": base.sha256_file(BOOT_IMAGE),
        "boot_image_size": image_size,
        "boot_partition_max_bytes": BOOT_PARTITION_MAX_BYTES,
        "ramdisk_cpio": base.rel(RAMDISK_CPIO),
        "ramdisk_sha256": base.sha256_file(RAMDISK_CPIO),
        "overlay_entries": [
            "init",
            "bin/a90_android_execns_probe",
            ENGINE_RAMDISK_PATH,
        ],
        "removed_obsolete_engines": [
            "bin/" + name for name in removed_obsolete_engines
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
            "candidate_type": "gpu-z3-primary-setcrtc-candidate",
            "adoption_state": "pending-gpu-z3-primary-setcrtc-live-validation",
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
    manifest["candidate_type"] = "gpu-z3-primary-setcrtc-candidate"
    manifest["adoption_state"] = "pending-gpu-z3-primary-setcrtc-live-validation"
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
    for key in ("gpu_d3", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2"):
        manifest.pop(key, None)
    manifest["gpu_z3"] = _minimal_gpu_z3_manifest()
    manifest["gpu_z3"]["ramdisk_overlay"] = overlay
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
    for key in ("gpu_d3", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2"):
        manifest.pop(key, None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-z3-primary-setcrtc-candidate",
        "adoption_state": "pending-gpu-z3-primary-setcrtc-live-validation",
        "gpu_z3": _minimal_gpu_z3_manifest(),
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


def _apply_v3335_overrides() -> None:
    previous._apply_v3334_overrides()
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
        "SFX_STREAM_MARKER": SFX_STREAM_MARKER,
        "SOUND_MODE": SOUND_MODE,
        "AUDIO_CORUN_MODE": SOUND_MODE,
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3335_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3335_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3335_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3335_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
