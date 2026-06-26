#!/usr/bin/env python3
"""Build V3321 GPU M3 visual hold timeout-budget fix."""

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
import build_native_init_boot_v3320_gpu_m3_monitor_extraction as previous

base = previous.base

CYCLE = "V3321"
INIT_VERSION = "0.11.92"
INIT_BUILD = "v3321-gpu-m3-hold-timeout-budget"
BUILD_TAG = INIT_BUILD
DECISION = "v3321-gpu-m3-hold-timeout-budget-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3321_GPU_M3_HOLD_TIMEOUT_BUDGET_SOURCE_BUILD_2026-06-27.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3321_gpu_m3_hold_timeout_budget.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3321_gpu_m3_hold_timeout_budget"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3321_gpu_m3_hold_timeout_budget.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v613_gpu_m3_hold_timeout_budget"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3321"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3321.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3321.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3321"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3321-gpu-m3-hold-timeout-budget"

FRAME_PATH = "/tmp/a90-doomgeneric-v3321-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3321-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3321-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3321-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3321-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3321-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3321-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-gpu-m3-hold-timeout-budget"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-gpu-m3-hold-timeout-budget"

SFX_STREAM_MARKER = "a90.doomgeneric.v3321.audio=real-sfx-pcm-stream-gpu-m3-hold-timeout-budget"
SOUND_MODE = "native-doom-sfx-gpu-m3-hold-timeout-budget-v3321"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3321.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SCOPE = "gpu-m3-shared-kgsl-2d-present-extraction"
M3_COMMAND = "gpu m3-monitor-extraction-probe --frames 12 --interval-ms 200 --timeout-ms 60000 --hold-ms 60000 --materialize-devnode"
M3_NODE_ENUM_BASELINE = "v3316-gpu-m0-system-monitor-node-enum-pass"
M3_SAMPLER_BASELINE = "v3317-gpu-m0-monitor-sampler-live-pass"
M3_DASHBOARD_BASELINE = "v3318-gpu-m1-monitor-dashboard-live-pass"
M3_LIVE_GRAPH_BASELINE = "v3319-gpu-m2-monitor-live-graphs-live-pass"
M3_EXTRACTION_BASELINE = "v3320-gpu-m3-monitor-extraction-telemetry-pass"


