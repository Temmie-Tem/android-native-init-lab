#!/usr/bin/env python3
"""Build V2127 native shared-server-info route with ICNSS event stats."""

from __future__ import annotations

from pathlib import Path

import build_native_init_wifi_test_boot_v2120 as prev2120


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v2127-icnss-event-stats-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2127/dev/__properties__"
EXPECTED_HELPER_MARKER = "a90_android_execns_probe v422"
EXPECTED_HELPER_SHA256 = "86587acfb03eefe09e578aabf5d38aa89d6ca3a6442d9a241d63c8790cc14f2d"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2127_ICNSS_EVENT_STATS_SOURCE_BUILD_2026-06-05.md"
)
HELPER_FLAGS = (
    *prev2120.HELPER_FLAGS,
    "-DA90_WIFI_TEST_BOOT_WLFW_INDICATION_LABEL_FIX=1",
    "-DA90_WIFI_TEST_BOOT_ICNSS_STATS_NUMERIC_SUMMARY=1",
    "-DA90_WIFI_TEST_BOOT_ICNSS_STATS_EVENT_SUMMARY=1",
)


def configure_base() -> None:
    prev2120.OUT_DIR = OUT_DIR
    prev2120.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2120.REPORT_PATH = REPORT_PATH
    prev2120.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    prev2120.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2120.HELPER_FLAGS = HELPER_FLAGS
    prev2120.configure_base()

    base = prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    args = list(base.DEFAULT_ARGS)
    replacements = {
        "--cycle": "V2127",
        "--decision": "v2127-icnss-event-stats-source-build-pass",
        "--cycle-label": "v2127",
        "--init-version": "0.9.238",
        "--init-build": "v2127-icnss-event-stats",
        "--out-dir": str(OUT_DIR),
        "--init-binary": str(OUT_DIR / "init_v2127_icnss_event_stats"),
        "--helper-binary": str(OUT_DIR / "a90_android_execns_probe_v422_icnss_event_stats"),
        "--ramdisk-cpio": str(OUT_DIR / "ramdisk_v2127_icnss_event_stats.cpio"),
        "--boot-image": str(OUT_DIR / "boot_linux_v2127_icnss_event_stats.img"),
        "--wifi-test-klog-prefix": "A90v2127",
        "--wifi-test-disable": "/cache/native-init-wifi-test-boot-v2127.disable",
        "--wifi-test-log": "/cache/native-init-wifi-test-boot-v2127.log",
        "--wifi-test-summary": "/cache/native-init-wifi-test-boot-v2127.summary",
        "--wifi-test-helper-result": "/cache/native-init-wifi-test-boot-v2127-helper.result",
        "--wifi-test-pid": "/cache/native-init-wifi-test-boot-v2127.pid",
        "--wifi-test-watcher-pid": "/cache/native-init-wifi-test-boot-v2127-supervisor.pid",
        "--wifi-test-property-root": REMOTE_PROPERTY_ROOT,
    }
    for key, value in replacements.items():
        prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.set_arg(args, key, value)
    base.DEFAULT_ARGS = args


def render_report(manifest: dict[str, object]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V2127 ICNSS Event Stats Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V2127`",
        "- Type: source/build-only observability correction for the post-cal kernel ICNSS event edge.",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: helper v422 keeps the V2120/V2123 shared-server-info route unchanged and adds `/sys/kernel/debug/icnss/stats` event-table parsing for `FW_READY` posted/processed and ICNSS state.",
        "- Manifest: `tmp/wifi/v2127-icnss-event-stats-test-boot/manifest.json`",
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
        "- Kept: V2120 dual-RFS read-only/read-write/shared bridges, root lower companions, PerMgr/WLFW focused summaries, post-BDF summary, and long lower-window hold.",
        "- Added: event-table `icnss/stats` counters for `SERVER_ARRIVE`, `FW_READY`, `REGISTER_DRIVER`, plus the `State:` line; numeric request counters stay enabled.",
        "- Excluded: route behavior changes, tftp identity changes, OTA ruleset fabrication, mcfg optimization, macloader retry, DIAG, boot-time QRTR matrix, rild/cnss/pm-service strace, `tftp_server` ptrace, AP QMI send, `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator writes, forced RC1/case, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, and firmware/partition writes.",
        "",
        "## Branch",
        "",
        "- If `FW_READY` posted/processed stays zero while userspace msg21 appears, classify the gap as FW_READY indication not delivered to the kernel ICNSS event queue.",
        "- If `FW_READY` is posted but not processed, classify the blocker in the ICNSS event worker; if processed but no `wlan0`, chase driver probe.",
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
    base = prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.prev2008.prev2006.build_base_module()
    base.base.EXPECTED_HELPER_MARKER = EXPECTED_HELPER_MARKER
    base.base.EXPECTED_HELPER_SHA256 = EXPECTED_HELPER_SHA256
    prev2120.prev2112.prev2108.prev2106.prev2102.prev2100.prev2097.prev2095.prev2082.prev2080.prev2058.prev2038.patch_helper_builder(base)
    base.render_report = render_report
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
