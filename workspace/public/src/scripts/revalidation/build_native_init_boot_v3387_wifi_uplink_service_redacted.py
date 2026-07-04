#!/usr/bin/env python3
"""Build V3387 native-init boot image with redacted Wi-Fi uplink-service responses."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3386_wifi_uplink_service_boundary as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3386_text
ORIG_PREVIOUS_REWRITE_BYTES = previous._rewrite_v3386_bytes
ORIG_PREVIOUS_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3386

CYCLE = "V3387"
INIT_VERSION = "0.11.143"
INIT_BUILD = "v3387-wifi-uplink-service-redacted"
BUILD_TAG = INIT_BUILD
DECISION = "v3387-wifi-uplink-service-redacted-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3387_WIFI_UPLINK_SERVICE_REDACTED_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3387_wifi_uplink_service_redacted.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3387_wifi_uplink_service_redacted"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3387_wifi_uplink_service_redacted.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v634_wifi_uplink_service_redacted"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3387"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3387.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3387.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3387"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3387-wifi-uplink-service-redacted"

FRAME_PATH = "/tmp/a90-doomgeneric-v3387-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3387-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3387-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3387-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3387-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3387-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3387-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3387.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3387_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3386-wifi-uplink-service-boundary", INIT_BUILD),
        ("wifi-uplink-service-boundary", "wifi-uplink-service-redacted"),
        ("0.11.142", INIT_VERSION),
        ("V3386", CYCLE),
        ("v3386", "v3387"),
        ("a90-doomgeneric-v3386", "a90-doomgeneric-v3387"),
        ("a90.doomgeneric.v3386", "a90.doomgeneric.v3387"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3387_bytes(item: bytes) -> bytes:
    return _rewrite_v3387_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3387_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3387_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3387_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3387_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3387_bytes(marker) for marker in ORIG_PREVIOUS_REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.143",
    b"v3387-wifi-uplink-service-redacted",
    b"a90-native-wifi-uplink-service-v1",
    b"wifi uplink-service [status|start|stop|once]",
    b"autoconnect_profile_present=",
    b"config_profile_present=",
    b"requested_profile_present=",
    b"wifi-uplink-service-confirm-required",
    b"credentials=private-config-gated",
    b"secret_values_logged=0",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3386",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "wifi-uplink-service-redacted"
    manifest["scope"] = "native-owned-wifi-uplink-service-profile-label-redacted"
    manifest["wifi_uplink_service_boundary"]["profile_label_values"] = "redacted-to-present-booleans"
    manifest["wifi_uplink_service_boundary"]["redacted_profile_fields"] = [
        "autoconnect_profile_present",
        "config_profile_present",
        "requested_profile_present",
    ]
    manifest["wifi_uplink_service_boundary"]["obsolete_ramdisk_engines"] = [
        "bin/" + name for name in OBSOLETE_RAMDISK_ENGINES
    ]
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
        "# Native Init V3387 Wi-Fi Uplink Service Redaction Source Build",
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
        "- Carries forward the V3386 uplink-service command surface.",
        "- Tightens file-response redaction: profile label values are no longer emitted.",
        "- Replaces profile label strings with `autoconnect_profile_present`, `config_profile_present`, and `requested_profile_present` booleans.",
        "- Keeps the `confirm=A90_NATIVE_UPLINK_AUTOCONNECT_V1` gate, public tunnel denial, external ping denial, and `secret_values_logged=0` contract.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_native_wifi_uplink_service_source`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3387_wifi_uplink_service_redacted`.",
        "- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `wifi-uplink-service-redacted`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "wifi-uplink-service-redacted.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-uplink-service-redacted",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "wifi_uplink_service_redaction": {
            "profile_label_values": "redacted-to-present-booleans",
            "redacted_profile_fields": [
                "autoconnect_profile_present",
                "config_profile_present",
                "requested_profile_present",
            ],
        },
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3387(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-uplink-service-redacted",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3386_module_for_v3387() -> None:
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
        "OBSOLETE_RAMDISK_ENGINES": OBSOLETE_RAMDISK_ENGINES,
        "SOFTAP_COMMANDS": SOFTAP_COMMANDS,
        "render_report": render_report,
        "_rewrite_v3386_text": _rewrite_v3387_text,
        "_rewrite_v3386_bytes": _rewrite_v3387_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3386": _normalize_manifest_for_v3387,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3386_module_for_v3387()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
