#!/usr/bin/env python3
"""Build V2114 native dual-RFS leaf-precreate plus bounded DIAG session-mask test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2112 as prev2112


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2114-dual-rfs-leaf-diag-session-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2114/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v416"
EXPECTED_HELPER_SHA256 = "57f71f91ec3e5eb8473c521843973db5f498019ca7b75e297c8c6d5430aed2d8"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2114_DUAL_RFS_LEAF_DIAG_SESSION_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2112.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_DIAG_DCI_REGISTER_READ_PROBE=1",
    "-DA90_WIFI_TEST_BOOT_DIAG_DCI_WLAN_TARGET_MASK_PROBE=1",
    "-DA90_WIFI_TEST_BOOT_DIAG_WLAN_PD_MEMORY_DEVICE_PROBE=1",
    "-DA90_WIFI_TEST_BOOT_DIAG_WLAN_PD_MEMORY_SESSION_MASK_PROBE=1",
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
        "--cycle": "V2114",
        "--decision": "v2114-dual-rfs-leaf-diag-session-source-build-pass",
        "--cycle-label": "v2114",
        "--init-version": "0.9.232",
        "--init-build": "v2114-dual-rfs-leaf-diag-session",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2114_dual_rfs_leaf_diag_session"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v416_dual_rfs_leaf_diag_session"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2114_dual_rfs_leaf_diag_session.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2114_dual_rfs_leaf_diag_session.img"),
        "--wifi-test-klog-prefix": "A90v2114",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2114.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2114.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2114.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2114-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2114.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2114-supervisor.pid",
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
        "# Native Init V2114 Dual-RFS Leaf DIAG Session Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2114`",
        "- Type: source/build-only integration of V2113 bridge parity with the bounded V2074 WLAN-PD DIAG memory-session mask observer.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v416 keeps the V2113 dual-RFS plus persist-RFS leaf route and adds only the existing query-gated WLAN-PD `MEMORY_DEVICE_MODE` DIAG session with three WLAN log masks and three WLAN event masks, held and cleared in one boot.",
        "- Manifest: `tmp/wifi/v2114-dual-rfs-leaf-diag-session-test-boot/manifest.json`",
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
        "- Kept: V2113 exact Android dual-RFS WLAN image path, readwrite tmpfs, persist-RFS leaf precreate, process namespace audit, PerMgr/WLFW focused summaries, and long lower-window hold.",
        "- Added: bounded V2074 DIAG session-mask observer: DCI support/register/read/deinit, bounded WLAN target masks, one WLAN-PD-only memory-device switch, session-local HDLC disable, exactly three WLAN log masks and three WLAN event masks, then cleanup.",
        "- Excluded: USB/PCIE/global DIAG restore, broad DIAG masks, DCI stream config, passive DIAG replay, boot-time QRTR matrix, rild/cnss/pm-service multi-strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If DIAG yields useful WLAN-PD memory payloads, decode them offline to choose the next modem-side mask/event.",
        "- If it again yields mask-response-only/no-payload with the V2113 bridge, the AP-side DIAG session path is closed for this producer gate.",
        "- If `wlanmdsp`, FW-ready, or `wlan0` appears, chase the normal downstream cascade and defer scan/connect until real `wlan0` is present.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue live device commands, flash, reboot, run Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, open `/dev/subsys_esoc0`, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, send AP QMI payloads, or write firmware/boot/device partitions.",
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
