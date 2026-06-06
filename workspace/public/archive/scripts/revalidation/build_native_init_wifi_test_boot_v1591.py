#!/usr/bin/env python3
"""Build the V1591 late-per_proxy lower-marker Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1591-late-per-proxy-lower-marker-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1591_LATE_PER_PROXY_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1591",
    "--decision",
    "v1591-late-per-proxy-lower-marker-test-boot-source-build-pass",
    "--cycle-label",
    "v1591",
    "--init-version",
    "0.9.102",
    "--init-build",
    "v1591-late-per-proxy-lower-marker",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1591_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v294"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1591_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1591_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1591",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1591.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1591.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1591.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1591-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1591.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1591-supervisor.pid",
    "--wifi-test-watch-sec",
    "120",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "130",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "android-service-window-pm-proxy-contract-late-per-proxy-lower-marker",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1591 Late-per_proxy Lower-marker Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1591`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a firmware-mount-preserving late-per_proxy-only service-window test boot with helper v294 lower-marker sampling",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1589",
        "",
        "- Preserves firmware mount parity, private devnodes, and the helper private vendor namespace.",
        "- Bumps `a90_android_execns_probe` to v294.",
        "- Uses late `pm-proxy` ordering after the mdm_helper/CNSS window instead of the immediate V1589 `pm_proxy` placement.",
        "- Keeps `android_wifi_service_window.lower_marker` summary output while disabling the direct scoped `/dev/subsys_esoc0` trigger child.",
        "- Samples process liveness/fd counts, subsystem state, RC1/LTSSM state, runtime MHI, QRTR/WLFW request markers, BDF, FW-ready, and `wlan0` without per-sample verbose dumps.",
        "- Does not add credential handling, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC direct writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, or platform bind/unbind.",
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
        "This build script was source/build-only. It did not issue device commands,",
        "flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform",
        "external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/",
        "`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device",
        "partitions.",
        "",
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot image marker verification passed, including late `pm-proxy`, service-window PM proxy contract, firmware mounts, helper v294, and lower-marker strings.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1592 should run local artifact sanity over this exact manifest, then a",
        "rollbackable live handoff may flash only this V1591 image, collect the log,",
        "summary, helper result, focused dmesg, and `wlan0` state, then roll back to",
        "`stage3/boot_linux_v724.img` and verify native selftest `fail=0`.",
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
