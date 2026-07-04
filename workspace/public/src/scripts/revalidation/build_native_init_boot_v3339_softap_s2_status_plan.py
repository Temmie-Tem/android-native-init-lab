#!/usr/bin/env python3
"""Build V3339 native-init SoftAP S2 status/plan candidate."""

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
import build_native_init_boot_v3335_gpu_z3_primary_setcrtc as previous

base = previous.base

CYCLE = "V3339"
INIT_VERSION = "0.11.104"
INIT_BUILD = "v3339-softap-s2-status-plan"
BUILD_TAG = INIT_BUILD
DECISION = "v3339-softap-s2-status-plan-source-build-pass"
BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024
OBSOLETE_ENGINE_NAMES = (
    "a90_doomgeneric_private_engine_v3334",
    "a90_doomgeneric_private_engine_v3335",
)

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3339_SOFTAP_S2_STATUS_PLAN_SOURCE_BUILD_2026-06-27.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3339_softap_s2_status_plan.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3339_softap_s2_status_plan"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3339_softap_s2_status_plan.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v623_softap_s2_status_plan"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3339"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3339.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3339.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3339"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3339-softap-s2-status-plan"

FRAME_PATH = "/tmp/a90-doomgeneric-v3339-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3339-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3339-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3339-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3339-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3339-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3339-sfx.pcmstream"

FRAME_SCALE = "1:1-demo-hud-large-groups-softap-s2-status-plan"
FRAME_IPC = "shared-mmap-direct-blit-demo-hud-large-groups-softap-s2-status-plan"

SFX_STREAM_MARKER = "a90.doomgeneric.v3339.audio=real-sfx-pcm-stream-softap-s2-status-plan"
SOUND_MODE = "native-doom-sfx-softap-s2-status-plan-v3339"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3339.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SOFTAP_COMMANDS = (
    "wifi softap status",
    "wifi softap plan",
    "wifi softap prepare",
)


