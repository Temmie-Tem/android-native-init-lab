#!/usr/bin/env python3
"""Build V1924 WLFW client-wait observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1924-wlfw-client-wait-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1924/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v360"
EXPECTED_HELPER_SHA256 = "5e2ef4c3923d0efd6d52f19e7844b646bc907a18441e7efd2cb0d84bb0fcb524"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1924_WLFW_CLIENT_WAIT_OBSERVER_SOURCE_BUILD_2026-06-04.md"
)

WLFW_CLIENT_WAIT_LABELS = [
    "wlfw_client_init_instance_call",
    "wlfw_client_init_instance_retcheck",
    "wlfw_client_init_instance_fail_log",
    "wlfw_register_error_cb_call",
    "wlfw_register_error_cb_retcheck",
    "wlfw_get_service_instance_call",
    "wlfw_get_service_instance_retcheck",
    "wlfw_get_instance_id_call",
    "wlfw_get_instance_id_retcheck",
    "wlfw_send_ind_register_entry",
    "wlfw_fw_mem_cond_wait",
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
        "V1924",
        "--decision",
        "v1924-wlfw-client-wait-observer-source-build-pass",
        "--cycle-label",
        "v1924",
        "--init-version",
        "0.9.173",
        "--init-build",
        "v1924-wlfw-client-wait-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1924_wlfw_client_wait_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v360"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1924_wlfw_client_wait_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1924_wlfw_client_wait_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1924",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1924.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1924.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1924.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1924-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1924.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1924-supervisor.pid",
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
    labels = ", ".join(f"`{label}`" for label in WLFW_CLIENT_WAIT_LABELS)
    return "\n".join([
        "# Native Init V1924 WLFW Client-wait Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1924`",
        "- Type: source/build-only rollbackable internal-modem WLFW client-wait observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1923 localized the blocker to post-`wlfw_service_request` WLFW service availability; helper v360 adds read-only uprobes around WLFW QMI client initialization and service-instance lookup before the first indication/capability QMI send.",
        "- Manifest: `tmp/wifi/v1924-wlfw-client-wait-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded internal-modem post-PM lower observer used by V1846/V1920: firmware mounts, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-locator/domain-list, service-notifier listener, and WLFW QRTR readback.",
        "- Added WLFW worker labels: " + labels + ".",
        "- New label selection distinguishes blocking in `qmi_client_init_instance`, `qmi_client_get_service_instance`, instance-id lookup, ind-register entry-before-QMI, and the FW-memory condition wait.",
        "- Stop condition: WLFW service 69, `wlan_pd`, requested `wlanmdsp`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `wlfw-worker-blocked-in-qmi-client-init-instance`: worker enters `qmi_client_init_instance` and does not return while WLFW69 remains absent.",
        "- `wlfw-worker-blocked-in-get-service-instance`: client init returns and service-instance lookup blocks while WLFW69 remains absent.",
        "- `wlfw-worker-service-instance-returned-before-instance-id`: lookup returns but the instance-id path does not progress.",
        "- `wlfw-worker-entered-ind-register-before-qmi-send`: `wlfw_send_ind_register_req` entry fires but the QMI send at `0xf32c` does not.",
        "- `wlfw-worker-thread-started-qmi-ind-register-sent`: first WLFW QMI send progressed; stop and classify the new downstream state before BDF/HAL work.",
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
