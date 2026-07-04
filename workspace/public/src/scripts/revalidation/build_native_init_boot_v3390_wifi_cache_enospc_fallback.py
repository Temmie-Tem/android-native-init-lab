#!/usr/bin/env python3
"""Build V3390 native-init boot image with Wi-Fi cache ENOSPC fallback."""

from __future__ import annotations

import json
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

from a90harness.evidence import workspace_private_build_path, workspace_private_input_path
import build_native_init_boot_v3389_wifi_connect_carrier_diagnostics as previous

base = previous.base
ORIG_PREVIOUS_REWRITE_TEXT = previous._rewrite_v3389_text
ORIG_PREVIOUS_REWRITE_BYTES = previous._rewrite_v3389_bytes
ORIG_PREVIOUS_REQUIRED_STRINGS = previous.REQUIRED_STRINGS
ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST = previous._boot_audit_manifest
ORIG_PREVIOUS_NORMALIZE_MANIFEST = previous._normalize_manifest_for_v3389

CYCLE = "V3390"
INIT_VERSION = "0.11.146"
INIT_BUILD = "v3390-wifi-cache-enospc-fallback"
BUILD_TAG = INIT_BUILD
DECISION = "v3390-wifi-cache-enospc-fallback-source-build"
EXPECTED_HELPER_MARKER = previous.EXPECTED_HELPER_MARKER
EXPECTED_HELPER_SHA256 = previous.EXPECTED_HELPER_SHA256

OUT_DIR = workspace_private_build_path("native-init", BUILD_TAG)
OBJ_DIR = OUT_DIR / "obj"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V3390_WIFI_CACHE_ENOSPC_FALLBACK_SOURCE_BUILD_2026-07-04.md"
)
BOOT_IMAGE = workspace_private_input_path(
    "boot_images",
    "boot_linux_v3390_wifi_cache_enospc_fallback.img",
    legacy_fallback=False,
)
BASE_BOOT = previous.BOOT_IMAGE
INIT_BINARY = OUT_DIR / "init_v3390_wifi_cache_enospc_fallback"
RAMDISK_CPIO = OUT_DIR / "ramdisk_v3390_wifi_cache_enospc_fallback.cpio"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v634_wifi_cache_enospc_fallback"

ENGINE_BINARY = OUT_DIR / "a90_doomgeneric_private_engine_v3390"
ENGINE_ADAPTER_SOURCE = OUT_DIR / "a90_doomgeneric_native_bridge_v3390.c"
ENGINE_ADAPTER_OBJECT = OBJ_DIR / "a90_doomgeneric_native_bridge_v3390.o"
ENGINE_RAMDISK_PATH = "bin/a90_doomgeneric_private_engine_v3390"
ENGINE_REMOTE_PATH = "/" + ENGINE_RAMDISK_PATH
ENGINE_NAME = "doomgeneric-private-link-v3390-wifi-cache-enospc-fallback"

FRAME_PATH = "/tmp/a90-doomgeneric-v3390-raw-fallback-frame.xbgr8888"
SHARED_FRAME_PATH = "/tmp/a90-doomgeneric-v3390-shared-frame.bin"
INPUT_STATE_PATH = "/tmp/a90-doomgeneric-v3390-input.state"
INPUT_SOCKET_PATH = "/tmp/a90-doomgeneric-v3390-input.sock"
PACE_SOCKET_PATH = "/tmp/a90-doomgeneric-v3390-pace.sock"
TICK_TELEMETRY_PATH = "/tmp/a90-doomgeneric-v3390-tick-telemetry.txt"
AUDIO_PCM_STREAM_PATH = "/cache/a90-runtime/a90-doomgeneric-v3390-sfx.pcmstream"

SFX_BACKEND_SOURCE = OUT_DIR / "a90_doomgeneric_native_sfx_v3390.c"
SDL_MIXER_STUB = OUT_DIR / "SDL_mixer.h"

SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG = previous.SERVICE_OBJECT_FWCLASS_BRIDGE_FLAG
SOFTAP_COMMANDS = tuple(previous.SOFTAP_COMMANDS)


