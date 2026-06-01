#!/usr/bin/env python3
"""Build the V1462 exact provider tracepoint Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1462-wifi-test-boot-exact-provider-tracepoint-sampler"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1462_WIFI_TEST_BOOT_EXACT_PROVIDER_TRACEPOINT_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1462",
    "--decision",
    "v1462-wifi-test-boot-exact-provider-tracepoint-source-build-pass",
    "--cycle-label",
    "v1462",
    "--init-version",
    "0.9.86",
    "--init-build",
    "v1462-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1462_wifi_test"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1462_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1462_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1462",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1462.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1462.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1462.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1462.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1462-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1462-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1462-rc1-window.result",
    "--wifi-test-watch-sec",
    "35",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "40",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "45",
    "--wifi-test-rc1-watcher-delay-ms",
    "0",
    "--wifi-test-rc1-window-sampler",
    "--wifi-test-rc1-endpoint-sampler",
    "--wifi-test-rc1-micro-endpoint-sampler",
    "--wifi-test-provider-trigger-micro-endpoint-sampler",
    "--wifi-test-provider-trigger-exact-line",
    "--wifi-test-provider-trigger-long-window",
    "--wifi-test-provider-trigger-thread-state",
    "--wifi-test-provider-trigger-tracepoint-sampler",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1462 Wi-Fi Test Boot Exact Provider Tracepoint Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1462`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built an exact-provider GPIO tracepoint sampler without contacting or flashing the device",
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
        "- Keeps the exact provider trigger and the V1458 thread-state sampler.",
        "- Arms `gpio_value` and `gpio_direction` tracepoints before helper start.",
        "- Samples GPIO tracepoint output for GPIO1270, GPIO135, GPIO142, and GPIO141 at each provider micro sample.",
        "- Samples endpoint state through `1000ms` plus a `1200ms` context sample.",
        "- Does not issue an explicit RC1 debugfs `rc_sel`/`case` write.",
        "- Does not write PMIC/GPIO/GDSC controls, eSoC notify/`BOOT_DONE`, or Wi-Fi HAL state.",
        "- Sampler marker: `read-only-v1462-exact-provider-tracepoint`.",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Window result path: `{wifi['rc1_window_result']}`",
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
        "- Boot image marker verification passed.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1463 should be local-only artifact sanity over the exact V1462 manifest",
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
