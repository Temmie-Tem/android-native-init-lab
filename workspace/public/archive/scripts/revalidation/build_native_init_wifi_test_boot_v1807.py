#!/usr/bin/env python3
"""Build V1807 WLAN-PD PM-client return fetcharg observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1807-pm-client-return-fetchargs-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1807/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1807_PM_CLIENT_RETURN_FETCHARGS_SOURCE_BUILD_2026-06-03.md"
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
        "V1807",
        "--decision",
        "v1807-pm-client-return-fetchargs-source-build-pass",
        "--cycle-label",
        "v1807",
        "--init-version",
        "0.9.152",
        "--init-build",
        "v1807-pm-client-return-fetchargs",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1807_pm_client_return_fetchargs"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v343"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1807_pm_client_return_fetchargs.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1807_pm_client_return_fetchargs.img"),
        "--wifi-test-klog-prefix",
        "A90v1807",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1807.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1807.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1807.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1807-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1807.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1807-supervisor.pid",
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
        "# Native Init V1807 PM-client Return Fetchargs Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1807`",
        "- Type: source/build-only rollbackable WLAN-PD PM-client return fetcharg observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v343 keeps the V1805 lower-state observer route and adds tracefs fetchargs for `cnss-daemon` PM-client register/connect return paths.",
        "- Manifest: `tmp/wifi/v1807-pm-client-return-fetchargs-test-boot/manifest.json`",
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
        "- Base route remains the V1805 bounded lower-state observer: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, private `/dev` projection for only `subsys_esoc0` and `subsys_modem`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`, service-notifier listener, and compact lower-state samples.",
        "- Added fetchargs: `pm_init_pm_client_register_call` captures raw argument registers, `pm_init_pm_client_register_retcheck` captures `rc=%x0`, `pm_init_pm_client_connect_call` captures raw argument registers, `pm_init_pm_client_connect_retcheck` captures `rc=%x0`, and `pm_init_return_path` captures `rc=%x0`.",
        "- The next live discriminator should decide whether PM client register/connect returns success while mdm3 still stays `OFFLINING`, or whether a non-zero PM client return is the immediate blocker.",
        "- Still excluded: direct `/dev/subsys_esoc0` open, fake-ONLINE, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC writes, `boot_wlan`, restart-PD request, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Expected Live Discriminator",
        "",
        "- V1808 should run one rollbackable live gate with this artifact and classify PM-client return values plus the lower-state samples.",
        "- `pm-client-return-success-still-offlining`: PM register/connect returns are zero, PM vote boundary is reached, and mdm3 remains `OFFLINING` with no MHI/WLFW/wlan0 progress.",
        "- `pm-client-return-error`: PM register/connect return fetchargs show a non-zero return; stop before any repair.",
        "- `lower-progress`: mdm3 leaves `OFFLINING`, mdm status IRQ increases, MHI appears, WLFW service 69 appears, or `wlan0` appears; stop before Wi-Fi HAL/scan/connect.",
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
