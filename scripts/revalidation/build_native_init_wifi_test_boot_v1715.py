#!/usr/bin/env python3
"""Build V1715 WLAN-PD cnss-daemon pm_init uprobe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1712 as prev


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1715-cnss-pm-init-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1715/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1715_CNSS_PM_INIT_UPROBE_SOURCE_BUILD_2026-06-02.md"
)


def configure_base() -> None:
    prev.configure_base()
    prev.prev.prev.base.base.OUT_DIR = OUT_DIR
    prev.prev.prev.base.base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.prev.prev.base.base.PROPERTY_ROOT = prev.prev.prev.base.base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.prev.prev.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.prev.base.base.REPORT_PATH = REPORT_PATH
    prev.prev.prev.base.OUT_DIR = OUT_DIR
    prev.prev.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.prev.base.REPORT_PATH = REPORT_PATH
    prev.prev.prev.OUT_DIR = OUT_DIR
    prev.prev.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.prev.REPORT_PATH = REPORT_PATH
    prev.prev.OUT_DIR = OUT_DIR
    prev.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.REPORT_PATH = REPORT_PATH
    prev.OUT_DIR = OUT_DIR
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.prev.prev.base.base.DEFAULT_ARGS = [
        "--cycle",
        "V1715",
        "--decision",
        "v1715-cnss-pm-init-uprobe-source-build-pass",
        "--cycle-label",
        "v1715",
        "--init-version",
        "0.9.133",
        "--init-build",
        "v1715-cnss-pm-init-uprobe",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1715_cnss_pm_init_uprobe"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v319"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1715_cnss_pm_init_uprobe.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1715_cnss_pm_init_uprobe.img"),
        "--wifi-test-klog-prefix",
        "A90v1715",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1715.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1715.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1715.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1715-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1715.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1715-supervisor.pid",
        "--wifi-test-watch-sec",
        "55",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "80",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def render_report(manifest: dict[str, object]) -> str:
    return "\n".join([
        "# Native Init V1715 CNSS pm_init Uprobe Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1715`",
        "- Type: source/build-only rollbackable CNSS `pm_init` uprobe test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends V1713/V1714 from `wlfw_start` call-site proof into `pm_init@0xc39c` discriminators",
        "- Manifest: `tmp/wifi/v1715-cnss-pm-init-uprobe-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        "- Helper runtime mode: `wifi-companion-wlan-pd-cnss-output-visibility-start-only`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## New Trace Targets",
        "",
        "- `pm_init_entry` at `cnss-daemon+0xc39c`.",
        "- `pm_init_get_system_info_call` / `pm_init_system_info_ok` at `0xc444` / `0xc470`.",
        "- null-peripheral loop targets at `0xc49c`, `0xc58c`, and `0xc5e0`.",
        "- `pm_client_register` edge at `0xc624` / `0xc628`.",
        "- `pm_client_connect` edge at `0xc650` / `0xc654`.",
        "- `pm_init_return_path` at `0xc554`.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = prev.prev.prev.ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1715-cnss-pm-init-property-runtime-ready"
        if pass_ok
        else "v1715-cnss-pm-init-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    prev.prev.prev.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.prev.prev.base.render_report = render_report
    prev.prev.prev.base.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.prev.prev.base.base.render_report = render_report
    return prev.prev.prev.base.base.main()


if __name__ == "__main__":
    raise SystemExit(main())
