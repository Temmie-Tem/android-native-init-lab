#!/usr/bin/env python3
"""Build V1745 WLAN-PD private tracefs path repair test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v1693 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1745-wlan-pd-private-tracefs-repair-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1745/dev/__properties__"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1745_WLAN_PD_PRIVATE_TRACEFS_REPAIR_SOURCE_BUILD_2026-06-03.md"
)

ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME = base.build_cnss_property_runtime


def build_cnss_property_runtime() -> dict[str, object]:
    manifest = ORIGINAL_BUILD_CNSS_PROPERTY_RUNTIME()
    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v1745-cnss-output-source-property-runtime-ready"
        if pass_ok
        else "v1745-cnss-output-source-property-runtime-blocked"
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
        "V1745",
        "--decision",
        "v1745-wlan-pd-private-tracefs-repair-source-build-pass",
        "--cycle-label",
        "v1745",
        "--init-version",
        "0.9.142",
        "--init-build",
        "v1745-wlan-pd-private-tracefs-repair",
        "--out-dir",
        str(OUT_DIR),
        "--init-binary",
        str(OUT_DIR / "init_v1745_wlan_pd_private_tracefs_repair"),
        "--helper-binary",
        str(OUT_DIR / "a90_android_execns_probe_v329"),
        "--ramdisk-cpio",
        str(OUT_DIR / "ramdisk_v1745_wlan_pd_private_tracefs_repair.cpio"),
        "--boot-image",
        str(OUT_DIR / "boot_linux_v1745_wlan_pd_private_tracefs_repair.img"),
        "--wifi-test-klog-prefix",
        "A90v1745",
        "--wifi-test-disable",
        "/cache/native-init-wifi-test-boot-v1745.disable",
        "--wifi-test-log",
        "/cache/native-init-wifi-test-boot-v1745.log",
        "--wifi-test-summary",
        "/cache/native-init-wifi-test-boot-v1745.summary",
        "--wifi-test-helper-result",
        "/cache/native-init-wifi-test-boot-v1745-helper.result",
        "--wifi-test-pid",
        "/cache/native-init-wifi-test-boot-v1745.pid",
        "--wifi-test-watcher-pid",
        "/cache/native-init-wifi-test-boot-v1745-supervisor.pid",
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


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1745 WLAN-PD Private Tracefs Repair Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1745`",
        "- Type: source/build-only rollbackable pure-route private tracefs repair test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: extends V1743/V1744 by making CNSS uprobe arming search the private tracefs bind path before global `/sys/kernel/*/tracing` roots.",
        "- Manifest: `tmp/wifi/v1745-wlan-pd-private-tracefs-repair-test-boot/manifest.json`",
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
        "- Source change: CNSS and peripheral uprobe finders now try private tracefs paths materialized under the helper namespace before the global roots.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Expected Live Discriminator",
        "",
        "- If tracefs becomes available, V1745 can finally classify pure-route non-log `wlfw_start` entry vs no-entry.",
        "- If tracefs still reports unavailable, the blocker is not just path selection and the next unit should inspect whether tracefs is mounted globally before private namespace setup.",
        "- If `wlfw_start` appears, keep actor expansion stopped and classify the blocker as downstream WLAN-PD/WLFW publication.",
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
