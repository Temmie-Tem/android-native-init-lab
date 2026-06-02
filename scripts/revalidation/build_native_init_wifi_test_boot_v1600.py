#!/usr/bin/env python3
"""Build the V1600 PM-first late-per-proxy PPH-gate lower-marker Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1600_PM_FIRST_LATE_PER_PROXY_PPH_GATE_LOWER_MARKER_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1600",
    "--decision",
    "v1600-pm-first-late-per-proxy-pph-gate-lower-marker-test-boot-source-build-pass",
    "--cycle-label",
    "v1600",
    "--init-version",
    "0.9.105",
    "--init-build",
    "v1600-pm-first-late-per-proxy-pph-gate-lower-marker",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1600_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v297"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1600_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1600_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1600",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1600.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1600.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1600.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1600-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1600.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1600-supervisor.pid",
    "--wifi-test-watch-sec",
    "120",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "130",
    "--wifi-test-firmware-mounts",
    "--wifi-test-helper-mode",
    "android-service-window-pm-proxy-contract-pm-first-late-per-proxy-pph-gate-lower-marker",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1600 PM-first Late-per-proxy PPH-gate Lower-marker Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1600`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a firmware-mount-preserving PM-first late-per-proxy PPH-gated service-window test boot with helper v297 lower-marker sampling",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1592",
        "",
        "- Preserves V1591 firmware mount parity, private devnodes, and the helper private vendor namespace.",
        "- Bumps `a90_android_execns_probe` to v297.",
        "- Adds `--allow-android-wifi-service-window-pm-first-late-per-proxy-route` and `--allow-android-wifi-service-window-pph-modem-fd-gate`.",
        "- Uses V1238/V1303-inspired stripped ordering, but gates `per_mgr` until `pm_proxy_helper` holds `/dev/subsys_modem`: service managers, `pm_proxy_helper`, fd gate, `per_mgr`, `cnss-daemon`, `mdm_helper`, late `pm-proxy`, then lower-marker sampling.",
        "- Does not start Wi-Fi HAL or `wificond` before PM-service-owned `/dev/subsys_esoc0` observation.",
        "- Keeps the direct scoped `/dev/subsys_esoc0` trigger child disabled.",
        "- Classifies PPH fd gate timeout as `pm-proxy-helper-modem-fd-missing`, otherwise classifies PM-service-owned powerup with `pm-service-owned-powerup-observed` or `pm-service-owned-powerup-missing`.",
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
        "- Boot image marker verification passed, including PM-first late-per-proxy PPH-gate route strings, service-window PM proxy contract, firmware mounts, helper v297, and lower-marker strings.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1601 should run local artifact sanity over this exact manifest.  If sanity",
        "passes, V1602 can perform a rollbackable live handoff that flashes only the",
        "V1600 image, collects the helper result/lower markers/dmesg/`wlan0`, then",
        "rolls back to `stage3/boot_linux_v724.img` and verifies native selftest",
        "`fail=0`.",
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
