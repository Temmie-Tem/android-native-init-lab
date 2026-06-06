#!/usr/bin/env python3
"""Build V2108 native TFTP persist-RFS leaf precreate test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2106 as prev2106


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2108-tftp-persist-rfs-leaf-precreate-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2108/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v414"
EXPECTED_HELPER_SHA256 = "25a9e1460d9b66a654e729ad3f3b5b4e08fc0157085707fe66ca2419f9293e23"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2108_TFTP_PERSIST_RFS_LEAF_PRECREATE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2106.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_LEAF_PRECREATE=1",
)


def configure_base() -> None:
    prev2106.OUT_DIR = OUT_DIR
    prev2106.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2106.REPORT_PATH = REPORT_PATH
    prev2106.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2106.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2106.HELPER_FLAGS = HELPER_FLAGS
    prev2106.configure_base()

    base = prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2108",
        "--decision": "v2108-tftp-persist-rfs-leaf-precreate-source-build-pass",
        "--cycle-label": "v2108",
        "--init-version": "0.9.230",
        "--init-build": "v2108-tftp-persist-rfs-leaf-precreate",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2108_tftp_persist_rfs_leaf_precreate"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v414_tftp_persist_rfs_leaf_precreate"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2108_tftp_persist_rfs_leaf_precreate.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2108_tftp_persist_rfs_leaf_precreate.img"),
        "--wifi-test-klog-prefix": "A90v2108",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2108.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2108.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2108.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2108-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2108.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2108-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2108 TFTP Persist-RFS Leaf Precreate Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2108`",
        "- Type: source/build-only follow-up to V2107, fixing the remaining stock `tftp_server` persist-RFS ENOENT mkdir targets.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v414 keeps the V2106 light internal-modem route and adds only namespace-local `/mnt/vendor/persist/rfs/{mdm/mpss,apq/gnss}` precreation as `vendor_rfs:vendor_rfs 0770`. V2107 proved parent traversal works and exposed the remaining `mkdir failed: [2]` startup targets for stock `tftp_server`.",
        "- Manifest: `tmp/wifi/v2108-tftp-persist-rfs-leaf-precreate-test-boot/manifest.json`",
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
        "- Kept: V2106 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, parent traversal parity, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, process-namespace audit, post-BDF surface summary, and long lower-window hold.",
        "- Added: rootfs-namespace-only precreation of `/mnt/vendor/persist/rfs/mdm/mpss` and `/mnt/vendor/persist/rfs/apq/gnss`; `sda29` remains read-only.",
        "- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If persist-RFS mkdir failures clear and Android-order `server_check -> ota_firewall -> wlanmdsp` appears, chase WLFW 69/BDF/FW-ready/`wlan0` next.",
        "- If mkdir failures clear but the TFTP bootstrap branch is still late/incomplete, the blocker is modem-internal before the producer chooses the full WLAN-PD firmware fetch branch.",
        "- If mkdir failures persist, inspect exact missing persist-RFS leaves and stock `tftp_server` path expectations before moving to active modem-side DIAG.",
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
    base = prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
