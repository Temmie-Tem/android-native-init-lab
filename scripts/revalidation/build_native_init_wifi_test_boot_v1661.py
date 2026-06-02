#!/usr/bin/env python3
"""Build the V1661 native natural-path power diff test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1661-native-natural-power-diff-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1661_NATIVE_NATURAL_POWER_DIFF_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1661",
    "--decision",
    "v1661-native-natural-power-diff-source-build-pass",
    "--cycle-label",
    "v1661",
    "--init-version",
    "0.9.115",
    "--init-build",
    "v1661-native-power-diff",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1661_native_power_diff"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1661_native_power_diff.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1661_native_power_diff.img"),
    "--wifi-test-klog-prefix",
    "A90v1661",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1661.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1661.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1661.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1661-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1661.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1661-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1661-natural-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1661-natural-window.result",
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
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1661 Native Natural-path Power Diff Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1661`",
        "- Type: source/build-only rollbackable native natural-path test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built a native natural-path observer that adds read-only power/clock/subsystem snapshots to the V1636 MDM2AP timing route",
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
        "- Keeps the V1636 `mdm2ap_timing.*` IRQ delta summary.",
        "- Adds `A90_V1661_REGULATOR_*` full `regulator_summary` snapshots.",
        "- Adds `A90_V1661_CLOCKS_*` targeted named-clock snapshots from individual clock debugfs leaf files only.",
        "- Adds `A90_V1661_SUBSYS_*` subsystem sequence snapshots.",
        "- Explicitly records `natural_power_diff.full_clk_summary_read=0`; full `clk_summary` is not read for the power diff path.",
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
        "Run one rollbackable V1661 live handoff, restore `stage3/boot_linux_v724.img`, verify native `selftest fail=0`, then run the V1662 host-only Android-vs-native diff classifier.",
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
