#!/usr/bin/env python3
"""Build the V1485 auto-readiness Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1485-wifi-auto-readiness-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1485_WIFI_AUTO_READINESS_TEST_BOOT_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1485",
    "--decision",
    "v1485-wifi-auto-readiness-test-boot-source-build-pass",
    "--cycle-label",
    "v1485",
    "--init-version",
    "0.9.90",
    "--init-build",
    "v1485-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1485_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1485_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1485_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1485",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1485.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1485.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1485.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1485.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1485-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1485-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1485-readiness.result",
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
        "# Native Init V1485 Wi-Fi Auto-readiness Test Boot Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1485`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free auto-readiness test boot that runs the bounded helper readiness route at boot",
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
        "- Adds marker `auto-v1485-wifi-readiness-test`.",
        "- Bundles helper `a90_android_execns_probe v287` as `/bin/a90_android_execns_probe`.",
        "- Passes `--pm-observer-auto-readiness-summary` to emit `auto_readiness.*` keys.",
        "- Uses the existing bounded current-route PM/CNSS readiness observer without adding a new lower mutation.",
        "- Keeps RC1 debugfs enumerate/write paths disabled for this auto-readiness image.",
        "- Uses debugfs only for read-only diagnostics and PID1 cleanup.",
        "- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        "",
        "## Expected Readiness Keys",
        "",
        "- `auto_readiness.wlfw_start_seen`",
        "- `auto_readiness.icnss_qmi_seen`",
        "- `auto_readiness.bdf_seen`",
        "- `auto_readiness.fw_ready_seen`",
        "- `auto_readiness.wlan0_seen`",
        "- `auto_readiness.primary_checkpoint`",
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
        "- Boot image marker verification passed, including the auto-readiness marker and helper flag contract.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1486 should be local-only artifact sanity over the exact V1485 manifest",
        "before any rollbackable live handoff.",
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

