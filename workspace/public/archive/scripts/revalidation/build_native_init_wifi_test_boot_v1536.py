#!/usr/bin/env python3
"""Build the V1536 sysfs/client-enumerate Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1536-wifi-sysfs-client-enumerate-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1536_WIFI_SYSFS_CLIENT_ENUMERATE_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1536",
    "--decision",
    "v1536-wifi-sysfs-client-enumerate-test-boot-source-build-pass",
    "--cycle-label",
    "v1536",
    "--init-version",
    "0.9.98",
    "--init-build",
    "v1536-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1536_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1536_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1536_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1536",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1536.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1536.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1536.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1536.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1536-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1536-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1536-sysfs-client-enumerate.result",
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
        "# Native Init V1536 Wi-Fi Sysfs/Client Enumerate Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1536`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot that replaces PID1 debugfs TEST:11 with targeted pci-msm sysfs/client enumerate",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1515/V1535",
        "",
        "- Keeps the V1515 critical-source, source-timestamped, case-aligned micro sampling contract.",
        "- Changes only the PID1 first-L0 trigger write: `/sys/devices/platform/soc/1c08000.qcom,pcie/debug/enumerate` receives `1` instead of writing debugfs `rc_sel=2` and `case=11`.",
        "- Records `trigger_mode=sysfs_client_enumerate` in the RC1 watcher result and `sysfs_client_enumerate=1` in the window result header.",
        "- Preserves the hard exclusions: no Wi-Fi HAL start, scan/connect, credentials, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE spoof, global PCI rescan, or platform bind/unbind.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- RC1 watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Sysfs/client enumerate result path: `{wifi['rc1_window_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- sysfs/client enumerate trigger: `{wifi['rc1_sysfs_client_enumerate']}`",
        f"- micro source timestamped sampler: `{wifi['rc1_micro_source_timestamped_sampler']}`",
        f"- micro critical fast endpoint sampler: `{wifi['rc1_micro_critical_fast_endpoint_sampler']}`",
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
        "- Boot image marker verification passed, including sysfs/client enumerate, auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, source-timestamped, and critical-fast sampler markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1537 should run local artifact sanity over the exact V1536 manifest before",
        "any rollbackable live handoff. V1538 may then flash only this test image,",
        "collect the V1536 log, summary, RC1 watcher result, sysfs-client enumerate",
        "result, focused dmesg, and `wlan0` state, then roll back to v724 and verify",
        "native selftest `fail=0`.",
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
