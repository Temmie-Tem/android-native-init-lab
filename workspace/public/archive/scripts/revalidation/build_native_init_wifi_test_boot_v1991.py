#!/usr/bin/env python3
"""Build V1991 RFS-bridge light native wlanmdsp trace test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1989 as prev1989


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1991-rfs-bridge-wlanmdsp-trace-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1991/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v365"
EXPECTED_HELPER_SHA256 = "30b117398401c5ab809d40494c997d22488117f2c66cdb3f5764ada27139073c"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1991_RFS_BRIDGE_WLANMDSP_TRACE_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1989.configure_base()
    prev1989.OUT_DIR = OUT_DIR
    prev1989.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.REPORT_PATH = REPORT_PATH
    prev1989.prev1936.OUT_DIR = OUT_DIR
    prev1989.prev1936.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.prev1936.REPORT_PATH = REPORT_PATH
    prev1989.prev1936.prev1929.OUT_DIR = OUT_DIR
    prev1989.prev1936.prev1929.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.prev1936.prev1929.REPORT_PATH = REPORT_PATH
    prev1989.prev1936.prev1929.prev1792.OUT_DIR = OUT_DIR
    prev1989.prev1936.prev1929.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.prev1936.prev1929.prev1792.REPORT_PATH = REPORT_PATH
    prev1989.prev1936.prev1929.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1989.prev1936.prev1929.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.prev1936.prev1929.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1991",
        "--decision",
        "v1991-rfs-bridge-wlanmdsp-trace-source-build-pass",
        "--cycle-label",
        "v1991",
        "--init-version",
        "0.9.178",
        "--init-build",
        "v1991-rfs-bridge-wlanmdsp-trace",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1991_rfs_bridge_wlanmdsp_trace"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v365"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1991_rfs_bridge_wlanmdsp_trace.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1991_rfs_bridge_wlanmdsp_trace.img"),
        "--wifi-test-klog-prefix",
        "A90v1991",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1991.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1991.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1991.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1991-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1991.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1991-supervisor.pid",
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
        "# Native Init V1991 RFS Bridge Wlanmdsp Trace Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1991`",
        "- Type: source/build-only rollbackable internal-modem light `wlanmdsp.mbn` RFS bridge trace artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v365 adds a namespace-local `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` bridge to the read-only `/vendor/firmware/wlanmdsp.mbn` asset without writing sda29, while preserving the V1989 light observer contract.",
        "- Manifest: `tmp/wifi/v1991-rfs-bridge-wlanmdsp-trace-test-boot/manifest.json`",
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
        "- Kept: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, `rmt_storage`, `tftp_server`, firmware mounts, klog lower-window summaries, and libqmi/ICNSS read-only uprobes.",
        "- Added: namespace-local RFS bridge over the existing vendor RFS mountpoint so the Android tftp path `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` resolves to the read-only `/vendor/firmware/wlanmdsp.mbn` asset.",
        "- Still removed from init argv: `--allow-qrtr-ns-readback`, `--allow-servloc-domain-list-probe`, `--allow-service-notifier-listener-probe`, and `--qrtr-readback-matrix wlfw:69:0,1`.",
        "- Live discriminator: after exact-path bridge confirmation, classify requested+served+UP, not-requested, or requested+served+still-down.",
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
    base = prev1989.prev1936.prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
