#!/usr/bin/env python3
"""Build the V1604 per_mgr startup-trace Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1604-per-mgr-startup-trace-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1604_PER_MGR_STARTUP_TRACE_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1604",
    "--decision",
    "v1604-per-mgr-startup-trace-test-boot-source-build-pass",
    "--cycle-label",
    "v1604",
    "--init-version",
    "0.9.106",
    "--init-build",
    "v1604-per-mgr-startup-trace",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1604_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v298"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1604_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1604_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1604",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1604.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1604.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1604.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1604-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1604.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1604-supervisor.pid",
    "--wifi-test-watch-sec",
    "120",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "130",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "android-service-window-pm-proxy-contract-pm-first-late-per-proxy-pph-gate-per-mgr-startup-trace-lower-marker",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1604 per_mgr Startup Trace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1604`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built the V1602 route with helper v298 and a bounded `per_mgr` startup trace after the proven PPH modem-fd gate",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1600",
        "",
        "- Bumps `a90_android_execns_probe` to v298.",
        "- Preserves the V1600 PM-first late-per-proxy PPH-gated lower-marker route.",
        "- Adds `--allow-android-wifi-service-window-per-mgr-startup-trace`.",
        "- Samples `per_mgr` every 20ms for 1s after spawn, recording liveness, state, cmdline, cwd, wchan, exit timing, and fd counts for `/dev/subsys_modem`, `/dev/subsys_esoc0`, binder nodes, sockets, and `/dev/socket`.",
        "- Keeps Wi-Fi HAL/`wificond`, direct scoped `/dev/subsys_esoc0`, credentials, scan/connect, DHCP/routes, external ping, PMIC/GPIO/GDSC writes, blind eSoC notify/`BOOT_DONE`, global PCI rescan, and platform bind/unbind disabled.",
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
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot image marker verification passed, including the V1604 per_mgr startup trace markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Safety Scope",
        "",
        "This build script was source/build-only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan/platform bind-unbind, or write device partitions.",
        "",
        "## Next",
        "",
        "V1605 should run local artifact sanity over this exact manifest.  If it passes, V1606 can perform a rollbackable live handoff that flashes only the V1604 image, collects helper result/lower markers/dmesg/`wlan0`, rolls back to `stage3/boot_linux_v724.img`, and verifies native selftest `fail=0`.",
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
