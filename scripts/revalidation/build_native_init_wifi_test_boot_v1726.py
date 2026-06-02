#!/usr/bin/env python3
"""Build V1726 WLAN-PD service-manager-only bootstrap test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1726-wlan-pd-service-manager-bootstrap-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1726/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1726_WLAN_PD_SERVICE_MANAGER_BOOTSTRAP_SOURCE_BUILD_2026-06-03.md"
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
        "V1726",
        "--decision",
        "v1726-wlan-pd-service-manager-bootstrap-source-build-pass",
        "--cycle-label",
        "v1726",
        "--init-version",
        "0.9.136",
        "--init-build",
        "v1726-wlan-pd-service-manager-bootstrap",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1726_wlan_pd_service_manager_bootstrap"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v323"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1726_wlan_pd_service_manager_bootstrap.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1726_wlan_pd_service_manager_bootstrap.img"),
        "--wifi-test-klog-prefix",
        "A90v1726",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1726.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1726.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1726.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1726-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1726.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1726-supervisor.pid",
        "--wifi-test-watch-sec",
        "55",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "80",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-window-trigger",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1726-service-manager-bootstrap-property-runtime-ready"
        if pass_ok
        else "v1726-service-manager-bootstrap-property-runtime-blocked"
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
        "# Native Init V1726 WLAN-PD Service-manager Bootstrap Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1726`",
        "- Type: source/build-only rollbackable WLAN-PD service-manager-only bootstrap test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: carries V1725's corrected internal-modem route forward, but switches the next bounded gate to the minimal vendor Binder service-manager bootstrap proven necessary by V1719/V1720.",
        "- Manifest: `tmp/wifi/v1726-wlan-pd-service-manager-bootstrap-test-boot/manifest.json`",
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
        "- Added evidence: `wlan_pd_cnss_nonlog_control_flow.service_manager=1` plus existing CNSS/WLFW/peripheral uprobes.",
        "- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `peripheral-service-name-built-no-get` or a later peripheral label means vendor Binder service-manager acquisition progressed beyond the V1719 blocker.",
        "- `peripheral-default-service-manager-call-no-return` means the service-manager-only bootstrap did not move the blocker.",
        "- `cnss-target-unavailable` means the CNSS target could not be observed and the live gate must be treated as non-diagnostic.",
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