def _rewrite_v3339_text(text: str) -> str:
    replacements = (
        (previous.INIT_VERSION, INIT_VERSION),
        (previous.INIT_BUILD, INIT_BUILD),
        (previous.ENGINE_NAME, ENGINE_NAME),
        (previous.ENGINE_REMOTE_PATH, ENGINE_REMOTE_PATH),
        (previous.SOUND_MODE, SOUND_MODE),
        (previous.SFX_STREAM_MARKER, SFX_STREAM_MARKER),
        (previous.AUDIO_PCM_STREAM_PATH, AUDIO_PCM_STREAM_PATH),
        ("a90-doomgeneric-v3335", "a90-doomgeneric-v3339"),
        ("a90.doomgeneric.v3335", "a90.doomgeneric.v3339"),
        ("v3335", "v3339"),
        ("V3335", "V3339"),
        ("gpu-z3-primary-setcrtc", "softap-s2-status-plan"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3339_bytes(item: bytes) -> bytes:
    return _rewrite_v3339_text(item.decode("utf-8")).encode("utf-8")


REQUIRED_STRINGS = tuple(_rewrite_v3339_bytes(item) for item in previous.REQUIRED_STRINGS) + (
    b"a90-native-wifi-softap-v1",
    b"/cache/a90-softap",
    b"wifi softap [status|plan|prepare [profile]|cleanup]",
    b"softap-status-blocked-wlan-gate",
    b"softap-prepare-blocked-wlan-gate",
    b"scope=read-only-status-plan-no-ap-start",
    b"hostapd_start_attempted=0",
    b"dhcp_server_start_attempted=0",
    b"listener_start_attempted=0",
    b"server_exposure_attempted=0",
    b"start_allowed=0",
)


def _softap_manifest() -> dict[str, Any]:
    return {
        "rung": "S2",
        "scope": "softap-status-plan-prepare-no-start",
        "commands": list(SOFTAP_COMMANDS),
        "expected_current_decisions": [
            "softap-status-blocked-wlan-gate",
            "softap-prepare-blocked-wlan-gate",
        ],
        "hard_no_start_fields": [
            "config_write_attempted=0",
            "hostapd_start_attempted=0",
            "dhcp_server_start_attempted=0",
            "listener_start_attempted=0",
            "interface_mode_change_attempted=0",
            "address_assign_attempted=0",
            "server_exposure_attempted=0",
            "start_supported=0",
            "start_allowed=0",
            "ssid_psk_logged=0",
        ],
        "pass_requirements": [
            "version-0.11.104",
            "post-flash-selftest-fail-0",
            "wifi-softap-status-rc-0",
            "wifi-softap-plan-rc-0",
            "wifi-softap-prepare-rc-0",
            "start-allowed-0",
            "all-ap-server-mutation-attempted-fields-0",
            "no-wifi-scan-connect-dhcp-ping",
            "no-hostapd-ap-mode-listener-start",
        ],
    }


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    return "\n".join([
        "# Native Init V3339 SoftAP S2 Status/Plan Source Build",
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
        "- Builds the V3338 `wifi softap` status/plan/prepare/cleanup source surface into a flashable candidate.",
        "- Keeps SoftAP S2 below AP bring-up: no config write, no hostapd start, no DHCP-server start, no listener exposure, no interface mode change, no address assignment.",
        "- Expected live result on the current S1 inventory is a clean no-go report: `start_allowed=0` and `softap-prepare-blocked-wlan-gate`.",
        "",
        "## Validation Contract",
        "",
        "- Commands: `wifi softap status`, `wifi softap plan`, `wifi softap prepare`.",
        "- PASS requires command rc=0, explicit no-start fields all `0`, `start_allowed=0`, no scan/connect/DHCP/ping, no AP daemon/listener start, and post-flash `selftest fail=0`.",
        "- No PMIC/GDSC/regulator/GPIO/backlight write, forbidden partition, raw flash path, credential logging, AP mode, or server exposure is introduced.",
        "",
        "## Static Validation",
        "",
        "- `py_compile`: V3339 builder and focused source test.",
        "- Unit tests: V3339 focused source/build contract.",
        "- Build: AArch64 helper/native-init compile, preserved-ramdisk overlay, boot image pack, SHA256 capture.",
        "- Marker check: generated boot image contains V3339 identity and SoftAP no-start status markers.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `softap-s2-status-plan-candidate`.",
    ]) + "\n"


def v3339_adapter_source() -> str:
    return _rewrite_v3339_text(previous.v3335_adapter_source())


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "softap-s2-status-plan-candidate.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "softap-s2-status-plan-candidate",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "live_validation_focus": manifest["softap_s2"]["pass_requirements"],
        "source_report": base.rel(REPORT_PATH),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "adoption_state": "pending-softap-s2-live-validation",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _overlay_preserved_v3339_ramdisk() -> dict[str, Any]:
    if not BASE_BOOT.exists():
        raise FileNotFoundError(f"missing V3339 base boot: {BASE_BOOT}")
    if not INIT_BINARY.exists():
        raise FileNotFoundError(f"missing V3339 init binary: {INIT_BINARY}")
    if not HELPER_BINARY.exists():
        raise FileNotFoundError(f"missing V3339 helper binary: {HELPER_BINARY}")
    if not ENGINE_BINARY.exists():
        raise FileNotFoundError(f"missing V3339 DOOM engine binary: {ENGINE_BINARY}")

    with tempfile.TemporaryDirectory(prefix="a90-v3339-overlay-") as temp_name:
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
        for old_engine in OBSOLETE_ENGINE_NAMES:
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
            raise RuntimeError("V3339 base boot mkbootimg args did not include --ramdisk")

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
            f"V3339 boot image too large for boot partition: "
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
        raise RuntimeError(f"missing V3339 overlay ramdisk entries: {missing_entries}")

    return {
        "mode": "preserve-v3335-ramdisk-overlay-v3339-init-helper-engine",
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
            "bin/" + name for name in OBSOLETE_ENGINE_NAMES
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
            "candidate_type": "softap-s2-status-plan-candidate",
            "adoption_state": "pending-softap-s2-live-validation",
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
    manifest["candidate_type"] = "softap-s2-status-plan-candidate"
    manifest["adoption_state"] = "pending-softap-s2-live-validation"
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
    for key in ("gpu_d3", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2", "gpu_z3"):
        manifest.pop(key, None)
    manifest["softap_s2"] = _softap_manifest()
    manifest["softap_s2"]["ramdisk_overlay"] = overlay
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
    for key in ("gpu_d3", "gpu_m0", "gpu_m1", "gpu_m2", "gpu_m3", "gpu_z2", "gpu_z3"):
        manifest.pop(key, None)
    manifest.update({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "softap-s2-status-plan-candidate",
        "adoption_state": "pending-softap-s2-live-validation",
        "softap_s2": _softap_manifest(),
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


def _apply_v3339_overrides() -> None:
    previous._apply_v3335_overrides()
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
        "SFX_BACKEND_SOURCE_TEXT": _rewrite_v3339_text(base.SFX_BACKEND_SOURCE_TEXT),
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "render_report": render_report,
        "v3210_adapter_source": v3339_adapter_source,
        "_overlay_preserved_v3208_ramdisk": _overlay_preserved_v3339_ramdisk,
        "_postprocess_manifest": _postprocess_manifest,
        "_finalize_manifest_after_overlay": _finalize_manifest_after_overlay,
    }
    for name, value in replacements.items():
        setattr(base, name, value)


def main() -> int:
    _apply_v3339_overrides()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
