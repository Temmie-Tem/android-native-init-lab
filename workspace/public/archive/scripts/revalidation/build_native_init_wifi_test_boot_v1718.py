#!/usr/bin/env python3
"""Build V1718 WLAN-PD cnss-daemon peripheral-client uprobe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1712 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1718-cnss-peripheral-client-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1718/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1718_CNSS_PERIPHERAL_CLIENT_UPROBE_SOURCE_BUILD_2026-06-02.md"
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
        "V1718",
        "--decision",
        "v1718-cnss-peripheral-client-uprobe-source-build-pass",
        "--cycle-label",
        "v1718",
        "--init-version",
        "0.9.134",
        "--init-build",
        "v1718-cnss-peripheral-client-uprobe",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1718_cnss_peripheral_client_uprobe"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v320"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1718_cnss_peripheral_client_uprobe.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1718_cnss_peripheral_client_uprobe.img"),
        "--wifi-test-klog-prefix",
        "A90v1718",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1718.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1718.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1718.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1718-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1718.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1718-supervisor.pid",
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
        "# Native Init V1718 CNSS Peripheral Client Uprobe Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1718`",
        "- Type: source/build-only rollbackable CNSS `libperipheral_client.so` uprobe test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends V1716/V1717 from `pm_client_register` call proof into `libperipheral_client.so` Binder registration discriminators",
        "- Manifest: `tmp/wifi/v1718-cnss-peripheral-client-uprobe-test-boot/manifest.json`",
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
        "- `periph_pm_client_register_entry` at `libperipheral_client.so+0x6ec8`.",
        "- `periph_pm_register_connect_entry` at `0x612c`.",
        "- `periph_vndbinder_init_call` at `0x6168` and `periph_default_service_manager_call` at `0x6190`.",
        "- `periph_service_manager_get_call` at `0x61c4` and `periph_binder_object_present_check` at `0x620c`.",
        "- `periph_manager_register_tx_call` / retcheck at `0x6274` / `0x6278`.",
        "- `periph_pm_register_connect_return` / `periph_pm_client_register_common_return` at `0x66dc` / `0x7184`.",
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
        "v1718-cnss-peripheral-client-property-runtime-ready"
        if pass_ok
        else "v1718-cnss-peripheral-client-property-runtime-blocked"
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
