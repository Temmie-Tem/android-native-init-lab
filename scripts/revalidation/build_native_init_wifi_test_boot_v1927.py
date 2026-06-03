#!/usr/bin/env python3
"""Build V1927 libqmi CCI service-wait observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1927-libqmi-cci-uprobe-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1927/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v361"
EXPECTED_HELPER_SHA256 = "619c900346b83bcbf3f9588990812d9e62f7df7bdea85bb4ca0ab788bf7e37a6"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1927_LIBQMI_CCI_UPROBE_OBSERVER_SOURCE_BUILD_2026-06-04.md"
)

LIBQMI_LABELS = [
    "libqmi_client_init_instance_entry",
    "libqmi_initial_get_service_instance_ret",
    "libqmi_initial_client_init_ret",
    "libqmi_notifier_init_call",
    "libqmi_notifier_init_ret",
    "libqmi_wait_call",
    "libqmi_wait_return",
    "libqmi_loop_get_service_instance_ret",
    "libqmi_loop_client_init_ret",
    "libqmi_init_timeout_path",
    "libqmi_init_return",
    "libqmi_signal_wait_entry",
    "libqmi_signal_wait_timedwait",
    "libqmi_signal_wait_timeout_store",
    "libqmi_xport_new_server_entry",
    "libqmi_xport_new_server_signal",
]


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
        "V1927",
        "--decision",
        "v1927-libqmi-cci-uprobe-observer-source-build-pass",
        "--cycle-label",
        "v1927",
        "--init-version",
        "0.9.174",
        "--init-build",
        "v1927-libqmi-cci-uprobe-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1927_libqmi_cci_uprobe_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v361"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1927_libqmi_cci_uprobe_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1927_libqmi_cci_uprobe_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1927",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1927.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1927.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1927.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1927-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1927.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1927-supervisor.pid",
        "--wifi-test-watch-sec",
        "120",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "150",
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
    labels = ", ".join(f"`{label}`" for label in LIBQMI_LABELS)
    return "\n".join([
        "# Native Init V1927 Libqmi CCI Uprobe Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1927`",
        "- Type: source/build-only rollbackable internal-modem libqmi CCI observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1925 localized the live stall inside `qmi_client_init_instance`; V1926 mapped the libqmi wait loop; helper v361 adds a separate read-only `libqmi_cci.so` uprobe target group.",
        "- Manifest: `tmp/wifi/v1927-libqmi-cci-uprobe-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded internal-modem post-PM lower observer: clean firmware mounts, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-locator/domain-list, service-notifier listener, and WLFW QRTR readback.",
        "- Added libqmi labels: " + labels + ".",
        "- New discriminator separates wait-loop entry, notifier setup, service-list retry, timeout return, and transport new-server wake edges.",
        "- Stop condition: WLFW service 69, `wlan_pd`, requested `wlanmdsp`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `qmi-client-init-instance-waiting-no-new-server`: WLFW worker is blocked in libqmi wait and no libqmi new-server edge arrived.",
        "- `qmi-client-init-instance-new-server-no-wake`: libqmi saw a new-server edge but the wait loop did not wake/progress.",
        "- `qmi-client-init-instance-timeout`: timeout path at `libqmi_cci.so+0x7954` hit.",
        "- `qmi-client-init-instance-returned`: libqmi returned; classify the caller/downstream state before any HAL work.",
        "- `safety-regression`: any hard-stop side effect appears; stop and roll back.",
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
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
