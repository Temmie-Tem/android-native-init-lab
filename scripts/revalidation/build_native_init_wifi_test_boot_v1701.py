#!/usr/bin/env python3
"""Build V1701 WLAN-PD cnss-daemon tracefs target-path test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1699 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1701-wlan-pd-cnss-tracefs-target-path-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1701/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1701_WLAN_PD_CNSS_TRACEFS_TARGET_PATH_SOURCE_BUILD_2026-06-02.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = base.build_cnss_property_runtime


def configure_base() -> None:
    base.configure_base()
    base.base.OUT_DIR = OUT_DIR
    base.base.PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
    base.base.PROPERTY_ROOT = base.base.PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
    base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.REPORT_PATH = REPORT_PATH
    base.OUT_DIR = OUT_DIR
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.REPORT_PATH = REPORT_PATH
    base.base.DEFAULT_ARGS = [
        "--cycle",
        "V1701",
        "--decision",
        "v1701-wlan-pd-cnss-tracefs-target-path-source-build-pass",
        "--cycle-label",
        "v1701",
        "--init-version",
        "0.9.128",
        "--init-build",
        "v1701-wlan-pd-cnss-tracefs-target-path",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1701_wlan_pd_cnss_tracefs_target_path"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v314"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1701_wlan_pd_cnss_tracefs_target_path.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1701_wlan_pd_cnss_tracefs_target_path.img"),
        "--wifi-test-klog-prefix",
        "A90v1701",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1701.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1701.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1701.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1701-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1701.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1701-supervisor.pid",
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
        "# Native Init V1701 WLAN-PD cnss-daemon Tracefs Target-path Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1701`",
        "- Type: source/build-only rollbackable WLAN-PD cnss-daemon tracefs target-path test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: repairs the V1700 uprobe target-path contract without adding new runtime actors",
        "- Manifest: `tmp/wifi/v1701-wlan-pd-cnss-tracefs-target-path-test-boot/manifest.json`",
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
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`",
        "- Evidence prefix: `wlan_pd_cnss_nonlog_control_flow.*`.",
        "- The helper attempts one bounded tracefs uprobe for `cnss-daemon+0xec00` and falls back to `/proc` evidence only if registration remains unavailable.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Target-path Contract",
        "",
        "- V1700 failed with `uprobe.register_rc=-2` while tracefs itself was available.",
        "- V1701 selects the uprobe target from the helper's private namespace vendor mount first: `{temp_root}/vendor/bin/cnss-daemon`.",
        "- It records target candidate `access/stat` evidence for private vendor, `/mnt/vendor/bin/cnss-daemon`, and `/vendor/bin/cnss-daemon`.",
        "- Existing successful tracefs collectors used global mounted paths such as `/mnt/vendor/bin/pm-service`; this build avoids relying on the chroot-visible `/vendor/bin/cnss-daemon` path.",
        "",
        "## Property Runtime",
        "",
        "- `persist.vendor.cnss-daemon.kmsg_logging`: `4` in `u:object_r:vendor_default_prop:s0`",
        "- `persist.vendor.cnss-daemon.debug_level`: `4` in `u:object_r:vendor_default_prop:s0`",
        "",
        "## Live Labels",
        "",
        "- `cnss-process-exited-before-wlfw`",
        "- `cnss-wlfw-entry-hit-downstream-wait`",
        "- `cnss-wlfw-entry-not-hit-init-stall`",
        "- `cnss-uprobe-unavailable-fallback-needed`",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1701-cnss-tracefs-target-path-property-runtime-ready"
        if pass_ok
        else "v1701-cnss-tracefs-target-path-property-runtime-blocked"
    )
    return manifest


def main() -> int:
    configure_base()
    base.build_cnss_property_runtime = build_cnss_property_runtime
    base.render_report = render_report
    base.base.build_cnss_property_runtime = build_cnss_property_runtime
    base.base.render_report = render_report
    return base.base.main()


if __name__ == "__main__":
    raise SystemExit(main())
