#!/usr/bin/env python3
"""Build the V1493 RC1/MHI-focused auto-readiness Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1493-wifi-auto-readiness-rc1-window-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1493_WIFI_AUTO_READINESS_RC1_WINDOW_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1493",
    "--decision",
    "v1493-wifi-auto-readiness-rc1-window-test-boot-source-build-pass",
    "--cycle-label",
    "v1493",
    "--init-version",
    "0.9.92",
    "--init-build",
    "v1493-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1493_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1493_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1493_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1493",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1493.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1493.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1493.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1493.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1493-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1493-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1493-rc1-window.result",
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
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1493 Wi-Fi Auto-readiness RC1 Window Test Boot Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1493`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot that keeps the V1488 auto path and enables a PID1 RC1 watcher/window path",
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
        "- Keeps the V1488 timeout-safe `auto_readiness_pid1.*` summary.",
        "- Enables `A90_WIFI_TEST_BOOT_PID1_RC1_WATCHER`.",
        "- Enables `A90_WIFI_TEST_BOOT_RC1_WINDOW_SAMPLER`.",
        f"- RC1 watcher timeout sec: `{wifi['rc1_watcher_timeout_sec']}`",
        f"- RC1 watcher delay ms: `{wifi['rc1_watcher_delay_ms']}`",
        f"- RC1 watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- RC1 window result path: `{wifi['rc1_window_result']}`",
        "- On provider trigger, the watcher performs a bounded corrected RC1 enumerate by",
        "  writing `/sys/kernel/debug/pci-msm/rc_sel=2` and",
        "  `/sys/kernel/debug/pci-msm/case=11`, while the window sampler captures",
        "  boot-time RC1/LTSSM/MHI/proc/sysfs evidence.",
        "- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
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
        "- Boot image marker verification passed, including PID1 RC1 watcher/window and timeout-safe readiness markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1494 should run local artifact sanity over the exact V1493 manifest before",
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
