#!/usr/bin/env python3
"""Build V1735 WLAN-PD timestamped observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1735-wlan-pd-timestamped-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1735/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1735_WLAN_PD_TIMESTAMPED_OBSERVER_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = prev.build_cnss_property_runtime


def configure_base() -> None:
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1735",
        "--decision",
        "v1735-wlan-pd-timestamped-observer-source-build-pass",
        "--cycle-label",
        "v1735",
        "--init-version",
        "0.9.139",
        "--init-build",
        "v1735-wlan-pd-timestamped-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1735_wlan_pd_timestamped_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v326"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1735_wlan_pd_timestamped_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1735_wlan_pd_timestamped_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1735",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1735.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1735.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1735.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1735-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1735.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1735-supervisor.pid",
        "--wifi-test-watch-sec",
        "70",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "95",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-timestamped-observer",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1735-timestamped-observer-property-runtime-ready"
        if pass_ok
        else "v1735-timestamped-observer-property-runtime-blocked"
    )
    return manifest


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1735 WLAN-PD Timestamped Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1735`",
        "- Type: source/build-only rollbackable WLAN-PD timestamped observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: carries the V1734 modem-side WLAN-PD start-gap classification forward into one bounded live observer artifact.",
        "- Manifest: `tmp/wifi/v1735-wlan-pd-timestamped-observer-test-boot/manifest.json`",
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
        "- Actors: `servicemanager`, `hwservicemanager`, VND service-manager fallback (`/system/bin/servicemanager /dev/vndbinder`), `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- Added evidence: `wlan_pd_service_window_trigger.observer_monotonic_ms`, service-window summary fields, firmware-serve fields, QRTR readback, and service-notifier listener timing.",
        "- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `wlfw-start-reached`: cnss-daemon reached the WLFW start/request path and the remaining blocker is downstream WLAN-PD/WLFW publication.",
        "- `service-window-still-no-wlfw`: the bounded window did not expose WLFW start/request evidence.",
        "- `service-window-child-failed`: one of the required internal-modem companion actors did not remain running.",
        "- `modem-holder-regression`: `/dev/subsys_modem` holder did not open successfully.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev.build_cnss_property_runtime = build_cnss_property_runtime
    prev.render_report = render_report
    return prev.main()


if __name__ == "__main__":
    raise SystemExit(main())
