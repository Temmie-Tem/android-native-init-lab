#!/usr/bin/env python3
"""Build V1810 WLAN-PD post-PM lower handoff klog observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1810-post-pm-lower-handoff-klog-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1810/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1810_POST_PM_LOWER_HANDOFF_KLOG_SOURCE_BUILD_2026-06-03.md"
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
        "V1810",
        "--decision",
        "v1810-post-pm-lower-handoff-klog-source-build-pass",
        "--cycle-label",
        "v1810",
        "--init-version",
        "0.9.153",
        "--init-build",
        "v1810-post-pm-lower-handoff-klog",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1810_post_pm_lower_handoff_klog"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v344"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1810_post_pm_lower_handoff_klog.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1810_post_pm_lower_handoff_klog.img"),
        "--wifi-test-klog-prefix",
        "A90v1810",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1810.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1810.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1810.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1810-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1810.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1810-supervisor.pid",
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
        "# Native Init V1810 Post-PM Lower Handoff Klog Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1810`",
        "- Type: source/build-only rollbackable WLAN-PD post-PM lower handoff klog observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v344 keeps the V1807 PM-client return fetcharg and lower-state observer route, then adds read-only service-notifier 180/74 plus `sysmon_qmi` klog samples at the post-PM lower handoff.",
        "- Manifest: `tmp/wifi/v1810-post-pm-lower-handoff-klog-test-boot/manifest.json`",
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
        "- Base route remains the V1807 bounded lower-state observer: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, private `/dev` projection for only `subsys_esoc0` and `subsys_modem`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-notifier listener, compact lower-state samples, and PM-client register/connect return fetchargs.",
        "- Added klog samples: `wlan_pd_post_pm_lower_handoff_klog.after_holder_start`, `after_early_listener`, and `after_post_listener_window` report `sysmon_qmi`, service-notifier 180, and service-notifier 74 counts plus last-line snapshots.",
        "- The samples are read-only syslog scans through the existing service74 klog parser; they do not request `boot_wlan`, restart PDs, spoof modem state, open `/dev/subsys_esoc0`, or touch PMIC/GPIO/GDSC controls.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1811 should run one rollbackable live gate with this artifact and classify whether service-notifier klog 180/74 progress appears below the PM-client success boundary.",
        "- `servnotif-klog-absent`: PM-client returns stay zero, mdm3 remains `OFFLINING`, and service-notifier 180/74 counts do not advance.",
        "- `servnotif-klog-progress-still-uninit`: service-notifier 180/74 or `sysmon_qmi` klog counts advance while the QRTR service-notifier endpoint state remains `uninit`.",
        "- `lower-progress`: mdm3 leaves `OFFLINING`, mdm status IRQ increases, MHI appears, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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