def _rewrite_v3390_text(text: str) -> str:
    text = ORIG_PREVIOUS_REWRITE_TEXT(text)
    replacements = (
        ("v3389-wifi-connect-carrier-diagnostics", INIT_BUILD),
        ("0.11.145", INIT_VERSION),
        ("V3389", CYCLE),
        ("v3389", "v3390"),
        ("a90-doomgeneric-v3389", "a90-doomgeneric-v3390"),
        ("a90.doomgeneric.v3389", "a90.doomgeneric.v3390"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def _rewrite_v3390_bytes(item: bytes) -> bytes:
    return _rewrite_v3390_text(item.decode("utf-8")).encode("utf-8")


FRAME_SCALE = _rewrite_v3390_text(previous.FRAME_SCALE)
FRAME_IPC = _rewrite_v3390_text(previous.FRAME_IPC)
SFX_STREAM_MARKER = _rewrite_v3390_text(previous.SFX_STREAM_MARKER)
SOUND_MODE = _rewrite_v3390_text(previous.SOUND_MODE)

PREVIOUS_REQUIRED_STRINGS = tuple(_rewrite_v3390_bytes(marker) for marker in ORIG_PREVIOUS_REQUIRED_STRINGS)

REQUIRED_STRINGS = PREVIOUS_REQUIRED_STRINGS + (
    b"0.11.146",
    b"v3390-wifi-cache-enospc-fallback",
    b"a90-native-wifi-uplink-service-v1",
    b"wifi uplink-service [status|start|stop|once]",
    b"autoconnect_profile_present=",
    b"config_profile_present=",
    b"requested_profile_present=",
    b"scan_recovery_attempted=",
    b"scan_recovery_first_scan_rc=",
    b"scan_recovery_rc=",
    b"scan_recovery_rescan_rc=",
    b"scan_recovery_success=",
    b"scan_recovery_decision=",
    b"connect_diag_attempted=",
    b"connect_diag_decision=",
    b"connect_ctrl_status_wpa_state=",
    b"connect_carrier_wait_rc=",
    b"connect_ctrl_reassociate_rc=",
    b"wifi-connect-status-not-completed",
    b"wifi-connect-no-carrier",
    b"wifi-config-enospc-inplace-fallback",
    b"wifi_config_cache_fallback=",
    b"wifi-uplink-service-confirm-required",
    b"credentials=private-config-gated",
    b"secret_values_logged=0",
)

OBSOLETE_RAMDISK_ENGINES = tuple(dict.fromkeys([
    *previous.OBSOLETE_RAMDISK_ENGINES,
    "a90_doomgeneric_private_engine_v3389",
]))


def _boot_audit_manifest() -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_BOOT_AUDIT_MANIFEST()
    manifest["rung"] = "wifi-cache-enospc-fallback"
    manifest["scope"] = "native-owned-wifi-cache-enospc-fallback"
    manifest["wifi_uplink_service_boundary"]["scan_recovery"] = {
        "strategy": "cleanup-iftype-probe-rescan-once",
        "redacted_result_fields": [
            "scan_recovery_attempted",
            "scan_recovery_first_scan_rc",
            "scan_recovery_rc",
            "scan_recovery_rescan_rc",
            "scan_recovery_success",
            "scan_recovery_decision",
        ],
    }
    manifest["wifi_uplink_service_boundary"]["connect_diagnostics"] = {
        "strategy": "persist-redacted-connect-carrier-ctrl-summary",
        "redacted_result_fields": [
            "connect_diag_attempted",
            "connect_diag_decision",
            "connect_wlan0_wait_rc",
            "connect_wlan0_wait_elapsed_ms",
            "connect_link_up_rc",
            "connect_link_up_errno",
            "connect_prepare_rc",
            "connect_runtime_prepare_rc",
            "connect_supplicant_root_exec_rc",
            "connect_supplicant_process_count_before",
            "connect_supplicant_start_rc",
            "connect_ctrl_wait_rc",
            "connect_ctrl_wait_errno",
            "connect_ctrl_wait_elapsed_ms",
            "connect_ctrl_wait_category",
            "connect_ctrl_driver_country_rc",
            "connect_ctrl_scan_rc",
            "connect_ctrl_enable_network_rc",
            "connect_ctrl_select_network_rc",
            "connect_ctrl_reassociate_rc",
            "connect_carrier_wait_rc",
            "connect_carrier_wait_elapsed_ms",
            "connect_carrier_up_at_wait",
            "connect_ctrl_status_rc",
            "connect_ctrl_status_errno",
            "connect_ctrl_status_wpa_state",
            "connect_ctrl_status_completed",
            "connect_ctrl_signal_rc",
            "connect_ctrl_signal_errno",
            "connect_supplicant_spawned",
            "connect_supplicant_left_running",
            "connect_cleanup_status",
        ],
    }
    manifest["wifi_uplink_service_boundary"]["cache_enospc_fallback"] = {
        "strategy": "existing-config-in-place-rewrite-on-storage-pressure",
        "bounded_paths": [
            "A90_WIFICFG_SUPPLICANT_CONF",
            "WIFICFG_SUPPLICANT_TMP",
        ],
        "broad_cache_delete": False,
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
        "# Native Init V3390 Wi-Fi Cache ENOSPC Fallback Source Build",
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
        "- Carries forward the V3389 uplink-service command surface, response redaction, scan recovery, and connect diagnostics.",
        "- Adds a bounded supplicant config ENOSPC fallback for full `/cache` conditions.",
        "- Falls back to `O_NOFOLLOW` in-place rewrite of the existing generated supplicant config only when atomic temp rewrite fails with storage pressure.",
        "- Keeps the confirmed-autoconnect gate, public tunnel denial, external ping denial, and `secret_values_logged=0` contract.",
        "",
        "## Validation",
        "",
        "- Build: AArch64 helper/native-init compile, required-string audit, preserved-ramdisk overlay, boot image pack, and SHA256 capture.",
        "- Static source checks: `tests.test_native_wifi_uplink_service_source` and `tests.test_native_wifi_cache_enospc_fallback_source`.",
        "- Builder regression: `tests.test_build_native_init_boot_v3390_wifi_cache_enospc_fallback`.",
        "- No association, DHCP, ping, public exposure, userdata, or switch-root action was performed in this source unit.",
        "",
        "## Metadata",
        "",
        f"- Helper flags: `{', '.join(helper_flags)}`",
        f"- Init extra flags: `{', '.join(init_extra_flags)}`",
        "- Candidate type: `wifi-cache-enospc-fallback`.",
    ]) + "\n"


def _write_candidate_manifest(manifest: dict[str, Any]) -> None:
    (OUT_DIR / "wifi-cache-enospc-fallback.json").write_text(json.dumps({
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-cache-enospc-fallback",
        "boot_image": base.rel(BOOT_IMAGE),
        "boot_sha256": manifest["boot_sha256"],
        "init_version": manifest["init_version"],
        "init_build": manifest["init_build"],
        "helper_sha256": manifest.get("helper_sha256", ""),
        "source_report": base.rel(REPORT_PATH),
        "base_boot": base.rel(BASE_BOOT),
        "rollback_baseline": "v2321-usb-clean-identity-rodata",
        "wifi_autoconnect_scan_recovery": {
            "strategy": "cleanup-iftype-probe-rescan-once",
            "redacted_result_fields": [
                "scan_recovery_attempted",
                "scan_recovery_first_scan_rc",
                "scan_recovery_rc",
                "scan_recovery_rescan_rc",
                "scan_recovery_success",
                "scan_recovery_decision",
            ],
        },
        "wifi_connect_carrier_diagnostics": {
            "strategy": "persist-redacted-connect-carrier-ctrl-summary",
            "redacted_result_fields": manifest["boot_audit"]["wifi_uplink_service_boundary"]["connect_diagnostics"]["redacted_result_fields"],
        },
        "wifi_cache_enospc_fallback": manifest["boot_audit"]["wifi_uplink_service_boundary"]["cache_enospc_fallback"],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_manifest_for_v3390(manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = ORIG_PREVIOUS_NORMALIZE_MANIFEST(manifest)
    manifest.update({
        "decision": DECISION,
        "cycle": CYCLE,
        "candidate_tag": INIT_BUILD,
        "candidate_type": "wifi-cache-enospc-fallback",
        "adoption_state": "source-built-live-gated",
        "boot_image": base.rel(BOOT_IMAGE),
        "init_version": INIT_VERSION,
        "init_build": INIT_BUILD,
        "boot_audit": _boot_audit_manifest(),
    })
    return manifest


def _patch_v3389_module_for_v3390() -> None:
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
        "_rewrite_v3389_text": _rewrite_v3390_text,
        "_rewrite_v3389_bytes": _rewrite_v3390_bytes,
        "_boot_audit_manifest": _boot_audit_manifest,
        "_write_candidate_manifest": _write_candidate_manifest,
        "_normalize_manifest_for_v3389": _normalize_manifest_for_v3390,
    }
    for name, value in replacements.items():
        setattr(previous, name, value)


def main() -> int:
    _patch_v3389_module_for_v3390()
    return previous.main()


if __name__ == "__main__":
    raise SystemExit(main())
