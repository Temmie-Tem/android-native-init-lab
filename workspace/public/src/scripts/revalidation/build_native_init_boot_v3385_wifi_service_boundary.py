#!/usr/bin/env python3
"""Build V3385 native-init boot image with the native-owned Wi-Fi service boundary."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3339_softap_s2_status_plan as v3339_overlay
import build_native_init_boot_v3384_server_distro_hardware_contract as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3384_text
ORIG_PREVIOUS_REWRITE_BYTES = previous._rewrite_v3384_bytes
ORIG_PREVIOUS_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3384
ORIG_V3339_OBSOLETE_ENGINE_NAMES = v3339_overlay.OBSOLETE_ENGINE_NAMES

CYCLE = "V3385"
INIT_VERSION = "0.11.141"
INIT_BUILD = "v3385-wifi-service-boundary"
BUILD_TAG = INIT_BUILD
DECISION = "v3385-wifi-service-boundary-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3385_WIFI_SERVICE_BOUNDARY_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3385_wifi_service_boundary.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3385_wifi_service_boundary"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3385_wifi_service_boundary.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v632_wifi_service_boundary"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3385"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3385.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3385.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3385"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3385-wifi-service-boundary"

FRAME_PATH = "/tmp/a90-doomgeneric-v3385-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3385-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3385-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3385-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3385-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3385-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3385-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3385.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3385_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3384-server-distro-hardware-contract", INIT_BUILD),
        ("server-distro-hardware-contract", "wifi-service-boundary"),
        ("server-distro-stage0-hardware-contract", "wifi-service-boundary"),
        ("stage0-hardware-contract", "wifi-service-boundary"),
        ("0.11.140", INIT_VERSION),
        ("V3384", CYCLE),
        ("v3384", "v3385"),
        ("a90-doomgeneric-v3384", "a90-doomgeneric-v3385"),
        ("a90.doomgeneric.v3384", "a90.doomgeneric.v3385"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3385_bytes(item: bytes) -> bytes:
    return _rewrite_v3385_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3385_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3385_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3385_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3385_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3385_bytes(marker) for marker in ORIG_PREVIOUS_REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.141",
    b"v3385-wifi-service-boundary",
    b"a90-native-wifi-service-v1",
    b"wifi service [status|start|stop|once]",
    b"wifi-service-start-pass",
    b"wifi-service-once-pass",
    b"wifi-service-status-running",
    b"owner=native-init",
    b"raw_results_redacted=1",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *ORIG_V3339_OBSOLETE_ENGINE_NAMES,
    "a90_doomgeneric_private_engine_v3384",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "wifi-service-boundary"
    manifest["scope"] = "native-owned-wifi-file-request-response-service"
    manifest["wifi_service_boundary"] = {
        "command": "wifi service [status|start|stop|once] <dir>",
        "version": "a90-native-wifi-service-v1",
        "request_file": "request",
        "response_file": "response",
        "supported_ops": ["status", "scan"],
        "denied_in_this_rung": ["connect", "dhcp", "ping", "public-tunnel"],
        "owner": "native-init",
        "obsolete_ramdisk_engines": ["bin/" + name for name in OBSOLETE_RAMDISK_ENGINES],
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
        "# Native Init V3385 Wi-Fi Service Boundary Source Build",
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
        "- Carries forward the V3384 server-distro hardware contract surface.",
        "- Adds a native-owned `wifi service [status|start|stop|once] <dir>` command surface.",
        "- The service watches a shared request file and writes a redacted response file so a Debian chroot can request native-owned `status` and `scan` without taking raw WLAN ownership.",
        "- This rung intentionally excludes connect, DHCP, ping, DNS, API probing, and public tunnel exposure.",
        "- This is source/build only; live validation is a separate checked-helper flash gate.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_native_wifi_service_boundary_source`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3385_wifi_service_boundary`.",
        "- No device action was performed in this source unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `wifi-service-boundary`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "wifi-service-boundary.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-service-boundary",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "wifi_service_boundary": {
            "command": "wifi service [status|start|stop|once] <dir>",
            "request_file": "request",
            "response_file": "response",
            "live_gate": "flash checked helper, start service inside chroot-visible dir, write request from Debian SSH, verify native response",
            "obsolete_ramdisk_engines": ["bin/" + name for name in OBSOLETE_RAMDISK_ENGINES],
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3385(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-service-boundary",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3384_module_for_v3385() -> None:
    v3339_overlay.OBSOLETE_ENGINE_NAMES = OBSOLETE_RAMDISK_ENGINES
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
        "_rewrite_v3384_text": _rewrite_v3385_text,
        "_rewrite_v3384_bytes": _rewrite_v3385_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3384": _normalize_manifest_for_v3385,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3384_module_for_v3385()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