def _rewrite_v3321_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3320", "a90-doomgeneric-v3321"),
        ("a90.doomgeneric.v3320", "a90.doomgeneric.v3321"),
        ("v3320", "v3321"),
        ("V3320", "V3321"),
        ("gpu-m3-monitor-extraction", "gpu-m3-hold-timeout-budget"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3321_bytes(item: bytes) -> bytes:
    return _rewrite_v3321_text(item.decode("utf-8")).encode("utf-8")


GPU_M3_MONITOR_MARKERS = (
    b"m3-monitor-extraction-probe",
    b"monitor-extraction-probe",
    b"gpu.m3.extract.scope=",
    b"gpu.m3.extract.layer=gpu_2d_present_v1",
    b"gpu.m3.extract.shared_core=bo-map,sync-to-gpu,submit-wait,linear-readback,kms-copy",
    b"gpu.m3.extract.live_consumer=m2-monitor-live-graph-probe",
    b"gpu.m3.extract.regression_consumers=d3-video-texture-present-probe,m2-monitor-live-graph-probe",
    b"gpu.m3.extract.kgsl_submit_attempted=1",
    b"gpu.m3.extract.kms_present_attempted=1",
    b"gpu.m3.extract.power_write_attempted=0",
    b"gpu.m3.extract.proprietary_blob_attempted=0",
    b"gpu.m3.extract.delegate_rc=%d",
    b"gpu.m3.extract.result=%s",
    b"shared-2d-present-monitor-pass",
    b"m2-monitor-live-graph-probe",
    b"monitor-live-graph-probe",
    b"gpu.d3.video.extraction_layer=gpu_2d_present_v1",
    b"gpu.m2.graph.extraction_layer=gpu_2d_present_v1",
    b"gpu.m2.graph.pipeline=shared-kgsl-2d-present-v1",
    b"gpu.m2.graph.parent_timeout_ms=%d",
    b"gpu.m2.graph.timeout_split=render-plus-visual-hold",
    b"gpu.m2.graph.scope=",
    b"gpu.m2.graph.texture_source=live-monitor-mono1-graph-cpu-gpu-mem-temp",
    b"gpu.m2.graph.blit_mode=kgsl-textured-quad-scale-to-960x720-linear-readback-kms-copy",
    b"gpu.m2.graph.power_write_attempted=0",
    b"gpu.m2.graph.proprietary_blob_attempted=0",
    b"gpu.m2.graph.kgsl_submit_attempted=1",
    b"gpu.m2.graph.kms_present_attempted=1",
    b"gpu.m2.graph.graph_pixels_set=%u",
    b"gpu.m2.graph.cpu.count=%u",
    b"gpu.m2.graph.cluster.count=%u",
    b"gpu.m2.graph.present_rc=%d",
    b"gpu.m2.graph.semantic.match_count=%u",
    b"gpu.m2.graph.result=%s",
    b"monitor-live-graph-pass",
    b"SHARED KGSL 2D PRESENT",
)

REQUIRED_STRINGS = tuple(
    _rewrite_v3321_bytes(item)
    for item in previous.REQUIRED_STRINGS
    if b"gpu.m1.monitor" not in item
    and b"m1-monitor" not in item
    and b"monitor-dashboard" not in item
) + (
    SFX_STREAM_MARKER.encode("ascii"),
    SOUND_MODE.encode("ascii"),
    AUDIO_PCM_STREAM_PATH.encode("ascii"),
    INIT_VERSION.encode("ascii"),
    INIT_BUILD.encode("ascii"),
) + GPU_M3_MONITOR_MARKERS


def _minimal_gpu_m3_manifest() -> dict[str, Any]:
    return {
        "source_baseline": [
            M3_NODE_ENUM_BASELINE,
            M3_SAMPLER_BASELINE,
            M3_DASHBOARD_BASELINE,
            M3_LIVE_GRAPH_BASELINE,
            M3_EXTRACTION_BASELINE,
        ],
        "scope": SCOPE,
        "command": M3_COMMAND,
        "candidate_type": "gpu-m3-hold-timeout-budget-candidate",
        "data_sources": [
            "/sys/devices/system/cpu/cpu*/topology",
            "/sys/devices/system/cpu/cpu*/cpufreq",
            "/proc/stat",
            "/proc/meminfo",
            "/proc/loadavg",
            "/sys/class/kgsl/kgsl-3d0",
            "/sys/class/thermal",
            "/sys/class/power_supply/battery",
        ],
        "cluster_detect_source": "cpufreq/related_cpus plus cpuinfo/scaling max frequency",
        "history_capacity": 16,
        "default_frames": 12,
        "default_interval_ms": 200,
        "default_hold_ms": 60000,
        "default_timeout_ms": 60000,
        "expected_result": "shared-2d-present-monitor-pass",
        "power_write_attempted": False,
        "kgsl_submit_attempted": True,
        "kms_present_attempted": True,
        "proprietary_blob_attempted": False,
        "next_live_validation": [
            "flash-v3321-through-native-init-flash",
            "post-flash-health-check",
            "gpu-m3-hold-timeout-budget-60s-hold-probe",
            "require-shared-2d-present-monitor-pass",
            "require-extraction-layer-gpu_2d_present_v1",
            "require-render-plus-visual-hold-timeout-split",
            "require-parent-timeout-125000",
            "require-hold-ms-60000",
            "require-not-timed-out",
            "require-m2-delegate-monitor-live-graph-pass",
            "require-presented-frames-12",
            "require-graph-pixels-positive",
            "require-kgsl-submit-attempted",
            "require-cpu-count-8",
            "require-cluster-count-3",
            "require-kms-present-rc-0",
            "require-semantic-match-count-64",
            "require-d3-regression-video-texture-present-pass",
            "post-probe-selftest",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    return "\n".join([
        "# Native Init V3321 GPU M3 Hold Timeout Budget Source Build",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Track: GPU rung 3, M3 visual hold timeout-budget fix.",
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
        "- Keeps the V3320 `gpu_2d_present_v1` extraction intact.",
        "- Splits the M2/M3 monitor parent watchdog into render timeout plus visual hold budget plus a 5 s margin.",
        "- Adds `gpu.m2.graph.parent_timeout_ms` and `gpu.m2.graph.timeout_split=render-plus-visual-hold` telemetry so a 60 s visual hold no longer races the 60 s render timeout.",
        "",
        "## M3 Hold Gate",
        "",
        f"- Command: `{M3_COMMAND}`",
        "- PASS requires `gpu.m3.extract.result=shared-2d-present-monitor-pass`, `gpu.m3.extract.layer=gpu_2d_present_v1`, M2 delegate live graph pass, `parent_timeout_ms=125000`, 12 presented frames, semantic match count 64, `present_rc=0`, no timeout for a 60 s hold, and `selftest fail=0` after the probe.",
        "- The user visually confirmed the D3 Bad Apple path as visible with normal-looking frames before the V3320 extraction unit.",
        "- This is a real KGSL submit path (`kgsl_submit_attempted=1`) plus KMS present, with no power/sysfs writes.",
        "",
        "## Safety",
        "",
        "- Monitor telemetry sources are read-only `/proc` and `/sys` reads.",
        "- Live KGSL validation may use the existing G0 firmware-cache/devnode materialization path; no power/display sysfs write is part of M3.",
        "- No backlight/PWM/PMIC/regulator/GDSC/GPIO write, panel re-init, proprietary blob, Wi-Fi connect, DHCP, or ping.",
        "- Boot partition only through `native_init_flash.py` in the live step.",
        "",
        "## Validation",
        "",
        "- `py_compile`: V3321 builder and focused source test.",
        "- `unittest`: V3321 M3 source/dispatch/builder contract.",
        "- Compile: focused AArch64 native-init compile with existing baseline warnings only.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3321 identity plus M3 extraction telemetry, M2 delegate telemetry, timeout split telemetry, and shared 2D present labels.",
        "- Size gate: final boot image must be `<= 67108864` bytes before any flash attempt.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        f"- Node enum baseline: `{M3_NODE_ENUM_BASELINE}`",
        f"- M0 sampler baseline: `{M3_SAMPLER_BASELINE}`",
        f"- M1 dashboard baseline: `{M3_DASHBOARD_BASELINE}`",
        f"- M2 live graph baseline: `{M3_LIVE_GRAPH_BASELINE}`",
        f"- M3 extraction baseline: `{M3_EXTRACTION_BASELINE}`",
        "- Candidate type: `gpu-m3-hold-timeout-budget-candidate`.",
    ]) + "\n"


def v3321_adapter_source() -> str:
    return _rewrite_v3321_text(previous.v3320_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "gpu-m3-hold-timeout-budget-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-m3-hold-timeout-budget-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["gpu_m3"]["next_live_validation"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-gpu-m3-hold-timeout-budget-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _overlay_preserved_v3321_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3321 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3321 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3321 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3321 DOOM engine binary: {ENGINE_BINARY}")

    with tempfile.TemporaryDirectory(prefix="a90-v3321-overlay-") as temp_name:
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
        for old_engine in (
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
        ):
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
            raise RuntimeError("V3321 base boot mkbootimg args did not include --ramdisk")

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
            f"V3321 boot image too large for boot partition: "
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
        raise RuntimeError(f"missing V3321 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3320-ramdisk-overlay-v3321-init-helper-engine",
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
            "bin/a90_doomgeneric_private_engine_v3204",
            "bin/a90_doomgeneric_private_engine_v3208",
            "bin/a90_doomgeneric_private_engine_v3210",
            "bin/a90_doomgeneric_private_engine_v3303",
            "bin/a90_doomgeneric_private_engine_v3310",
            "bin/a90_doomgeneric_private_engine_v3311",
            "bin/a90_doomgeneric_private_engine_v3312",
            "bin/a90_doomgeneric_private_engine_v3313",
            "bin/a90_doomgeneric_private_engine_v3314",
            "bin/a90_doomgeneric_private_engine_v3315",
            "bin/a90_doomgeneric_private_engine_v3317",
            "bin/a90_doomgeneric_private_engine_v3318",
            "bin/a90_doomgeneric_private_engine_v3319",
            "bin/a90_doomgeneric_private_engine_v3320",
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
            "candidate_type": "gpu-m3-hold-timeout-budget-candidate",
            "adoption_state": "pending-gpu-m3-hold-timeout-budget-live-validation",
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
    manifest["candidate_type"] = "gpu-m3-hold-timeout-budget-candidate"
    manifest["adoption_state"] = "pending-gpu-m3-hold-timeout-budget-live-validation"
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
    manifest.pop("gpu_d3", None)
    manifest.pop("gpu_m0", None)
    manifest.pop("gpu_m1", None)
    manifest.pop("gpu_m2", None)
    manifest["gpu_m3"] = _minimal_gpu_m3_manifest()
    manifest["gpu_m3"]["ramdisk_overlay"] = overlay
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
    manifest.pop("gpu_d3", None)
    manifest.pop("gpu_m0", None)
    manifest.pop("gpu_m1", None)
    manifest.pop("gpu_m2", None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "gpu-m3-hold-timeout-budget-candidate",
        "adoption_state": "pending-gpu-m3-hold-timeout-budget-live-validation",
        "gpu_m3": _minimal_gpu_m3_manifest(),
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


def _apply_v3321_overrides() -> None:
    previous._apply_v3320_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3321_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3321_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3321_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3321_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
