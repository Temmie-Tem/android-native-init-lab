#!/usr/bin/env python3
"""Build V1739 WLAN-PD cnss-daemon output-source visibility test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1739-wlan-pd-cnss-output-source-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1739/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1739_WLAN_PD_CNSS_OUTPUT_SOURCE_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = prev.build_cnss_property_runtime


def configure_base() -> None:
    prev.OUT_DIR = OUT_DIR
    prev.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.PROPERTY_ROOT = prev.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.DEFAULT_ARGS = [
        "--cycle",
        "V1739",
        "--decision",
        "v1739-wlan-pd-cnss-output-source-source-build-pass",
        "--cycle-label",
        "v1739",
        "--init-version",
        "0.9.140",
        "--init-build",
        "v1739-wlan-pd-cnss-output-source",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1739_wlan_pd_cnss_output_source"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v327"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1739_wlan_pd_cnss_output_source.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1739_wlan_pd_cnss_output_source.img"),
        "--wifi-test-klog-prefix",
        "A90v1739",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1739.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1739.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1739.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1739-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1739.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1739-supervisor.pid",
        "--wifi-test-watch-sec",
        "70",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "95",
        "--wifi-test-firmware-mounts",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1739-cnss-output-source-property-runtime-ready"
        if pass_ok
        else "v1739-cnss-output-source-property-runtime-blocked"
    )
    return manifest


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1739 WLAN-PD cnss-daemon Output-source Visibility Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1739`",
        "- Type: source/build-only rollbackable WLAN-PD cnss-daemon output-source visibility test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: preserves the V1680 internal-modem firmware-serve route and separates cnss-daemon stdout/stderr/kmsg marker sources.",
        "- Manifest: `tmp/wifi/v1739-wlan-pd-cnss-output-source-test-boot/manifest.json`",
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
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Output-source Evidence",
        "",
        "- New fields: `wlan_pd_cnss_output_visibility.stdout_bytes` and `stderr_bytes`.",
        "- New fields: `wlan_pd_cnss_output_visibility.wlfw_start.{source,stdout_count,stderr_count,kmsg_count}`.",
        "- New fields: per-failure `stdout_count`, `stderr_count`, and `kmsg_count` for all eight pre-WLFW init failure strings.",
        "",
        "## Live Labels",
        "",
        "- `wlfw-start-reached-downstream-block`",
        "- `cnss-init-step-failed-<name>`",
        "- `cnss-output-still-invisible`",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    prev.build_cnss_property_runtime = build_cnss_property_runtime
    prev.render_report = render_report
    return prev.main()


if __name__ == "__main__":
    raise SystemExit(main())
