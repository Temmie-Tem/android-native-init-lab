#!/usr/bin/env python3
"""Build the V1621 pm-service property-root materialization Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1621-pm-service-property-root-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1621_PM_SERVICE_PROPERTY_ROOT_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1621",
    "--decision",
    "v1621-pm-service-property-root-test-boot-source-build-pass",
    "--cycle-label",
    "v1621",
    "--init-version",
    "0.9.110",
    "--init-build",
    "v1621-pm-service-property-root",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1621_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v302"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1621_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1621_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1621",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1621.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1621.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1621.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1621-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1621.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1621-supervisor.pid",
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
        "# Native Init V1621 pm-service Property-root Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1621`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built the V1617 route with helper v302 and private property-root materialization repair",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1617/V1620",
        "",
        "- Bumps `a90_android_execns_probe` to v302.",
        "- Preserves the PM-first late-per-proxy PPH-gated lower-marker route.",
        "- Keeps the non-ptrace `per_mgr` startup/context branch.",
        "- Keeps `--allow-android-wifi-service-window-per-mgr-system-info-surface` and repairs private property-root materialization for android service-window modes.",
        "- Captures read-only `pm_service_system_info_surface.*` snapshots before and after `per_mgr` startup tracing.",
        "",
        "## Materialized Surface",
        "",
        "- `/sys/bus/msm_subsys/devices`",
        "- `/sys/bus/esoc/devices`",
        "- `/sys/class/esoc-dev`",
        "- `/dev/subsys_*`, `/dev/esoc-*`, `/dev/vndbinder`, `/dev/binder`, `/dev/hwbinder`",
        "- private property root, property-service socket, and service-manager sockets",
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
        "V1622 should run local artifact sanity over this exact manifest. If it passes, V1623 can perform a rollbackable live handoff to verify `/dev/__properties__` is present in the private namespace and reclassify the `pm-service` OFFLINE-only boundary.",
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
