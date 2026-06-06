#!/usr/bin/env python3
"""Build V2120 native dual-RFS plus shared server_info bridge test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2112 as prev2112


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2120-dual-rfs-shared-server-info-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2120/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v419"
EXPECTED_HELPER_SHA256 = "d979538c8b405a31d1f7b4d9051502408599dc54e3ab278a5512d0e14fb8e49b"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2120_DUAL_RFS_SHARED_SERVER_INFO_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2112.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_SHARED_SERVER_INFO_TMPFS=1",
)


def configure_base() -> None:
    prev2112.OUT_DIR = OUT_DIR
    prev2112.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2112.REPORT_PATH = REPORT_PATH
    prev2112.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2112.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2112.HELPER_FLAGS = HELPER_FLAGS
    prev2112.configure_base()

    base = prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2120",
        "--decision": "v2120-dual-rfs-shared-server-info-source-build-pass",
        "--cycle-label": "v2120",
        "--init-version": "0.9.235",
        "--init-build": "v2120-dual-rfs-shared-server-info",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2120_dual_rfs_shared_server_info"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v419_dual_rfs_shared_server_info"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2120_dual_rfs_shared_server_info.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2120_dual_rfs_shared_server_info.img"),
        "--wifi-test-klog-prefix": "A90v2120",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2120.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2120.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2120.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2120-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2120.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2120-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2120 Dual-RFS Shared Server Info Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2120`",
        "- Type: source/build-only discriminator for the tftp_server startup `shared/server_info.txt` RFS bridge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v419 keeps the V2113 root `rmt_storage`/root `tftp_server` route and adds only a namespace-local tmpfs at `/vendor/rfs/msm/mpss/shared/server_info.txt`, matching the startup path that previously logged `Info file creation failed`.",
        "- Manifest: `tmp/wifi/v2120-dual-rfs-shared-server-info-test-boot/manifest.json`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Helper timeout: `{wifi['helper_timeout_sec']}`",
        f"- Property root: `{REMOTE_PROPERTY_ROOT}`",
        f"- Light firmware trace: `{wifi['light_firmware_trace']}`",
        "- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, root lower companions, PerMgr/WLFW focused summaries, and long lower-window hold.",
        "- Added: `/vendor/rfs/msm/mpss/shared` tmpfs plus writable `server_info.txt`, owned `vendor_rfs:vendor_rfs_shared`, rootfs namespace only.",
        "- Excluded: tftp identity changes, OTA ruleset fabrication, mcfg optimization, macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If `shared/server_info.txt` clears startup errors and the Android-order `ota_firewall`/`wlanmdsp` branch appears, chase WLFW 69/BDF/FW-ready/`wlan0` next.",
        "- If server_info clears but the route remains post-UP `server_check`/mcfg-only, this startup file is falsified as the WLAN-PD firmware-fetch trigger.",
        "- If artifact validation fails, do not run the live handoff.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write `/dev/wlan`, write `qcwlanstate`, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, use DIAG, ptrace `tftp_server`, send AP QMI payloads, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
