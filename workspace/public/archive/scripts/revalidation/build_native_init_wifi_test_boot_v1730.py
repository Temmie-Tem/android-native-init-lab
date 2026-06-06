#!/usr/bin/env python3
"""Build V1730 WLAN-PD service-notifier late listener test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1730-wlan-pd-servnotif-late-listener-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1730/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1730_WLAN_PD_SERVNOTIF_LATE_LISTENER_SOURCE_BUILD_2026-06-03.md"
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
        "V1730",
        "--decision",
        "v1730-wlan-pd-servnotif-late-listener-source-build-pass",
        "--cycle-label",
        "v1730",
        "--init-version",
        "0.9.138",
        "--init-build",
        "v1730-wlan-pd-servnotif-late-listener",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1730_wlan_pd_servnotif_late_listener"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v325"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1730_wlan_pd_servnotif_late_listener.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1730_wlan_pd_servnotif_late_listener.img"),
        "--wifi-test-klog-prefix",
        "A90v1730",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1730.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1730.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1730.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1730-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1730.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1730-supervisor.pid",
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
        "wlan-pd-service-window-trigger",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1730-servnotif-late-listener-property-runtime-ready"
        if pass_ok
        else "v1730-servnotif-late-listener-property-runtime-blocked"
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
        "# Native Init V1730 WLAN-PD Service-notifier Late Listener Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1730`",
        "- Type: source/build-only rollbackable WLAN-PD service-notifier late listener test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: carries V1729 forward and adds a late service-notifier listener register after the endpoint appears.",
        "- Manifest: `tmp/wifi/v1730-wlan-pd-servnotif-late-listener-test-boot/manifest.json`",
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
        "- Added evidence: `wifi_companion_service_notifier_late_listener.*` plus the V1729 `wifi_companion_service_notifier_late_probe.*` endpoint lookup.",
        "- No PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `late-listener-response-success` means the late service-notifier listener returned a QMI success response.",
        "- `late-listener-uninit-no-indication` means the listener response remains `uninit` and no state indication arrives in the bounded hold.",
        "- `late-listener-no-response` means the endpoint appeared but did not answer the register-listener request.",
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
