#!/usr/bin/env python3
"""V1702 one-run WLAN-PD cnss-daemon tracefs target-path handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_tracefs_uprobe_handoff_v1700 as base


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1702"
V1701_OUT = REPO_ROOT / "tmp" / "wifi" / "v1701-wlan-pd-cnss-tracefs-target-path-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1701/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1702-wlan-pd-cnss-tracefs-target-path-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1702_WLAN_PD_CNSS_TRACEFS_TARGET_PATH_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.128 (v1701-wlan-pd-cnss-tracefs-target-path)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1701.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1701.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1701-helper.result"
DMESG_PATTERN = base.DMESG_PATTERN.replace("A90v1699", "A90v1701")

def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1699_OUT = V1701_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN
    base.base.CYCLE = CYCLE
    base.base.V1690_OUT = V1701_OUT
    base.base.base.V1687_OUT = V1701_OUT
    base.base.base.DEFAULT_SOURCE_MANIFEST = V1701_OUT / "manifest.json"
    base.base.base.DEFAULT_TEST_IMAGE = V1701_OUT / "boot_linux_v1701_wlan_pd_cnss_tracefs_target_path.img"
    base.base.base.LOCAL_PROPERTY_ROOT = V1701_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.base.CYCLE = CYCLE
    base.base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.base.DMESG_PATTERN = DMESG_PATTERN


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    rollback = result.get("rollback", {})
    return "\n".join([
        "# Native Init V1702 WLAN-PD cnss-daemon Tracefs Target-path Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1702`",
        "- Type: one-run rollbackable WLAN-PD cnss-daemon tracefs target-path/non-log gate",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Evidence: `{result.get('out_dir')}`",
        f"- Rollback attempt: `{rollback.get('attempt')}`",
        f"- Rollback ok: `{rollback.get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- non-log label: `{gate.get('nonlog_label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- property lookup all_match: `{gate.get('property_lookup_all_match')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Tracefs / Non-log Control Flow",
        "",
        f"- tracefs path/available: `{gate.get('nonlog_tracefs_path')}` / `{gate.get('nonlog_tracefs_available')}`",
        f"- uprobe register rc/registered: `{gate.get('nonlog_uprobe_register_rc')}` / `{gate.get('nonlog_uprobe_registered')}`",
        f"- uprobe enable rc/enabled: `{gate.get('nonlog_uprobe_enable_rc')}` / `{gate.get('nonlog_uprobe_enabled')}`",
        f"- uprobe hit count: `{gate.get('nonlog_uprobe_hit_count')}`",
        f"- first hit line: `{gate.get('nonlog_uprobe_first_hit_line')}`",
        f"- maps text seen / runtime PC: `{gate.get('nonlog_maps_text_seen')}` / `{gate.get('nonlog_wlfw_start_pc')}`",
        f"- socket/kmsg fd counts: `{gate.get('nonlog_socket_count')}` / `{gate.get('nonlog_kmsg_count')}`",
        f"- MHI pipe fd count / ks process count: `{gate.get('nonlog_mhi_pipe_fd_count')}` / `{gate.get('nonlog_ks_process_count')}`",
        "",
        "## Safety Scope",
        "",
        "- `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- service-manager, PM trio, `boot_wlan`, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping were not used.",
        "- Mutation scope was private property runtime staging on `/mnt/sdext`, test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Interpretation",
        "",
        "- V1702 proves stock `cnss-daemon` reaches `wlfw_start` under the internal-modem firmware-serve route.",
        "- V1681-V1700 missing `wlfw_start` dmesg evidence is a logging/measurement gap, not proof that `cnss-daemon` skipped `wlfw_start`.",
        "- The current blocker moves downstream of `cnss-daemon` entry: WLAN-PD/WLFW service publication remains absent, firmware request remains absent, and `wlan0` is still absent.",
        "- Do not add PM/service-window actors or `boot_wlan` from this label; the next unit should classify the downstream WLFW wait/request path.",
        "",
        "## V1702 Delta",
        "",
        "- Uses V1701 test boot with helper `a90_android_execns_probe v314`.",
        "- Verifies whether the repaired private-vendor target path lets tracefs register `cnss-daemon+0xec00`.",
        "- Still uses only the internal-modem firmware-serve route; no PM/service-window actors, `boot_wlan`, eSoC/RC1, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
    ])


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.base.base.classify_gate = base.classify_gate
    base.base.base.render_report = render_report
    return base.base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
