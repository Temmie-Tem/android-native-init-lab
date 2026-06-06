#!/usr/bin/env python3
"""Build V2106 native TFTP persist-RFS parent traversal test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2102 as prev2102


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2106-tftp-persist-parent-traverse-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2106/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v413"
EXPECTED_HELPER_SHA256 = "6750bdf217a2a41e5d97877dd1dd1a7d344e287b8b7aabe15725c91d05ab5bb5"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2106_TFTP_PERSIST_PARENT_TRAVERSE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2102.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_TFTP_PERSIST_RFS_PARENT_TRAVERSE_PARITY=1",
)


def configure_base() -> None:
    prev2102.OUT_DIR = OUT_DIR
    prev2102.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2102.REPORT_PATH = REPORT_PATH
    prev2102.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2102.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2102.HELPER_FLAGS = HELPER_FLAGS
    prev2102.configure_base()

    base = prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2106",
        "--decision": "v2106-tftp-persist-parent-traverse-source-build-pass",
        "--cycle-label": "v2106",
        "--init-version": "0.9.229",
        "--init-build": "v2106-tftp-persist-parent-traverse",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2106_tftp_persist_parent_traverse"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v413_tftp_persist_parent_traverse"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2106_tftp_persist_parent_traverse.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2106_tftp_persist_parent_traverse.img"),
        "--wifi-test-klog-prefix": "A90v2106",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2106.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2106.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2106.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2106-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2106.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2106-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2106 TFTP Persist Parent Traverse Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2106`",
        "- Type: source/build-only follow-up to V2103, fixing the unclosed parent-traversal cause of `tftp_server` persist-RFS EACCES.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v413 keeps the V2102 light internal-modem route and changes only namespace-local `/mnt`, `/mnt/vendor`, and `/mnt/vendor/persist` from root-only traversal to `root:system 0750`. V2103 proved the leaf persist-RFS directories existed as `vendor_rfs`, but their parents were `0750 root:root`; stock `tftp_server` runs as `vendor_rfs` with supplemental group `system`, so it could not traverse to the leaf directories.",
        "- Manifest: `tmp/wifi/v2106-tftp-persist-parent-traverse-test-boot/manifest.json`",
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
        "- Kept: V2102 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, process-namespace audit, post-BDF surface summary, and long lower-window hold.",
        "- Added: rootfs-namespace-only parent traversal parity for `/mnt`, `/mnt/vendor`, and `/mnt/vendor/persist`; `sda29` remains read-only.",
        "- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If persist-RFS EACCES clears and Android-order `server_check -> ota_firewall -> wlanmdsp` appears, chase WLFW 69/BDF/FW-ready/`wlan0` next.",
        "- If EACCES clears but the TFTP bootstrap branch is still absent, the blocker is modem-internal before the producer chooses WLAN-PD firmware fetch.",
        "- If EACCES persists, inspect SELinux label parity for `/mnt/vendor/persist*` before moving to active modem-side DIAG.",
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
    base = prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
