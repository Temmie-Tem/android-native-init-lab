#!/usr/bin/env python3
"""Build the V1488 timeout-safe auto-readiness Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1488-wifi-auto-readiness-timeout-safe-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1488_WIFI_AUTO_READINESS_TIMEOUT_SAFE_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1488",
    "--decision",
    "v1488-wifi-auto-readiness-timeout-safe-test-boot-source-build-pass",
    "--cycle-label",
    "v1488",
    "--init-version",
    "0.9.91",
    "--init-build",
    "v1488-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1488_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1488_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1488_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1488",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1488.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1488.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1488.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1488.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1488-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1488-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1488-readiness.result",
    "--wifi-test-watch-sec",
    "45",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "70",
    "--wifi-test-mount-debugfs",
    "--wifi-test-auto-readiness-supervisor",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1488 Wi-Fi Auto-readiness Timeout-safe Test Boot Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1488`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot whose PID1 summary keeps readiness observable even if the helper times out",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Test-Boot Contract",
        "",
        "- Adds marker `auto-v1485-wifi-readiness-test` for the existing auto-readiness route.",
        "- Adds PID1-synthesized `auto_readiness_pid1.*` keys to the summary.",
        "- Reads kernel log state with `SYSLOG_ACTION_READ_ALL` after the bounded helper window.",
        "- Reports modem/provider trigger, PCIe RC1, MHI, WLFW, ICNSS/QMI, BDF, FW-ready, and `wlan0` checkpoints.",
        "- Bundles helper `a90_android_execns_probe v287` as `/bin/a90_android_execns_probe`.",
        "- Passes `--pm-observer-auto-readiness-summary`; helper-side `auto_readiness.*` remains useful if it exits cleanly.",
        "- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        "",
        "## Expected Timeout-safe Keys",
        "",
        "- `auto_readiness_pid1.begin=1`",
        "- `auto_readiness_pid1.primary_checkpoint`",
        "- `auto_readiness_pid1.provider_trigger_seen`",
        "- `auto_readiness_pid1.pcie_rc1_seen`",
        "- `auto_readiness_pid1.mhi_seen`",
        "- `auto_readiness_pid1.wlfw_seen`",
        "- `auto_readiness_pid1.bdf_seen`",
        "- `auto_readiness_pid1.fw_ready_seen`",
        "- `auto_readiness_pid1.wlan0_seen`",
        "- safety zeros for credentials, scan/connect, DHCP/routes, external ping, PMIC write, GPIO request, and direct eSoC ioctl",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands,",
        "flash, reboot, start Wi-Fi HAL, scan/connect, use credentials, configure",
        "DHCP/routes, perform external ping, or write device partitions.",
        "",
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot image marker verification passed, including PID1 timeout-safe readiness markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1489 should run local artifact sanity over the exact V1488 manifest before",
        "any rollbackable live handoff.",
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
