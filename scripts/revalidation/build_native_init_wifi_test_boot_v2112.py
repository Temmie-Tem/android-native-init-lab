#!/usr/bin/env python3
"""Build V2112 native dual-RFS + persist-RFS leaf precreate test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2108 as prev2108


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2112-dual-rfs-leaf-precreate-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2112/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v415"
EXPECTED_HELPER_SHA256 = "b86763800e2e56b4211c320ae454c07bbcfc7c40facf6b4e2a51f5bb7318c35d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2112_DUAL_RFS_LEAF_PRECREATE_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2108.HELPER_FLAGS,
    "-DA90_RFS_BRIDGE_SERVE_FIRMWARE_MNT_PROBE=1",
)


def configure_base() -> None:
    prev2108.OUT_DIR = OUT_DIR
    prev2108.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2108.REPORT_PATH = REPORT_PATH
    prev2108.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2108.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2108.HELPER_FLAGS = HELPER_FLAGS
    prev2108.configure_base()

    base = prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2112",
        "--decision": "v2112-dual-rfs-leaf-precreate-source-build-pass",
        "--cycle-label": "v2112",
        "--init-version": "0.9.231",
        "--init-build": "v2112-dual-rfs-leaf-precreate",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2112_dual_rfs_leaf_precreate"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v415_dual_rfs_leaf_precreate"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2112_dual_rfs_leaf_precreate.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2112_dual_rfs_leaf_precreate.img"),
        "--wifi-test-klog-prefix": "A90v2112",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2112.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2112.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2112.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2112-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2112.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2112-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2112 Dual-RFS Leaf Precreate Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2112`",
        "- Type: source/build-only integration of V2109 persist-RFS leaf fixes with the exact Android dual-RFS WLAN image bridge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v415 keeps the V2109 light internal-modem route and additionally resolves `/vendor/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn` to the already-mounted WLAN image, while preserving the fallback `/vendor/firmware/wlanmdsp.mbn` path.",
        "- Manifest: `tmp/wifi/v2112-dual-rfs-leaf-precreate-test-boot/manifest.json`",
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
        "- Kept: V2109 route, readonly/readwrite RFS bridges, vendor-owned tombstone dirs, persist-RFS auto-dir targets, parent traversal parity, persist-RFS mdm/apq leaf precreate, `tftp_server` logdw sink, focused PerMgr/WLFW summaries, process-namespace audit, post-BDF surface summary, and long lower-window hold.",
        "- Added: exact Android WLAN image path bridge for `readonly/vendor/firmware_mnt/image/wlanmdsp.mbn`; rootfs namespace only, no `sda29` write.",
        "- Excluded: `ota_firewall/ruleset` fabrication, macloader retry, `boot_wlan`/`qcwlanstate` write, module load/unload, driver bind/unbind, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If the exact dual-RFS path plus leaf precreate produces `wlanmdsp.mbn` transfer, chase WLFW 69/BDF/FW-ready/`wlan0` next.",
        "- If both image paths resolve but the modem still skips `ota_firewall/wlanmdsp`, the remaining gate is before the modem selects the Android-order WLAN-PD firmware-fetch branch.",
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
    base = prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
