#!/usr/bin/env python3
"""Build the V1541 endpoint-electrical observer Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1541-endpoint-electrical-observer-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1541_ENDPOINT_ELECTRICAL_OBSERVER_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1541",
    "--decision",
    "v1541-endpoint-electrical-observer-test-boot-source-build-pass",
    "--cycle-label",
    "v1541",
    "--init-version",
    "0.9.99",
    "--init-build",
    "v1541-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1541_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1541_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1541_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1541",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1541.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1541.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1541.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1541.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1541-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1541-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1541-endpoint-electrical.result",
    "--wifi-test-watch-sec",
    "45",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "70",
    "--wifi-test-mount-debugfs",
    "--wifi-test-auto-readiness-supervisor",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "70",
    "--wifi-test-rc1-watcher-delay-ms",
    "0",
    "--wifi-test-rc1-window-sampler",
    "--wifi-test-rc1-endpoint-sampler",
    "--wifi-test-rc1-focused-endpoint-sampler",
    "--wifi-test-rc1-micro-endpoint-sampler",
    "--wifi-test-rc1-micro-source-timestamped-sampler",
    "--wifi-test-rc1-micro-critical-fast-endpoint-sampler",
    "--wifi-test-rc1-micro-focused-endpoint-sampler",
    "--wifi-test-rc1-case-aligned-micro-endpoint-sampler",
    "--wifi-test-rc1-sysfs-client-enumerate",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1541 Endpoint Electrical Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1541`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot that keeps the V1536 sysfs/client enumerate trigger and adds micro-focused endpoint electrical sampling",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1536/V1540",
        "",
        "- Keeps the V1536 targeted sysfs/client enumerate trigger at `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate`.",
        "- Keeps the critical-fast sampler for `/proc/interrupts`, `/sys/kernel/debug/gpio`, regulator summary, and pinmux.",
        "- Adds the existing micro-focused sampler so each case-aligned micro sample also attempts exact-match reads for `micro_focused_clk`, `micro_focused_pinconf`, `micro_focused_pinmux`, `micro_focused_debug_gpio`, and focused regulator lines.",
        "- Targets the V1540 observables: GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE, GPIO135/AP2MDM, GPIO142/MDM2AP, `pcie_1_gdsc`, `gcc_pcie_1_*`, clkref/refgen, and pinconf state in the RC1 link-training window.",
        "- Does not add new live mutation beyond the already bounded sysfs/client enumerate trigger. No PMIC/GPIO/GDSC direct write, eSoC notify/BOOT_DONE spoof, global PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- RC1 watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Endpoint electrical result path: `{wifi['rc1_window_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- sysfs/client enumerate trigger: `{wifi['rc1_sysfs_client_enumerate']}`",
        f"- micro source timestamped sampler: `{wifi['rc1_micro_source_timestamped_sampler']}`",
        f"- micro critical fast endpoint sampler: `{wifi['rc1_micro_critical_fast_endpoint_sampler']}`",
        f"- micro focused endpoint sampler: `{wifi['rc1_micro_focused_endpoint_sampler']}`",
        f"- case-aligned micro sampler: `{wifi['rc1_case_aligned_micro_endpoint_sampler']}`",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands,",
        "flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform",
        "global PCI rescan/platform bind-unbind, or write device partitions.",
        "",
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot image marker verification passed, including sysfs/client enumerate, auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, source-timestamped, critical-fast, and micro-focused sampler markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1542 should run local artifact sanity over the exact V1541 manifest before",
        "any rollbackable live handoff. If sanity passes, V1543 may flash only this",
        "test image, collect the V1541 log, summary, RC1 watcher result, endpoint",
        "electrical result, focused dmesg, and `wlan0` state, then roll back to v724",
        "and verify native selftest `fail=0`.",
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
