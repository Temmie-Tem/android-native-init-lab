#!/usr/bin/env python3
"""Build V3384 native-init boot image for the server-distro hardware-contract surface."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3383_server_distro_handoff_cleanup as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3383_text
ORIG_PREVIOUS_REWRITE_BYTES = previous._rewrite_v3383_bytes
ORIG_PREVIOUS_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3383

CYCLE = "V3384"
INIT_VERSION = "0.11.140"
INIT_BUILD = "v3384-server-distro-hardware-contract"
BUILD_TAG = INIT_BUILD
DECISION = "v3384-server-distro-stage0-hardware-contract-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3384_SERVER_DISTRO_HARDWARE_CONTRACT_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3384_server_distro_hardware_contract.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3384_server_distro_hardware_contract"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3384_server_distro_hardware_contract.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v632_server_distro_hardware_contract"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3384"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3384.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3384.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3384"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3384-server-distro-hardware-contract"

FRAME_PATH = "/tmp/a90-doomgeneric-v3384-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3384-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3384-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3384-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3384-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3384-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3384-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3384.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3384_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3383-server-distro-handoff-cleanup", INIT_BUILD),
        ("server-distro-handoff-cleanup", "server-distro-hardware-contract"),
        ("server-distro-d4d-handoff-cleanup", "server-distro-stage0-hardware-contract"),
        ("d4d-handoff-cleanup", "stage0-hardware-contract"),
        ("handoff-cleanup", "hardware-contract"),
        ("0.11.139", INIT_VERSION),
        ("V3383", CYCLE),
        ("v3383", "v3384"),
        ("a90-doomgeneric-v3383", "a90-doomgeneric-v3384"),
        ("a90.doomgeneric.v3383", "a90.doomgeneric.v3384"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3384_bytes(item: bytes) -> bytes:
    return _rewrite_v3384_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3384_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3384_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3384_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3384_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3384_bytes(marker) for marker in ORIG_PREVIOUS_REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.140",
    b"v3384-server-distro-hardware-contract",
    b"server-distro [status|hardware-contract]",
    b"A90DHW contract.version=1",
    b"SERVER_DISTRO_STAGE0_HARDWARE_CONTRACT_2026-07-04.md",
    b"default.active=boot-control,usb-acm-ncm,storage-rootfs-handoff,drm-kms-boot-hud-release,health-status",
    b"default.drm_kms=optional-boot-hud release_rule=stop-autohud-and-native-init-drm-owners-before-switch_root",
    b"next.required=wifi-sta-upstream",
    b"next.wifi_sta=native-wlan0-materialization,debian-ip-route-tunnel",
    b"optin=audio-adsp-acdb,kgsl-gpu,video-doom,touch-game-input,stress-longsoak",
    b"denied.default_off=modem-cellular,camera,gnss,nfc,bluetooth,sensor-hubs,android-hal-services",
    b"public_tunnel.owner=debian native=off inbound_public_ports=0",
    b"safety.no=forbidden-partitions,raw-nonboot-flash,pmic-regulator-gdsc-gpio-backlight,panel-reinit",
)


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "server-distro-stage0-hardware-contract"
    manifest["scope"] = "read-only-stage0-hardware-contract-command-surface"
    manifest["server_distro_hardware_contract"] = {
        "command": "server-distro [status|hardware-contract]",
        "prefix": "A90DHW",
        "flags": "CMD_NONE",
        "default_active": [
            "boot-control",
            "usb-acm-ncm",
            "storage-rootfs-handoff",
            "drm-kms-boot-hud-release",
            "health-status",
        ],
        "next_required": "wifi-sta-upstream",
        "opt_in": ["audio", "kgsl-gpu", "video-doom", "input", "stress"],
        "default_off": [
            "modem-cellular",
            "camera",
            "gnss",
            "nfc",
            "bluetooth",
            "sensor-hubs",
            "android-hal-services",
        ],
    }
    return manifest


def render_report(
    manifest: dict[str, Any],
    helper_flags: tuple[str, ...],
    init_extra_flags: tuple[str, ...],
) -> str:
    boot_image = manifest.get("boot_image", base.rel(BOOT_IMAGE))
    boot_sha = manifest.get("boot_sha256", "")
    helper_sha = manifest.get("helper_sha256", "")
    return "\n".join([
        "# Native Init V3384 Server-Distro Hardware Contract Source Build",
        "",
        f"- Cycle: `{CYCLE}`",
        f"- Decision: `{DECISION}`",
        f"- Init: `A90 Linux init {INIT_VERSION} ({INIT_BUILD})`",
        f"- Boot image: `{boot_image}`",
        f"- Boot SHA256: `{boot_sha}`",
        f"- Helper SHA256: `{helper_sha}`",
        f"- Base boot: `{base.rel(BASE_BOOT)}`",
        "",
        "## Change",
        "",
        "- Carries forward the V3383 D4 userdata appliance handoff cleanup surface.",
        "- Adds a read-only `server-distro [status|hardware-contract]` command surface.",
        "- The command prints the Stage0 hardware contract under the `A90DHW` prefix: default active surfaces, the Wi-Fi STA next rung, opt-in demo hardware, default-off hardware, tunnel ownership, and safety no-go lines.",
        "- This is source/build only; live validation is a separate checked-helper flash gate.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_server_distro_hardware_contract`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3384_server_distro_hardware_contract`.",
        "- No device action was performed in this source unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `server-distro-stage0-hardware-contract`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "server-distro-hardware-contract.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-stage0-hardware-contract",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "hardware_contract": {
            "command": "server-distro [status|hardware-contract]",
            "prefix": "A90DHW",
            "live_gate": "flash checked helper, run server-distro hardware-contract, verify A90DHW lines",
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3384(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "server-distro-stage0-hardware-contract",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3383_module_for_v3384() -> None:
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
        "SFX_BACKEND_SOURCE": SFX_BACKEND_SOURCE,
        "SDL_MIXER_STUB": SDL_MIXER_STUB,
        "REQUIRED_STRINGS": REQUIRED_STRINGS,
        "SOFTAP_COMMANDS": SOFTAP_COMMANDS,
        "render_report": render_report,
        "_rewrite_v3383_text": _rewrite_v3384_text,
        "_rewrite_v3383_bytes": _rewrite_v3384_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3383": _normalize_manifest_for_v3384,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3383_module_for_v3384()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
