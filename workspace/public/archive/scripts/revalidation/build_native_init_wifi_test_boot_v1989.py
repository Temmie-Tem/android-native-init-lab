#!/usr/bin/env python3
"""Build V1989 light native wlanmdsp trace test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1936 as prev1936


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1989-light-native-wlanmdsp-trace-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1989/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v363"
EXPECTED_HELPER_SHA256 = "90b98eff707bb69744f9bc9824424d13651aed26380a1aa71d02936434fbb8da"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1989_LIGHT_NATIVE_WLANMDSP_TRACE_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1936.configure_base()
    prev1936.OUT_DIR = OUT_DIR
    prev1936.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1936.REPORT_PATH = REPORT_PATH
    prev1936.prev1929.OUT_DIR = OUT_DIR
    prev1936.prev1929.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1936.prev1929.REPORT_PATH = REPORT_PATH
    prev1936.prev1929.prev1792.OUT_DIR = OUT_DIR
    prev1936.prev1929.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1936.prev1929.prev1792.REPORT_PATH = REPORT_PATH
    prev1936.prev1929.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1936.prev1929.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1936.prev1929.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1936.prev1929.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1936.prev1929.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1936.prev1929.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1936.prev1929.prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1989",
        "--decision",
        "v1989-light-native-wlanmdsp-trace-source-build-pass",
        "--cycle-label",
        "v1989",
        "--init-version",
        "0.9.177",
        "--init-build",
        "v1989-light-native-wlanmdsp-trace",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1989_light_native_wlanmdsp_trace"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v363"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1989_light_native_wlanmdsp_trace.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1989_light_native_wlanmdsp_trace.img"),
        "--wifi-test-klog-prefix",
        "A90v1989",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1989.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1989.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1989.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1989-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1989.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1989-supervisor.pid",
        "--wifi-test-watch-sec",
        "120",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "150",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-light-firmware-trace",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-post-pm-lower-state-observer",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1989 Light Native Wlanmdsp Trace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1989`",
        "- Type: source/build-only rollbackable internal-modem light `wlanmdsp.mbn` request/load trace artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1979/V1982 exhausted AP-side producer differences; this artifact keeps the current native PM/CNSS/tftp route but removes boot-time QRTR readback matrix, service-locator probing, and service-notifier listener probing so the next live run observes only the native firmware-request edge.",
        "- Manifest: `tmp/wifi/v1989-light-native-wlanmdsp-trace-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        f"- Light firmware trace: `{wifi['light_firmware_trace']}`",
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, firmware mounts, klog lower-window summaries, and libqmi/ICNSS read-only uprobes already present in helper v363.",
        "- Removed from init argv by contract: `--allow-qrtr-ns-readback`, `--allow-servloc-domain-list-probe`, `--allow-service-notifier-listener-probe`, and `--qrtr-readback-matrix wlfw:69:0,1`.",
        "- Live discriminator: whether native requests `wlanmdsp.mbn`, serves it, and reaches modem PIL/PD-load markers without boot-time QRTR matrix or multi-strace observer perturbation.",
        "- Stop condition: `wlanmdsp.mbn` request/serve/load, WLAN-PD UP, WLFW 69, BDF, or `wlan0`; do not proceed to Wi-Fi HAL/scan/connect.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
