#!/usr/bin/env python3
"""Build the V1630 natural-path MDM2AP observation Wi-Fi test boot artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_text

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1630-natural-path-mdm2ap-observation-test-boot"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1630_NATURAL_PATH_MDM2AP_OBSERVATION_SOURCE_BUILD_2026-06-02.md"
)

DEFAULT_ARGS = [
    "--cycle",
    "V1630",
    "--decision",
    "v1630-natural-path-mdm2ap-observation-source-build-pass",
    "--cycle-label",
    "v1630",
    "--init-version",
    "0.9.112",
    "--init-build",
    "v1630-natural-mdm2ap",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1630_natural_mdm2ap"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1630_natural_mdm2ap.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1630_natural_mdm2ap.img"),
    "--wifi-test-klog-prefix",
    "A90v1630",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1630.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1630.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1630.summary",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1630.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1630-supervisor.pid",
    "--wifi-test-rc1-watcher-result",
    "/cache/native-init-wifi-test-boot-v1630-natural-watcher.result",
    "--wifi-test-rc1-window-result",
    "/cache/native-init-wifi-test-boot-v1630-natural-window.result",
    "--wifi-test-watch-sec",
    "45",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "70",
    "--wifi-test-mount-debugfs",
    "--wifi-test-pid1-rc1-watcher",
    "--wifi-test-rc1-watcher-timeout-sec",
    "60",
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
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    return "\n".join([
        "# Native Init V1630 Natural-path MDM2AP Observation Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1630`",
        "- Type: source/build-only rollbackable Wi-Fi test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: built the contract-defined natural `__subsystem_get(esoc0)` MDM2AP observation image without contacting or flashing the device",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Init SHA256: `{manifest['init_sha256']}`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Live Contract Encoded",
        "",
        "- Trigger remains the natural PM-first / `mdm_helper` / `pm-service` route into `__subsystem_get(esoc0)` and `mdm_subsys_powerup`.",
        "- The PID1 watcher is enabled only to detect the natural provider line; because the provider-trigger micro endpoint sampler is enabled, it samples rather than writing RC1 debugfs controls.",
        "- Arms GPIO tracepoints and `msm_pil_event:pil_notif` to capture GPIO1270/PM8150L GPIO9 PON, GPIO135/AP2MDM, GPIO142/MDM2AP, GPIO141/errfatal, and `fw=esoc0`.",
        "- Helper command keeps the existing `mdm2ap_timing.*` summary contract: GPIO142 IRQ delta, errfatal IRQ delta, PCIe/MHI/WLFW/`wlan0` context, and explicit safety-zero markers.",
        "- No forced RC1 enumerate, fake ONLINE, PMIC/GPIO/GDSC/regulator write, eSoC notify/`BOOT_DONE`, PCI rescan, platform bind/unbind, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Artifact Paths",
        "",
        f"- Log path: `{wifi['log']}`",
        f"- Summary path: `{wifi['summary']}`",
        f"- Watcher result path: `{wifi['rc1_watcher_result']}`",
        f"- Window result path: `{wifi['rc1_window_result']}`",
        "",
        "## Verification",
        "",
        "- Static init and helper verification passed.",
        "- Ramdisk entries include `/init`, `/bin/a90_android_execns_probe`, `/bin/a90_tcpctl`, and `/bin/a90_rshell`.",
        "- Boot marker verification passed, including the exact-provider PIL+GPIO tracepoint contract.",
        "- Forbidden credential-like byte scan over init/helper/ramdisk/boot image passed.",
        "",
        "## Next",
        "",
        "V1631 should run local-only artifact sanity.  V1632 may then perform one rollbackable live handoff and assign exactly one label: `mdm2ap-responds`, `mdm2ap-silent-natural-path`, or `provider-did-not-trigger`.",
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
