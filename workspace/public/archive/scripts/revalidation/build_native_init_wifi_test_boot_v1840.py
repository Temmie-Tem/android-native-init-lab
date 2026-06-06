#!/usr/bin/env python3
"""Build V1840 current-route PM callback/ack observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1840-pm-callback-ack-current-route-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1840/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1840_PM_CALLBACK_ACK_CURRENT_ROUTE_SOURCE_BUILD_2026-06-03.md"
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
        "V1840",
        "--decision",
        "v1840-pm-callback-ack-current-route-source-build-pass",
        "--cycle-label",
        "v1840",
        "--init-version",
        "0.9.163",
        "--init-build",
        "v1840-pm-callback-ack-current-route",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1840_pm_callback_ack_current_route"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v354"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1840_pm_callback_ack_current_route.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1840_pm_callback_ack_current_route.img"),
        "--wifi-test-klog-prefix",
        "A90v1840",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1840.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1840.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1840.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1840-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1840.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1840-supervisor.pid",
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
        "# Native Init V1840 PM Callback/Ack Current-route Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1840`",
        "- Type: source/build-only rollbackable current-route PM callback/ack observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v354 keeps the V1838 lower-continuation sampler and adds read-only current-route `libperipheral_client.so` uprobe hit counts for PM callback/transact and PM acknowledge branch offsets.",
        "- Manifest: `tmp/wifi/v1840-pm-callback-ack-current-route-test-boot/manifest.json`",
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
        "- Base route remains the bounded WLAN-PD post-PM lower observer from V1838, including PMIC/GDSC focus samples and inherited bounded QRTR/QMI probes.",
        "- Added current-route peripheral uprobe hit-count labels: `periph_pm_callback_stub_entry`, `periph_pm_callback_write_state`, `periph_pm_callback_remote_binder`, `periph_pm_callback_transact_call`, `periph_pm_callback_transact_return`, `periph_pm_client_ack_entry`, `periph_pm_client_ack_match`, `periph_pm_client_ack_virtual_call`, `periph_pm_server_ontransact_entry`, `periph_pm_server_ack_read_state`, `periph_pm_server_ack_impl_call`, and `periph_pm_server_ack_write_ret`.",
        "- These additions reuse the existing `wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.*` reporting path and record registration, enablement, hit count, and first-hit line only.",
        "- Explicit limitation: current helper peripheral uprobe records are entry-probe hit counters without fetch-arg decoding or uretprobe return decoding.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1841 should run one rollbackable live gate with this artifact only if current-route callback/ack hit counting is accepted as the next read-only target.",
        "- `callback-ack-absent-current-route`: PM list/register/connect still succeed, but callback/ack branch hit counts remain zero and lower state remains static.",
        "- `callback-ack-present-no-powerup`: callback/transact/ack branch hit counts appear, but powerup thread count, inferred eSoC open, mdm-status IRQ, MHI, WLFW service 69, and `wlan0` stay absent.",
        "- `powerup-or-wlfw-progress`: powerup thread, inferred eSoC open, mdm-status IRQ, MHI, WLFW service 69, service74/WLAN-PD UP, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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
