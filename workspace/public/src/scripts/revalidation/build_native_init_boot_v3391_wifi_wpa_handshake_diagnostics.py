#!/usr/bin/env python3
"""Build V3391 native-init boot image with Wi-Fi WPA handshake diagnostics."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3390_wifi_cache_enospc_fallback as previous

base = previous.base
ORIG_V3390_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_V3390_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_V3390_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3390

CYCLE = "V3391"
INIT_VERSION = "0.11.147"
INIT_BUILD = "v3391-wifi-wpa-handshake-diagnostics"
BUILD_TAG = INIT_BUILD
DECISION = "v3391-wifi-wpa-handshake-diagnostics-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3391_WIFI_WPA_HANDSHAKE_DIAGNOSTICS_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3391_wifi_wpa_handshake_diagnostics.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3391_wifi_wpa_handshake_diagnostics"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3391_wifi_wpa_handshake_diagnostics.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v634_wifi_wpa_handshake_diagnostics"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3391"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3391.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3391.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3391"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3391-wifi-wpa-handshake-diagnostics"

FRAME_PATH = "/tmp/a90-doomgeneric-v3391-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3391-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3391-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3391-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3391-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3391-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3391-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3391.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3391_text(text: str) -> str:
    text = previous.ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3390-wifi-cache-enospc-fallback", INIT_BUILD),
        ("0.11.146", INIT_VERSION),
        ("V3390", CYCLE),
        ("v3390", "v3391"),
        ("v3389-wifi-connect-carrier-diagnostics", INIT_BUILD),
        ("0.11.145", INIT_VERSION),
        ("V3389", CYCLE),
        ("v3389", "v3391"),
        ("a90-doomgeneric-v3390", "a90-doomgeneric-v3391"),
        ("a90.doomgeneric.v3390", "a90.doomgeneric.v3391"),
        ("a90-doomgeneric-v3389", "a90-doomgeneric-v3391"),
        ("a90.doomgeneric.v3389", "a90.doomgeneric.v3391"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3391_bytes(item: bytes) -> bytes:
    return _rewrite_v3391_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3391_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3391_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3391_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3391_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3391_bytes(marker) for marker in ORIG_V3390_REQUIRED_STRINGS)

WPA_HANDSHAKE_FIELDS = (
    "connect_wpa_complete_wait_rc",
    "connect_wpa_complete_wait_elapsed_ms",
    "connect_wpa_complete_samples",
    "connect_wpa_complete_completed",
    "connect_wpa_complete_retry_count",
    "connect_wpa_complete_first_state",
    "connect_wpa_complete_last_state",
    "connect_wpa_monitor_attach_rc",
    "connect_wpa_monitor_attach_errno",
    "connect_wpa_monitor_event_count",
    "connect_wpa_monitor_connected_seen",
    "connect_wpa_monitor_disconnected_seen",
    "connect_wpa_monitor_scan_results_seen",
    "connect_wpa_monitor_assoc_reject_seen",
    "connect_wpa_monitor_auth_reject_seen",
    "connect_wpa_monitor_temp_disabled_seen",
    "connect_wpa_monitor_eap_failure_seen",
    "connect_wpa_monitor_last_event",
)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.147",
    b"v3391-wifi-wpa-handshake-diagnostics",
    b"ctrl.monitor_attach_rc=",
    b"wpa_complete_wait_rc=",
    b"wpa_complete_last_state=",
    b"wpa_monitor_event_count=",
    b"connect_wpa_complete_wait_rc=",
    b"connect_wpa_complete_last_state=",
    b"connect_wpa_monitor_event_count=",
    b"connect_wpa_monitor_last_event=",
    b"ssid-temp-disabled",
    b"wifi-connect-status-not-completed",
    b"wifi-config-enospc-inplace-fallback",
    b"secret_values_logged=0",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3390",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_V3390_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "wifi-wpa-handshake-diagnostics"
    manifest["scope"] = "native-owned-wifi-wpa-handshake-diagnostics"
    fields = list(manifest["wifi_uplink_service_boundary"]["connect_diagnostics"]["redacted_result_fields"])
    for field in WPA_HANDSHAKE_FIELDS:
        if field not in fields:
            fields.append(field)
    manifest["wifi_uplink_service_boundary"]["connect_diagnostics"] = {
        "strategy": "wait-and-persist-redacted-wpa-handshake-summary",
        "redacted_result_fields": fields,
    }
    manifest["wifi_uplink_service_boundary"]["wpa_handshake_diagnostics"] = {
        "complete_wait_ms": 25000,
        "sample_ms": 1000,
        "retry_ms": 5000,
        "monitor_event_categories_only": True,
        "raw_event_logging": False,
        "event_categories": [
            "connected",
            "disconnected",
            "scan-results",
            "assoc-reject",
            "auth-reject",
            "ssid-temp-disabled",
            "eap-failure",
            "regdom-change",
            "scan-started",
            "other",
        ],
    }
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
        "# Native Init V3391 Wi-Fi WPA Handshake Diagnostics Source Build",
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
        "- Carries forward the V3390 uplink-service surface, response redaction, scan recovery, connect diagnostics, and cache ENOSPC fallback.",
        "- Adds a bounded WPA completion wait after carrier-up so native autoconnect does not fail on the first transient 4-way-handshake STATUS sample.",
        "- Adds a WPA control monitor that records only event categories and counters; raw WPA events, SSID, BSSID, MAC, IP, and credentials remain unlogged.",
        "- Keeps confirmed-autoconnect gating, public tunnel denial, external ping denial, and `secret_values_logged=0`.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_native_wifi_uplink_service_source`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics`.",
        "- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `wifi-wpa-handshake-diagnostics`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "wifi-wpa-handshake-diagnostics.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-wpa-handshake-diagnostics",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "wifi_wpa_handshake_diagnostics": manifest["boot_audit"]["wifi_uplink_service_boundary"]["wpa_handshake_diagnostics"],
        "wifi_connect_diagnostics": {
            "strategy": manifest["boot_audit"]["wifi_uplink_service_boundary"]["connect_diagnostics"]["strategy"],
            "redacted_result_fields": manifest["boot_audit"]["wifi_uplink_service_boundary"]["connect_diagnostics"]["redacted_result_fields"],
        },
        "wifi_cache_enospc_fallback": manifest["boot_audit"]["wifi_uplink_service_boundary"]["cache_enospc_fallback"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3391(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_V3390_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-wpa-handshake-diagnostics",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3390_module_for_v3391() -> None:
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
        "_rewrite_v3390_text": _rewrite_v3391_text,
        "_rewrite_v3390_bytes": _rewrite_v3391_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3390": _normalize_manifest_for_v3391,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3390_module_for_v3391()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
