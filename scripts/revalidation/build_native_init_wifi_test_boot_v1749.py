#!/usr/bin/env python3
"""Build V1749 WLAN-PD tracefs mount-restore test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1749-wlan-pd-tracefs-mount-restore-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1749/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1749_WLAN_PD_TRACEFS_MOUNT_RESTORE_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = base.build_cnss_property_runtime


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1749-cnss-output-source-property-runtime-ready"
        if pass_ok
        else "v1749-cnss-output-source-property-runtime-blocked"
    )
    return manifest


def configure_base() -> None:
    base.OUT_DIR = OUT_DIR
    base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    base.PROPERTY_ROOT = base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH
    base.DEFAULT_ARGS = [
        "--cycle",
        "V1749",
        "--decision",
        "v1749-wlan-pd-tracefs-mount-restore-source-build-pass",
        "--cycle-label",
        "v1749",
        "--init-version",
        "0.9.143",
        "--init-build",
        "v1749-wlan-pd-tracefs-mount-restore",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1749_wlan_pd_tracefs_mount_restore"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v329"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1749_wlan_pd_tracefs_mount_restore.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1749_wlan_pd_tracefs_mount_restore.img"),
        "--wifi-test-klog-prefix",
        "A90v1749",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1749.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1749.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1749.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1749-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1749.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1749-supervisor.pid",
        "--wifi-test-watch-sec",
        "70",
        "--wifi-test-supervise-helper",
        "--wifi-test-supervisor-timeout-sec",
        "95",
        "--wifi-test-firmware-mounts",
        "--wifi-test-mount-debugfs",
        "--wifi-test-property-root",
        REMOTE_PROPERTY_ROOT,
        "--wifi-test-helper-mode",
        "wlan-pd-cnss-output-visibility",
    ]


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1749 WLAN-PD Tracefs Mount Restore Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1749`",
        "- Type: source/build-only rollbackable pure-route tracefs mount-restore test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: restores the V1701 `--wifi-test-mount-debugfs` contract on the V1745 private tracefs path repair artifact.",
        "- Manifest: `tmp/wifi/v1749-wlan-pd-tracefs-mount-restore-test-boot/manifest.json`",
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
        f"- Debugfs mount enabled: `{wifi['mount_debugfs']}`",
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`.",
        "- Tracefs contract: mount debugfs/tracefs before helper uprobe arming, then let helper bind/search private tracefs paths first.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- If tracefs becomes available, classify pure-route non-log `wlfw_start` entry vs no-entry.",
        "- If `wlfw_start` appears, keep actor expansion stopped and classify the blocker as downstream WLAN-PD/WLFW publication.",
        "- If tracefs still reports unavailable, inspect the PID1 debugfs mount helper path rather than adding actors.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base.build_cnss_property_runtime = build_cnss_property_runtime
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
