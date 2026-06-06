#!/usr/bin/env python3
"""Build V1795 WLAN-PD PM-service count/sample observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1792 as prev1792


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1795-pm-service-count-sample-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1795/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1795_PM_SERVICE_COUNT_SAMPLE_OBSERVER_SOURCE_BUILD_2026-06-03.md"
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
        "V1795",
        "--decision",
        "v1795-pm-service-count-sample-observer-source-build-pass",
        "--cycle-label",
        "v1795",
        "--init-version",
        "0.9.148",
        "--init-build",
        "v1795-pm-service-count-sample-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1795_pm_service_count_sample_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v339"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1795_pm_service_count_sample_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1795_pm_service_count_sample_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1795",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1795.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1795.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1795.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1795-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1795.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1795-supervisor.pid",
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
        "# Native Init V1795 PM-service Count/Sample Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1795`",
        "- Type: source/build-only rollbackable WLAN-PD PM-service count/sample observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v339 keeps the V1792 PM register/devnode observers and adds value-ready PM-service count fetchargs plus per-event sample lines so the next live gate can capture first/second count values and every observed first-loop candidate string before any devnode repair.",
        "- Manifest: `tmp/wifi/v1795-pm-service-count-sample-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded V1792 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added observer only: PM-service count-load probes now fire after `x8` contains the count value, first/second add-call probes expose record/name/devnode fetchargs, and PM-service events emit up to four sampled trace lines.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Fetchargs",
        "",
        "- `pm_service_init_first_count_load` at `0x6bf4`: `first_count=%x8`",
        "- `pm_service_init_second_count_load` at `0x6cd8`: `second_count=%x8`",
        "- `pm_service_init_first_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`",
        "- `pm_service_init_second_add_peripheral_call`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string off_timeout=%x2 ack_timeout=%x3 flags=%x4`",
        "- PM-service event output now includes `sample_count` and `sample_line_0..3` for each `pm_server_uprobe` event.",
        "- Retained: `pm_server_register_no_peripheral`: `peripheral=+0(%x26):string`",
        "- Retained: `pm_service_add_peripheral_entry`: `record=%x1 name=+4(%x1):string devnode=+68(%x1):string`",
        "- Retained: `pm_service_add_peripheral_known_name`: `record=%x25 name=+0(%x21):string devnode=+68(%x25):string`",
        "- Retained: `pm_service_add_peripheral_init_fail`: `name=+0(%x21):string devnode=+0(%x25):string`",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- V1796 should run one rollbackable live gate with this artifact and classify the PM-service first-loop candidate set before any repair.",
        "- `modem-devnode-access-fail`: first count is at least `2`, sampled first-loop lines include `modem`, and list commit remains `0`.",
        "- `sdx50m-only-first-loop`: first count/hit samples show only `SDX50M`; return to sysfs/name reconstruction before repair.",
        "- `count-fetcharg-unavailable`: value-ready count fetchargs or sample lines fail to register/read; fall back to direct helper sysfs plus trace parser.",
        "- `list-commit-progress`: supported-list commit appears; stop and classify PM server register progression before any Wi-Fi HAL or repair cascade.",
        "- The gate remains one-run: do not autonomously chain into PM repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev1792.prev1790.prev1783.prev
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
