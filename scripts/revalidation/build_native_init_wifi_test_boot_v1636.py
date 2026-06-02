#!/usr/bin/env python3
"""Build the V1636 natural-path MDM2AP PID1 IRQ-delta test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1636-natural-path-mdm2ap-irq-summary-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1636_NATURAL_PATH_MDM2AP_IRQ_SUMMARY_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1636",
    "--decision",
    "v1636-natural-path-mdm2ap-irq-summary-source-build-pass",
    "--cycle-label",
    "v1636",
    "--init-version",
    "0.9.114",
    "--init-build",
    "v1636-natural-mdm2ap-irq-summary",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1636_natural_mdm2ap_irq_summary"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1636_natural_mdm2ap_irq_summary.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1636_natural_mdm2ap_irq_summary.img"),
    "--wifi-test-klog-prefix",
    "A90v1636",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1636.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1636.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1636.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1636-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1636.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1636-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1636-natural-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1636-natural-window.result",
    "--wifi-test-watch-sec",
    "55",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "80",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "70",
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
    "--wifi-test-provider-trigger-pil-tracepoint-sampler",
    "--wifi-test-natural-mdm2ap-irq-summary",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1636 Natural-path MDM2AP IRQ Summary Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1636`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a natural-path test boot that records `mdm2ap_timing.*` IRQ deltas in the PID1 window result, independent of helper process exit",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Capture Contract",
        "",
        "- Trigger remains natural `__subsystem_get(esoc0)` -> `mdm_subsys_powerup` only.",
        "- PID1 provider window records GPIO1270/PON, GPIO135/AP2MDM, GPIO142/MDM2AP state samples, and now `mdm2ap_timing.gpio142_irq_delta` plus `mdm2ap_timing.errfatal_irq_delta` directly in the window result.",
        "- The IRQ summary samples `/proc/interrupts` read-only for 120 samples at 50 ms after the provider micro-window, using initial counts collected immediately after provider detection.",
        "- Helper result remains useful but is no longer the sole source of `mdm2ap_timing.*` evidence.",
        "- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Artifact Paths",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Helper result path: `{wifi['helper_result']}`",
        f"- Watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Window result path: `{wifi['rc1_window_result']}`",
        "",
        "## Next",
        "",
        "Run local artifact sanity first.  A later live handoff, if explicitly chosen, should flash only this V1636 image, collect the V1636 window result, roll back to `stage3/boot_linux_v724.img`, and classify using the stricter V1632 wrapper logic.",
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
