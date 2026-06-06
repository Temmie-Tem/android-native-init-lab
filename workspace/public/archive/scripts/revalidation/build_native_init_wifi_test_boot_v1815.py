#!/usr/bin/env python3
"""Build V1815 lower publication precondition klog observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1815-lower-publication-precondition-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1815/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1815_LOWER_PUBLICATION_PRECONDITION_SOURCE_BUILD_2026-06-03.md"
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
        "V1815",
        "--decision",
        "v1815-lower-publication-precondition-source-build-pass",
        "--cycle-label",
        "v1815",
        "--init-version",
        "0.9.155",
        "--init-build",
        "v1815-lower-publication-precondition",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1815_lower_publication_precondition"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v346"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1815_lower_publication_precondition.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1815_lower_publication_precondition.img"),
        "--wifi-test-klog-prefix",
        "A90v1815",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1815.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1815.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1815.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1815-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1815.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1815-supervisor.pid",
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
        "# Native Init V1815 Lower Publication Precondition Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1815`",
        "- Type: source/build-only rollbackable WLAN-PD lower publication precondition klog observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v346 keeps the service74 raw-klog route and adds read-only raw counters/last lines for `pd-mapper`, `subsys`, `pil`, `qmi`, `wlfw`, and `wlan_pd` precondition surfaces.",
        "- Manifest: `tmp/wifi/v1815-lower-publication-precondition-test-boot/manifest.json`",
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
        "- Base route remains the V1813 bounded lower handoff observer: PM-client return fetchargs, lower-state samples, service-notifier listener, and raw service-notifier 180/74 klog samples.",
        "- Added precondition counters: `raw_count_pd_mapper_text`, `raw_count_subsys_text`, `raw_count_pil_text`, `raw_count_qmi_text`, and `raw_count_wlfw_text`, plus `last_wlan_pd`, `last_pd_mapper`, `last_subsys`, `last_pil`, `last_qmi`, and `last_wlfw`.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1816 should run one rollbackable live gate with this artifact and classify which lower publication precondition is still visible before the missing service 74/wlan_pd continuation.",
        "- `service74-raw-absent-preconditions-visible`: service 180, qmi/sysmon, and lower precondition klogs are visible, but service 74/wlan_pd remain absent.",
        "- `precondition-parser-gap`: raw precondition text appears only in broad counters without useful last-line attribution.",
        "- `lower-publication-progress`: service 74, wlan_pd, WLFW service 69, MHI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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
