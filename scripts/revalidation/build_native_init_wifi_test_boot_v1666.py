#!/usr/bin/env python3
"""Build the V1666 native pcie1 clock vote harness repair test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1666-pcie1-clock-vote-repair-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1666_PCIE1_CLOCK_VOTE_REPAIR_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1666",
    "--decision",
    "v1666-pcie1-clock-vote-repair-source-build-pass",
    "--cycle-label",
    "v1666",
    "--init-version",
    "0.9.117",
    "--init-build",
    "v1666-pcie1-clock-vote",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1666_pcie1_clock_vote"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1666_pcie1_clock_vote.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1666_pcie1_clock_vote.img"),
    "--wifi-test-klog-prefix",
    "A90v1666",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1666.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1666.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1666.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1666-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1666.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1666-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1666-natural-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1666-clock-vote-window.result",
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
    "--wifi-test-natural-power-diff-snapshot",
    "--wifi-test-pcie1-clock-vote-proof",
    "--wifi-test-pcie1-clock-vote-result",
    "/cache/native-init-wifi-test-boot-v1666-pcie1-clock-vote.result",
    "--wifi-test-pcie1-clock-vote-async",
    "--wifi-test-pcie1-clock-vote-wait-ms",
    "20000",
    "--wifi-test-pcie1-clock-vote-hold-ms",
    "30000",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1666 pcie1 Clock Vote Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1666`",
        "- Type: source/build-only rollbackable native pcie1 clock vote proof test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a V1661-style natural-path observer with async clock-debug vote readiness wait and separate result capture",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Gate Contract",
        "",
        "- Natural provider route remains the existing `__subsystem_get(esoc0)` route; no forced RC1 enumerate is enabled.",
        "- PID1 mounts debugfs, writes only targeted clock debugfs `rate`/`enable` leaves, holds them through the supervised helper window, then disables only clocks successfully enabled by the test boot.",
        "- The build keeps full `regulator_summary`, targeted named-clock, subsystem, GPIO/IRQ, provider-thread, GPIO tracepoint, and PIL tracepoint observations.",
        "- It records `pcie1_clock_vote.*` safety fields with regulator/GDSC/pci-case/PMIC/GPIO/eSoC/boot-done/scan/connect all set to zero.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
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
        "Run one rollbackable V1667 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then classify the clock vote result.",
        "",
    ])


def main() -> int:
    rc = base.main([*DEFAULT_ARGS, *sys.argv[1:]])
    if rc != 0:
        return rc
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pass"] = True
    manifest["source_build_only"] = True
    manifest["device_command"] = False
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
