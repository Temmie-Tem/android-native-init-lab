#!/usr/bin/env python3
"""Build V1787 WLAN-PD PM service init-discovery observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1783 as prev1783


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1787-pm-service-init-discovery-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1787/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1787_PM_SERVICE_INIT_DISCOVERY_OBSERVER_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_RENDER_REPORT = prev1783.render_report


def configure_base() -> None:
    prev1783.configure_base()
    prev1783.V1783_OUT = OUT_DIR
    prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1787",
        "--decision",
        "v1787-pm-service-init-discovery-observer-source-build-pass",
        "--cycle-label",
        "v1787",
        "--init-version",
        "0.9.145",
        "--init-build",
        "v1787-pm-service-init-discovery-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1787_pm_service_init_discovery_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v336"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1787_pm_service_init_discovery_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1787_pm_service_init_discovery_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1787",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1787.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1787.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1787.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1787-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1787.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1787-supervisor.pid",
        "--wifi-test-watch-sec",
        "75",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "105",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-object-visible-trigger",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1787 PM Service Init-discovery Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1787`",
        "- Type: source/build-only rollbackable WLAN-PD PM-service init-discovery observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v336 extends the V1783 PM server observer with `pm-service` init/discovery uprobes for `get_system_info`, add-peripheral calls, and supported-list insertion before Binder registration.",
        "- Manifest: `tmp/wifi/v1787-pm-service-init-discovery-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded V1783 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added observer only: `pm-service` main/list init, `get_system_info`, first/second add-peripheral calls, add-peripheral list commit, and pre-Binder init-done uprobes.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- `pm_service_init_get_system_info_call.hit_count > 0` proves PM service discovery was reached.",
        "- `pm_service_add_peripheral_list_commit.hit_count > 0` proves supported-list population before Binder registration.",
        "- `pm_service_init_get_system_info_call.hit_count > 0` with zero list commits identifies a discovery namespace/input gap.",
        "- The gate remains one-run: do not autonomously chain into PM repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev1783.prev.render_report = render_report
    return prev1783.prev.main()


if __name__ == "__main__":
    raise SystemExit(main())
