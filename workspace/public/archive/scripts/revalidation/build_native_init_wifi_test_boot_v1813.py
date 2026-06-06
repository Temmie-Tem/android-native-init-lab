#!/usr/bin/env python3
"""Build V1813 service-notifier 74 raw klog observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1813-service74-raw-klog-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1813/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1813_SERVICE74_RAW_KLOG_SOURCE_BUILD_2026-06-03.md"
)


def configure_base() -> None:
    prev1792.configure_base()
    prev1792.OUT_DIR = OUT_DIR
    prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1813",
        "--decision",
        "v1813-service74-raw-klog-source-build-pass",
        "--cycle-label",
        "v1813",
        "--init-version",
        "0.9.154",
        "--init-build",
        "v1813-service74-raw-klog",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1813_service74_raw_klog"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v345"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1813_service74_raw_klog.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1813_service74_raw_klog.img"),
        "--wifi-test-klog-prefix",
        "A90v1813",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1813.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1813.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1813.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1813-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1813.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1813-supervisor.pid",
        "--wifi-test-watch-sec",
        "90",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "120",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
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
        "# Native Init V1813 Service-notifier 74 Raw Klog Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1813`",
        "- Type: source/build-only rollbackable WLAN-PD service-notifier 74 raw klog observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v345 keeps the V1810/V1811 post-PM lower handoff route and adds raw service-notifier klog pattern counters plus the last service-notifier 180 line.",
        "- Manifest: `tmp/wifi/v1813-service74-raw-klog-test-boot/manifest.json`",
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
        "- Base route remains the V1810 bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener, and read-only post-PM klog samples.",
        "- Added raw klog counters: `raw_count_service_notifier_colon`, `raw_count_service_notifier_new_server`, `raw_count_qmi_handle`, `raw_count_180_service_text`, `raw_count_74_service_text`, and `raw_count_wlan_pd_text`.",
        "- Added raw line snapshots: `last_180` and existing `last_74`, so the next live gate can distinguish missing service 74 publication from an overly narrow parser.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1814 should run one rollbackable live gate with this artifact and classify whether raw service-notifier 74 text is absent or present-but-not-matched by the exact parser.",
        "- `service74-raw-absent`: exact service 74 count and raw `74 service` text remain zero while service 180 remains present.",
        "- `service74-parser-miss`: raw `74 service` text is present but exact service 74 count remains zero.",
        "- `service74-progress`: exact service 74 count appears, service-notifier state changes, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
        "- `safety-regression`: any forbidden side effect appears; stop and roll back.",
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
    base = prev1792.prev1790.prev1783.prev
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
