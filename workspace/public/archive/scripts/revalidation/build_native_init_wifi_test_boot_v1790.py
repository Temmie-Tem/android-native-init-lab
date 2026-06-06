#!/usr/bin/env python3
"""Build V1790 WLAN-PD PM-service devnode string observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1783 as prev1783


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1790-pm-service-devnode-string-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1790/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1790_PM_SERVICE_DEVNODE_STRING_OBSERVER_SOURCE_BUILD_2026-06-03.md"
)


def configure_base() -> None:
    prev1783.configure_base()
    prev1783.V1783_OUT = OUT_DIR
    prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1790",
        "--decision",
        "v1790-pm-service-devnode-string-observer-source-build-pass",
        "--cycle-label",
        "v1790",
        "--init-version",
        "0.9.146",
        "--init-build",
        "v1790-pm-service-devnode-string-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1790_pm_service_devnode_string_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v337"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1790_pm_service_devnode_string_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1790_pm_service_devnode_string_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1790",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1790.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1790.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1790.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1790-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1790.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1790-supervisor.pid",
        "--wifi-test-watch-sec",
        "75",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "105",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-service-object-visible-trigger",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1790 PM-service Devnode String Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1790`",
        "- Type: source/build-only rollbackable WLAN-PD PM-service devnode string observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v337 keeps the V1787 route and adds tracefs fetchargs to the PM-service add-peripheral entry, known-name, and init-fail uprobes so the next live gate can capture discovered candidate names and `/dev/subsys_*` devnode strings before any repair.",
        "- Manifest: `tmp/wifi/v1790-pm-service-devnode-string-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded V1787 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added observer only: PM-service add-peripheral tracefs fetchargs record the candidate record pointer, name, and devnode string in `first_hit_line` for the entry, known-name, and init-fail probes.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Fetchargs",
        "",
        "- `pm_service_add_peripheral_entry`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`",
        "- `pm_service_add_peripheral_known_name`: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`",
        "- `pm_service_add_peripheral_init_fail`: `name=+0(%x21):string devnode=+0(%x25):string`",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- V1791 should run one rollbackable live gate with this artifact and classify the exact candidate/devnode strings that fail `access(F_OK)`.",
        "- If the strings show a missing private `/dev/subsys_modem` path, the next separately scoped repair can materialize read-only private devnode parity for PM-service discovery.",
        "- If the strings show `/dev/subsys_esoc0` or another eSoC path, stop and classify host-only before any live repair; do not open the path blindly.",
        "- The gate remains one-run: do not autonomously chain into PM repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev1783.prev.render_report = render_report
    return prev1783.prev.main()


if __name__ == "__main__":
    raise SystemExit(main())
