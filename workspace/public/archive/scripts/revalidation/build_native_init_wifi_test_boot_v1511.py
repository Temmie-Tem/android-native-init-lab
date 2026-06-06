#!/usr/bin/env python3
"""Build the V1511 source-timestamped batched pre-L0 Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1511-wifi-source-timestamped-pre-l0-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1511_WIFI_SOURCE_TIMESTAMPED_PRE_L0_SOURCE_BUILD_2026-06-01.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1511",
    "--decision",
    "v1511-wifi-source-timestamped-pre-l0-test-boot-source-build-pass",
    "--cycle-label",
    "v1511",
    "--init-version",
    "0.9.96",
    "--init-build",
    "v1511-wifitest",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1511_wifi_test"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v287"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1511_wifi_test.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1511_wifi_test.img"),
    "--wifi-test-klog-prefix",
    "A90v1511",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1511.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1511.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1511.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1511.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1511-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1511-rc1-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1511-source-timestamped-pre-l0.result",
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
    "--wifi-test-rc1-micro-batched-focused-endpoint-sampler",
    "--wifi-test-rc1-micro-source-timestamped-sampler",
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
        "# Native Init V1511 Wi-Fi Source-Timestamped Pre-L0 Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1511`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a credential-free test boot that adds per-source begin/end timing to the batched pre-L0 sampler",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Delta From V1507/V1510",
        "",
        "- Keeps the corrected RC1 enumerate path: `/sys/kernel/debug/pci-msm/rc_sel=2` then `/sys/kernel/debug/pci-msm/case=11`.",
        "- Keeps case-aligned micro samples at `0, 1, 2, 5, 10, 20, 50, 100, 150ms` after the `case=11` write.",
        "- Keeps V1507 batched focused reads: `micro_batched_regulator`, `micro_batched_clk`, `micro_batched_debug_gpio`, `micro_batched_pinmux`, and `micro_batched_pinconf`.",
        "- Adds `micro_source_timestamped_sampler=1` and `source_timing=begin/end` lines around each micro source read.",
        "- Each source timing line records elapsed time from boot-test start, elapsed time from the micro-sampling start, source duration, and source path.",
        "",
        "## Test-Boot Contract",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- RC1 watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Source-timestamped pre-L0 result path: `{wifi['rc1_window_result']}`",
        f"- Supervisor timeout sec: `{wifi['supervisor_timeout_sec']}`",
        f"- micro batched focused endpoint sampler: `{wifi['rc1_micro_batched_focused_endpoint_sampler']}`",
        f"- micro source timestamped sampler: `{wifi['rc1_micro_source_timestamped_sampler']}`",
        "- Does not start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
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
        "- Boot image marker verification passed, including auto-readiness, PID1 RC1 watcher, endpoint, focused, case-aligned micro, batched micro-focused, and source-timestamped sampler markers.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1512 should run local artifact sanity over the exact V1511 manifest before",
        "any rollbackable live handoff. The next live gate should collect source",
        "begin/end timing for the first pre-L0 sample and decide whether a narrower",
        "critical-source sampler is needed before another boot image iteration.",
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
