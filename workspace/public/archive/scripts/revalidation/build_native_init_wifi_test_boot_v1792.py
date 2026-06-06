#!/usr/bin/env python3
"""Build V1792 WLAN-PD PM register request string observer test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1790 as prev1790


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1792-pm-register-request-string-observer-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1792/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1792_PM_REGISTER_REQUEST_STRING_OBSERVER_SOURCE_BUILD_2026-06-03.md"
)


def configure_base() -> None:
    prev1790.configure_base()
    prev1790.OUT_DIR = OUT_DIR
    prev1790.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1790.REPORT_PATH = REPORT_PATH
    prev1790.prev1783.V1783_OUT = OUT_DIR
    prev1790.prev1783.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1790.prev1783.DEFAULT_REPORT_PATH = REPORT_PATH
    prev = prev1790.prev1783.prev
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1792",
        "--decision",
        "v1792-pm-register-request-string-observer-source-build-pass",
        "--cycle-label",
        "v1792",
        "--init-version",
        "0.9.147",
        "--init-build",
        "v1792-pm-register-request-string-observer",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1792_pm_register_request_string_observer"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v338"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1792_pm_register_request_string_observer.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1792_pm_register_request_string_observer.img"),
        "--wifi-test-klog-prefix",
        "A90v1792",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1792.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1792.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1792.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1792-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1792.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1792-supervisor.pid",
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
        "# Native Init V1792 PM Register Request String Observer Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1792`",
        "- Type: source/build-only rollbackable WLAN-PD PM register request string observer test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v338 keeps the V1790 PM-service devnode fetchargs and adds tracefs fetchargs to the PM-service register entry, string-compare, and no-peripheral return so the next live gate can capture the exact peripheral name requested by `cnss-daemon` before any private devnode repair.",
        "- Manifest: `tmp/wifi/v1792-pm-register-request-string-observer-test-boot/manifest.json`",
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
        "- Base route remains the bounded V1790 service-object route: service managers, firmware-serve stack, `pm_proxy_helper`, `pm-service`, `/dev/subsys_modem` holder, `cnss_diag`, and stock `cnss-daemon`.",
        "- Added observer only: PM-service register tracefs fetchargs record the requested peripheral string, client string, string-compare operands, and no-peripheral return string.",
        "- V1790 devnode observer remains present to correlate the requested peripheral with discovered PM-service candidate name/devnode records.",
        "- Still excluded: full `pm-proxy`, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping.",
        "",
        "## Fetchargs",
        "",
        "- `pm_server_register_entry`: `peripheral=+0(%x1):string client=+0(%x2):string out_client=%x4 out_state=%x5`",
        "- `pm_server_register_strcmp_call`: `candidate=+0(%x0):string requested=+0(%x1):string`",
        "- `pm_server_register_no_peripheral`: `peripheral=+0(%x26):string`",
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
        "- V1793 should run one rollbackable live gate with this artifact and classify the exact PM register request string before any devnode repair.",
        "- `pm-register-request-sdx50m`: CNSS requests `SDX50M`; host-only plan a private devnode-existence parity repair without opening `/dev/subsys_esoc0`.",
        "- `pm-register-request-modem-or-other`: CNSS requests a different peripheral; classify list population and request/candidate mismatch before any repair.",
        "- `pm-register-fetcharg-unavailable`: tracefs fetchargs cannot recover the string; fall back to a narrower host-only disassembly or non-mutating uprobe plan.",
        "- `pm-register-list-commit-progress`: PM-service list commit appears and register progresses; stop and classify the new downstream label.",
        "- The gate remains one-run: do not autonomously chain into PM repair, WLAN-PD cascade, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev1790.prev1783.prev.render_report = render_report
    return prev1790.prev1783.prev.main()


if __name__ == "__main__":
    raise SystemExit(main())
