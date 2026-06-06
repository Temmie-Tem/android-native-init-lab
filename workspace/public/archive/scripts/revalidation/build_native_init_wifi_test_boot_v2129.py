#!/usr/bin/env python3
"""Build V2129 native post-FW_READY boot_wlan trigger test boot."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2127 as prev2127


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2129-post-fw-ready-boot-wlan-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2129/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v423"
EXPECTED_HELPER_SHA256 = "218b95ce9357ef9e437908c90d39725b2f34d7c74b86ee1efe63066738ea8e63"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2129_POST_FW_READY_BOOT_WLAN_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2127.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_POST_FW_READY_BOOT_WLAN_TRIGGER=1",
)


def configure_base() -> None:
    prev2127.OUT_DIR = OUT_DIR
    prev2127.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2127.REPORT_PATH = REPORT_PATH
    prev2127.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2127.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2127.HELPER_FLAGS = HELPER_FLAGS
    prev2127.configure_base()

    base = prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2129",
        "--decision": "v2129-post-fw-ready-boot-wlan-source-build-pass",
        "--cycle-label": "v2129",
        "--init-version": "0.9.239",
        "--init-build": "v2129-post-fw-ready-boot-wlan",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2129_post_fw_ready_boot_wlan"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v423_post_fw_ready_boot_wlan"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2129_post_fw_ready_boot_wlan.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2129_post_fw_ready_boot_wlan.img"),
        "--wifi-test-klog-prefix": "A90v2129",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2129.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2129.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2129.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2129-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2129.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2129-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2129 Post-FW_READY Boot WLAN Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2129`",
        "- Type: source/build-only discriminator for the post-FW_READY QCACLD registration edge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v423 keeps the V2127/V2128 route unchanged and adds one compile-gated `/sys/kernel/boot_wlan/boot_wlan` write only after the helper itself reads ICNSS `FW_READY` processed from `/sys/kernel/debug/icnss/stats`.",
        "- Manifest: `tmp/wifi/v2129-post-fw-ready-boot-wlan-test-boot/manifest.json`",
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
        "- Kept: V2127 dual-RFS bridges, shared `server_info.txt`, root lower companions, PerMgr/WLFW focused summaries, ICNSS numeric/event stats, post-BDF summary, and long lower-window hold.",
        "- Added: `post_fw_ready_boot_wlan_trigger` safety gate, which records pre-trigger `FW_READY`/`REGISTER_DRIVER` counters, writes `1` to `/sys/kernel/boot_wlan/boot_wlan` only when FW_READY is processed, then captures post-trigger klog and ICNSS stats.",
        "- Excluded: macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, module load/unload, driver bind/unbind, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If post-FW_READY `boot_wlan` posts/processes `REGISTER_DRIVER` and `wlan0` appears, stop before connectivity and run the dedicated connect/ping gate.",
        "- If `REGISTER_DRIVER` posts but `wlan0` remains absent, chase the QCACLD probe/startup return path.",
        "- If the write succeeds but `REGISTER_DRIVER` remains `0/0`, the boot_wlan callback path did not reach `wlan_hdd_register_driver()` under the native route.",
        "- If artifact validation fails, do not run the live handoff.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. The eventual V2130 live handoff is rollbackable and intentionally permits only the post-FW_READY `/sys/kernel/boot_wlan/boot_wlan` driver-start write. It still forbids Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, eSoC/PCIe/GDSC/PMIC/GPIO paths, module load/unload, driver bind/unbind, and firmware/partition writes.",
        "",
    ])


def main() -> int:
    configure_base()
    base = prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2127.prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
