#!/usr/bin/env python3
"""Build V1712 WLAN-PD cnss-daemon prologue-adjacent uprobe test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1709 as prev


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1712-cnss-wlfw-prologue-adjacent-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1712/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1712_CNSS_WLFW_PROLOGUE_ADJACENT_UPROBE_SOURCE_BUILD_2026-06-02.md"
)


def configure_base() -> None:
    prev.configure_base()
    prev.prev.base.base.OUT_DIR = OUT_DIR
    prev.prev.base.base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    prev.prev.base.base.PROPERTY_ROOT = prev.prev.base.base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    prev.prev.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.base.base.REPORT_PATH = REPORT_PATH
    prev.prev.base.OUT_DIR = OUT_DIR
    prev.prev.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.base.REPORT_PATH = REPORT_PATH
    prev.prev.OUT_DIR = OUT_DIR
    prev.prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.prev.REPORT_PATH = REPORT_PATH
    prev.OUT_DIR = OUT_DIR
    prev.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev.REPORT_PATH = REPORT_PATH
    prev.prev.base.base.DEFAULT_ARGS = [
        "--cycle",
        "V1712",
        "--decision",
        "v1712-cnss-wlfw-prologue-adjacent-uprobe-source-build-pass",
        "--cycle-label",
        "v1712",
        "--init-version",
        "0.9.132",
        "--init-build",
        "v1712-cnss-wlfw-prologue-adjacent-uprobe",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1712_cnss_wlfw_prologue_adjacent_uprobe"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v318"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1712_cnss_wlfw_prologue_adjacent_uprobe.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1712_cnss_wlfw_prologue_adjacent_uprobe.img"),
        "--wifi-test-klog-prefix",
        "A90v1712",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1712.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1712.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1712.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1712-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1712.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1712-supervisor.pid",
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
        "# Native Init V1712 CNSS WLFW Prologue Adjacent Uprobe Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1712`",
        "- Type: source/build-only rollbackable CNSS `wlfw_start` prologue-adjacent uprobe test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends V1710/V1711 to adjacent targets between `wlfw_start@0xec00` and first `pthread_mutex_init@0xec58`",
        "- Manifest: `tmp/wifi/v1712-cnss-wlfw-prologue-adjacent-uprobe-test-boot/manifest.json`",
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
        "- `cnss-daemon+0xec20`: log severity setup immediately before unconditional log call.",
        "- `cnss-daemon+0xec24`: unconditional log wrapper call.",
        "- `cnss-daemon+0xec28`: first post-log instruction.",
        "- `cnss-daemon+0xec34` / `0xec44`: optional setup calls on the zero-argument path.",
        "- `cnss-daemon+0xec48`: common path after log/optional setup.",
        "- `cnss-daemon+0xec50` / `0xec54` / `0xec58`: first pthread init edge.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = prev.prev.ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1712-cnss-wlfw-prologue-adjacent-property-runtime-ready"
        if pass_ok
        else "v1712-cnss-wlfw-prologue-adjacent-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    prev.prev.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.prev.base.render_report = render_report
    prev.prev.base.base.build_cnss_property_runtime = build_cnss_property_runtime
    prev.prev.base.base.render_report = render_report
    return prev.prev.base.base.main()


if __name__ == "__main__":
    raise SystemExit(main())
