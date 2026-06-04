#!/usr/bin/env python3
"""Build V2097 native TFTP tombstone-RFS vendor_rfs permission parity test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2095 as prev2095


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2097-tftp-tombstone-rfs-vendor-perms-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2097/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v410"
EXPECTED_HELPER_SHA256 = "6b243cde11b152f56a8d83628c3c1010c1750368947ec29fccd7d6839d593397"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2097_TFTP_TOMBSTONE_RFS_VENDOR_PERMS_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2095.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_TOMBSTONE_RFS_VENDOR_RFS_PERMS=1",
)


def configure_base() -> None:
    prev2095.OUT_DIR = OUT_DIR
    prev2095.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2095.REPORT_PATH = REPORT_PATH
    prev2095.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2095.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2095.HELPER_FLAGS = HELPER_FLAGS
    prev2095.configure_base()

    base = prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2097",
        "--decision": "v2097-tftp-tombstone-rfs-vendor-perms-source-build-pass",
        "--cycle-label": "v2097",
        "--init-version": "0.9.226",
        "--init-build": "v2097-tftp-tombstone-rfs-vendor-perms",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2097_tftp_tombstone_rfs_vendor_perms"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v410_tftp_tombstone_rfs_vendor_perms"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2097_tftp_tombstone_rfs_vendor_perms.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2097_tftp_tombstone_rfs_vendor_perms.img"),
        "--wifi-test-klog-prefix": "A90v2097",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2097.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2097.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2097.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2097-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2097.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2097-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2097 TFTP Tombstone-RFS Vendor-Perms Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2097`",
        "- Type: source/build-only follow-up to V2096, fixing the tombstone-RFS bridge ownership to match live `tftp_server` (`uid/gid vendor_rfs=2903`) and adding the observed `tn` directory.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v410 keeps the V2095 light internal-modem route but creates `/data/vendor/tombstones/rfs/{modem,lpass,tn}` as namespace-local directories owned by `vendor_rfs:vendor_rfs`. This only corrects the V2096 setup miss where root-owned `0770` dirs still produced `EACCES`; it still does not create `ota_firewall/ruleset`, ptrace `tftp_server`, retry macloader, send QMI, use DIAG, use Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or touch SDX50M/eSoC/PCIe/GDSC/PMIC/GPIO.",
        "- Manifest: `tmp/wifi/v2097-tftp-tombstone-rfs-vendor-perms-test-boot/manifest.json`",
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
        "- Kept: V2095 route, Android-parity RFS readonly/readwrite bridges, `tftp_server` logdw sink, PerMgr/WLFW focused summaries, post-BDF surface summary, and long lower-window hold.",
        "- Added: namespace-local `vendor_rfs:vendor_rfs` permission parity for `/data/vendor/tombstones/rfs/{modem,lpass,tn}` only.",
        "- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The live handoff should decide whether clearing the tombstone auto-dir setup failure changes the Android-order `server_check -> ota_firewall -> wlanmdsp` branch.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
