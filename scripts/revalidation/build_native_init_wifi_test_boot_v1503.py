#!/usr/bin/env python3
"""Build the V1503 dense pre-L0 endpoint parity Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1503-wifi-dense-pre-l0-parity-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1503_WIFI_DENSE_PRE_L0_PARITY_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1503",
    "--decision",
    "v1503-wifi-dense-pre-l0-parity-test-boot-source-build-pass",
    "--cycle-label",
    "v1503",
    "--init-version",
    "0.9.94",
    "--init-build",
    "v1503-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1503_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1503_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1503_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1503",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1503.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1503.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1503.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1503.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1503-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1503-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1503-dense-pre-l0-parity.result",
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
    "--wifi-test-rc1-micro-focused-endpoint-sampler",
    "--wifi-test-rc1-case-aligned-micro-endpoint-sampler",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1503 Wi-Fi Dense Pre-L0 Parity Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1503`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot that adds dense focused regulator/clock/GDSC sampling to the V1499 case-aligned micro window",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1499",
        "",
        "- Keeps the V1499 PID1 provider-triggered corrected RC1 enumerate path:",
        "  `/sys/kernel/debug/pci-msm/rc_sel=2` then",
        "  `/sys/kernel/debug/pci-msm/case=11`.",
        "- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms`",
        "  after the `case=11` write.",
        "- Adds `micro_focused_*` reads to every micro sample for `pcie_1_gdsc`,",
        "  PCIe1 clocks/refclk, GPIO102/PERST, GPIO103/CLKREQ, GPIO104/WAKE,",
        "  GPIO135/AP2MDM, GPIO142/MDM2AP, pinmux, and pinconf.",
        "- Keeps the 200ms post case-aligned full endpoint sample for context.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- RC1 watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Dense pre-L0 parity result path: `{wifi['rc1_window_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- micro focused endpoint sampler: `{wifi['rc1_micro_focused_endpoint_sampler']}`",
        "- Does not start Wi-Fi HAL, scan/connect, use credentials, configure",
        "  DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands,",
        "flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform",
        "global PCI rescan/platform bind-unbind, or write device partitions. The",
        "produced image is for a later rollbackable handoff gate only.",
        "",
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, and micro-focused sampler markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1504 should run local artifact sanity over the exact V1503 manifest before",
        "any rollbackable live handoff. Live V1505, if allowed by V1504, should collect",
        "only the V1503 log, summary, watcher, dense pre-L0 parity result, focused",
        "dmesg, and `wlan0` state, then roll back to v724 and verify selftest.",
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
