#!/usr/bin/env python3
"""V1626 local-only sanity verifier for the V1625 pm-service shutdown-list boot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_test_boot_artifact_sanity_v1591 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
_BASE_DECIDE = base.decide

base.DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1625-pm-service-shutdown-list-test-boot"
    / "manifest.json"
)
base.DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1626-pm-service-shutdown-list-artifact-sanity"
base.DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1626_PM_SERVICE_SHUTDOWN_LIST_ARTIFACT_SANITY_2026-06-02.md"
)
base.EXPECTED_DECISION = "v1625-pm-service-shutdown-list-test-boot-source-build-pass"
base.EXPECTED_HELPER = "a90_android_execns_probe_v303"
base.EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.111 (v1625-pm-service-shutdown-list)",
    "a90_android_execns_probe v303",
    "A90v1625",
    "wifi test boot armed",
    "/cache/native-init-wifi-test-boot-v1625-helper.result",
    "firmware_mounts_requested",
    "firmware mounts prepare rc=",
    "A90v641: firmware mounts ready",
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window-pm-proxy-contract",
    "--allow-android-wifi-service-window-late-per-proxy-only",
    "--allow-android-wifi-service-window-pm-first-late-per-proxy-route",
    "--allow-android-wifi-service-window-pph-modem-fd-gate",
    "--allow-android-wifi-service-window-per-mgr-startup-trace",
    "--allow-android-wifi-service-window-per-mgr-nonstop-context-trace",
    "--allow-android-wifi-service-window-per-mgr-system-info-surface",
    "android_wifi_service_window.per_mgr_startup_trace.begin=1",
    "android_wifi_service_window.per_mgr_system_info_surface=%d",
    "pm_service_system_info_surface.%s.begin=1",
    "pm_service_system_info_surface.%s.no_ioctl=1",
    "pm_service_system_info_surface.%s.no_subsys_open=1",
    "android_wifi_service_window.per_mgr_nonstop_context_trace=%d",
    "wifi_registry_snapshot.%s.begin=1",
    "android_wifi_service_window.runtime_per_mgr_pre_startup_trace",
    "android_wifi_service_window.runtime_per_mgr_post_startup_trace",
    "android_wifi_service_window.credentials=0",
    "android_wifi_service_window.dhcp_routing=0",
    "android_wifi_service_window.external_ping=0",
)
base.EXPECTED_HELPER_MARKERS = (
    "a90_android_execns_probe v303",
    "--allow-android-wifi-service-window-per-mgr-startup-trace",
    "--allow-android-wifi-service-window-per-mgr-nonstop-context-trace",
    "wifi_hal_composite_start.property_service_shim.allow_peripheral_shutdown_list=%d",
    "vendor.peripheral.shutdown_critical_list:SDX50M_|SDX50M_modem_",
    "android_wifi_service_window.per_mgr_startup_trace=%d",
    "android_wifi_service_window.per_mgr_early_exit_trace=%d",
    "android_wifi_service_window.per_mgr_nonstop_context_trace=%d",
    "android_wifi_service_window.per_mgr_startup_trace.begin=1",
    "android_wifi_service_window.per_mgr_startup_trace.sample_count=%d",
    "wifi_registry_snapshot.%s.begin=1",
    "wifi_registry_snapshot.%s.dev_socket_capture_path=%s",
    "android_wifi_service_window.runtime_per_mgr_pre_startup_trace",
    "android_wifi_service_window.runtime_per_mgr_post_startup_trace",
    "android_wifi_service_window.lower_marker.begin=1",
    "android_wifi_service_window.lower_marker.mode=service-window-pm-proxy-contract-lower-marker",
    "android_wifi_service_window.lower_marker.scan_connect=0",
    "android_wifi_service_window.lower_marker.credentials=0",
    "android_wifi_service_window.lower_marker.external_ping=0",
)
base.EXPECTED_INIT_MARKERS = (
    "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
    "--result-output-path",
    "--allow-android-wifi-service-window",
    "--allow-android-wifi-service-window-subsys-trigger-capture",
    "--allow-android-wifi-service-window-pm-proxy-contract",
    "--allow-android-wifi-service-window-late-per-proxy-only",
    "--allow-android-wifi-service-window-pm-first-late-per-proxy-route",
    "--allow-android-wifi-service-window-pph-modem-fd-gate",
    "--allow-android-wifi-service-window-per-mgr-startup-trace",
    "--allow-android-wifi-service-window-per-mgr-nonstop-context-trace",
    "--allow-android-wifi-service-window-per-mgr-system-info-surface",
)


def contract_check(wifi_test: dict[str, Any], safety: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "label": "v1625",
        "fresh_log": True,
        "summary_watcher": True,
        "supervise_helper": True,
        "supervisor_timeout_sec": 130,
        "watch_sec": 120,
        "helper_mode": "android-service-window-pm-proxy-contract-pm-first-late-per-proxy-pph-gate-per-mgr-system-info-surface-lower-marker",
        "helper_runtime_mode": "wifi-companion-android-wifi-service-window-subsys-trigger-capture",
        "helper_result": "/cache/native-init-wifi-test-boot-v1625-helper.result",
        "android_service_window": True,
        "scan_connect_credentials": False,
        "mount_debugfs": False,
        "firmware_mounts": True,
        "pid1_rc1_watcher": False,
        "rc1_window_sampler": False,
        "auto_readiness_supervisor": False,
        "rc1_retry_count": 0,
    }
    expected_safety = {
        "device_command": False,
        "flash": False,
        "partition_write": False,
        "wifi_scan_connect": False,
        "credentials": False,
        "dhcp_routes_external_ping": False,
    }
    observed = {key: wifi_test.get(key) for key in expected}
    safety_observed = {key: safety.get(key) for key in expected_safety}
    mismatches = {
        key: {"expected": expected[key], "observed": observed[key]}
        for key in expected
        if observed[key] != expected[key]
    }
    safety_mismatches = {
        key: {"expected": expected_safety[key], "observed": safety_observed[key]}
        for key in expected_safety
        if safety_observed[key] != expected_safety[key]
    }
    return {
        **observed,
        "safety": safety_observed,
        "mismatches": mismatches,
        "safety_mismatches": safety_mismatches,
        "ok": not mismatches and not safety_mismatches,
    }


def decide(checks: dict[str, Any]) -> tuple[str, bool, str]:
    decision, pass_ok, _reason = _BASE_DECIDE(checks)
    if pass_ok:
        return (
            "v1626-pm-service-shutdown-list-artifact-sanity-pass",
            True,
            "V1625 pm-service shutdown-list test boot artifact passed local sanity",
        )
    return (
        "v1626-pm-service-shutdown-list-artifact-sanity-blocked",
        False,
        f"V1625 artifact sanity failed; base decision was {decision}",
    )


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1626 pm-service Shutdown-list Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1626`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1625 manifest: `{manifest['_path']}`",
        f"- V1625 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot shutdown-list markers: `{checks['boot_markers']['ok']}`",
        f"- helper shutdown-list markers: `{checks['helper_markers']['ok']}`",
        f"- init route: `{checks['init_route']['ok']}`",
        f"- route contract: `{checks['wifi_test_contract']['ok']}`",
        f"- header parity: `{checks['header_parity']['header_args_ok']}`",
        f"- kernel parity: `{checks['header_parity']['kernel_sha256_ok']}`",
        f"- forbidden credential-like bytes absent: `{checks['forbidden_bytes']['ok']}`",
        f"- private modes: `{checks['private_modes']['ok']}`",
        "",
        "## Artifact",
        "",
        f"- boot image: `{manifest['boot_image']}`",
        f"- boot sha256: `{manifest['boot_sha256']}`",
        f"- ramdisk sha256: `{manifest['ramdisk_sha256']}`",
        f"- init sha256: `{manifest['init_sha256']}`",
        f"- helper sha256: `{manifest['helper_sha256']}`",
        f"- helper marker: `{manifest['helper_marker']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC direct write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind was performed by this verifier.",
        "",
        "## Next",
        "",
        "A later rollbackable live handoff may flash only the V1625 image, verify shutdown-critical-list requests are accepted by the property shim, collect `pm_service_system_info_surface.*`, then roll back to `stage3/boot_linux_v724.img` and verify selftest `fail=0`.",
        "",
    ])


base.contract_check = contract_check
base.decide = decide
base.render_report = render_report


if __name__ == "__main__":
    raise SystemExit(base.main())
