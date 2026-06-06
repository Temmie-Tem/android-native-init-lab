#!/usr/bin/env python3
"""Build the V1625 pm-service shutdown-list allowlist Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1625-pm-service-shutdown-list-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1625_PM_SERVICE_SHUTDOWN_LIST_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1625",
    "--decision",
    "v1625-pm-service-shutdown-list-test-boot-source-build-pass",
    "--cycle-label",
    "v1625",
    "--init-version",
    "0.9.111",
    "--init-build",
    "v1625-pm-service-shutdown-list",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1625_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v303"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1625_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1625_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1625",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1625.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1625.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1625.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1625-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1625.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1625-supervisor.pid",
    "--wifi-test-watch-sec",
    "120",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "130",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "android-service-window-pm-proxy-contract-pm-first-late-per-proxy-pph-gate-per-mgr-system-info-surface-lower-marker",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1625 pm-service Shutdown-list Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1625`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built the V1621 route with helper v303 and android service-window shutdown-critical-list allowlist repair",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1621/V1624",
        "",
        "- Bumps `a90_android_execns_probe` to v303.",
        "- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.",
        "- Keeps private property-root materialization for android service-window modes.",
        "- Enables the existing property-shim `vendor.peripheral.shutdown_critical_list` allowlist only for android service-window mode with `--allow-android-wifi-service-window`.",
        "- Keeps scan/connect, credential handling, DHCP/routes, and external ping disabled.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Helper result path: `{wifi['helper_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Firmware mounts: `{wifi['firmware_mounts']}`",
        f"- Android service window: `{wifi['android_service_window']}`",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.",
        "",
        "## Next",
        "",
        "V1626 should run local artifact sanity over this exact manifest. If it passes, V1627 can perform a rollbackable live handoff to verify whether the shutdown-critical-list requests are accepted and whether `pm-service` advances beyond the OFFLINE-only path.",
        "",
    ])


def main() -> int:
    rc = base.main([*DEFAULT_ARGS, *sys.argv[1:]])
    if rc != 0:
        return rc
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
