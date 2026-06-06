#!/usr/bin/env python3
"""Build V1936 ICNSS IPC/WLFW-server-arrive observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1929 as prev1929


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1936-icnss-ipc-service69-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1936/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v363"
EXPECTED_HELPER_SHA256 = "90b98eff707bb69744f9bc9824424d13651aed26380a1aa71d02936434fbb8da"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1936_ICNSS_IPC_SERVICE69_OBSERVER_SOURCE_BUILD_2026-06-04.md"
)


def configure_base() -> None:
    prev1929.configure_base()
    prev1929.OUT_DIR = OUT_DIR
    prev1929.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1929.REPORT_PATH = REPORT_PATH
    prev1929.prev1792.OUT_DIR = OUT_DIR
    prev1929.prev1792.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1929.prev1792.REPORT_PATH = REPORT_PATH
    prev1929.prev1792.prev1790.OUT_DIR = OUT_DIR
    prev1929.prev1792.prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1929.prev1792.prev1790.REPORT_PATH = REPORT_PATH
    prev1929.prev1792.prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1929.prev1792.prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1929.prev1792.prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1929.prev1792.prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1936",
        "--decision",
        "v1936-icnss-ipc-service69-observer-source-build-pass",
        "--cycle-label",
        "v1936",
        "--init-version",
        "0.9.176",
        "--init-build",
        "v1936-icnss-ipc-service69-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1936_icnss_ipc_service69_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v363"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1936_icnss_ipc_service69_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1936_icnss_ipc_service69_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1936",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1936.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1936.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1936.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1936-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1936.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1936-supervisor.pid",
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
    return "\n".join([
        "# Native Init V1936 ICNSS IPC Service69 Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1936`",
        "- Type: source/build-only rollbackable internal-modem ICNSS IPC/WLFW-server-arrive observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: V1935 localized the native stall to the WLFW service69 wait-return edge; helper v363 keeps the V1929 libqmi service-ID route and adds read-only ICNSS IPC/debugfs summaries at the post-PM phases.",
        "- Manifest: `tmp/wifi/v1936-icnss-ipc-service69-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded internal-modem post-PM lower observer: clean-DSP companion, service managers, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-locator/domain-list, service-notifier listener, WLFW QRTR readback, and libqmi service-ID uprobes.",
        "- Added read-only prefix: `wlan_pd_icnss_ipc_snapshot.<phase>.*` for `/sys/kernel/debug/ipc_logging`, `/proc/ipc_logging`, and `/sys/kernel/debug/icnss/stats` at `after_holder_start`, `after_early_listener`, and `after_post_listener_window`.",
        "- The new discriminator checks for Android-good comparator edges: `Get service notify`, `msm/modem/wlan_pd`, `PD notification registration happened`, and `WLFW server arrive` before WLFW service69 wait return.",
        "- Stop condition: WLFW service 69, `wlan_pd`, requested `wlanmdsp`, `wlfw_ind_register_qmi`, `wlfw_cap_qmi`, or `wlan0` appears; do not proceed to HAL/scan/connect in this unit.",
        "- Excluded by construction: private SDX50M mount, `/dev/subsys_esoc0` open, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- `native-icnss-ipc-wlfw-server-arrive-gap`: native reproduces service74/180, PM open, holder, WLFW lookup69, and libqmi wait, but ICNSS IPC/debugfs has no `WLFW server arrive` and service69 wait does not return.",
        "- `native-icnss-ipc-pd-registration-no-wlfw-arrive`: native records `msm/modem/wlan_pd` or PD notification registration but never records `WLFW server arrive`; focus next on the post-registration modem-to-WLFW publication edge.",
        "- `native-icnss-ipc-unreadable`: debugfs IPC and ICNSS stats are absent/unreadable in the rollbackable test boot; fall back to userland libqmi/servnotif-only observers.",
        "- `lower-publication-progress`: service69, WLAN-PD, `wlanmdsp`, WLFW QMI, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect and classify the new downstream state.",
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
    base = prev1929.prev1792.prev1790.prev1783.prev
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
