#!/usr/bin/env python3
"""V1708 one-run CNSS WLFW start-branch uprobe handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_tracefs_uprobe_handoff_v1700 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1708"
V1707_OUT = REPO_ROOT / "tmp" / "wifi" / "v1707-cnss-wlfw-start-branch-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1707/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1708-cnss-wlfw-start-branch-uprobe-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1708_CNSS_WLFW_START_BRANCH_UPROBE_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.130 (v1707-cnss-wlfw-start-branch-uprobe)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1707.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1707.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1707-helper.result"
DMESG_PATTERN = (
    base.DMESG_PATTERN.replace("A90v1699", "A90v1707")
    + "|wlfw_ind_register_qmi|wlfw_cap_qmi|dms_service_request"
)
VALID_BRANCH_LABELS = {
    "wlfw-start-worker-entry-reached",
    "wlfw-worker-thread-started-waiting-for-qmi-service",
    "wlfw-worker-thread-started-qmi-ind-register-sent",
    "wlfw-worker-thread-started-qmi-cap-sent",
    "wlfw-start-pthread-create-success-worker-missing",
    "wlfw-start-pthread-create-failed",
    "wlfw-start-pthread-create-call-no-return",
    "wlfw-start-dms-init-failed-before-worker",
    "wlfw-start-dms-init-blocked-before-worker",
    "wlfw-start-pre-dms-init-failed-before-worker",
    "wlfw-start-pthread-create-not-reached",
    "cnss-target-unavailable",
}
EVENT_KEYS = (
    "wlfw_start",
    "wlfw_service_request",
    "wlfw_ind_register_qmi",
    "wlfw_cap_qmi",
    "dms_service_request",
    "wlfw_cal_mutex_fail",
    "wlfw_mutex_fail",
    "wlfw_cond_fail",
    "wlfw_cond_rsp_fail",
    "wlfw_dms_initialize_call",
    "wlfw_dms_initialize_retcheck",
    "wlfw_worker_pthread_create_call",
    "wlfw_worker_pthread_create_failure",
    "wlfw_worker_pthread_create_success",
)


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1699_OUT = V1707_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN
    base.VALID_NONLOG_LABELS = set(VALID_BRANCH_LABELS)
    base.base.CYCLE = CYCLE
    base.base.V1690_OUT = V1707_OUT
    base.base.base.V1687_OUT = V1707_OUT
    base.base.base.DEFAULT_SOURCE_MANIFEST = V1707_OUT / "manifest.json"
    base.base.base.DEFAULT_TEST_IMAGE = V1707_OUT / "boot_linux_v1707_cnss_wlfw_start_branch_uprobe.img"
    base.base.base.LOCAL_PROPERTY_ROOT = V1707_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
    base.base.base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.base.base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.base.base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.base.base.CYCLE = CYCLE
    base.base.base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.base.base.TEST_LOG_PATH = TEST_LOG_PATH
    base.base.base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.base.base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.base.base.DMESG_PATTERN = DMESG_PATTERN


def classify_gate(args: argparse.Namespace,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    decision, pass_ok, reason, details = base.classify_gate(
        args,
        test_flash,
        rollback_result,
        evidence_dir,
    )
    helper_fields = base.base.base.fwbase.parse_helper_fields(evidence_dir)
    for key in EVENT_KEYS:
        prefix = f"wlan_pd_cnss_nonlog_control_flow.uprobe.{key}"
        details[f"nonlog_{key}_name"] = helper_fields.get(f"{prefix}.name")
        details[f"nonlog_{key}_offset"] = helper_fields.get(f"{prefix}.offset")
        details[f"nonlog_{key}_register_rc"] = helper_fields.get(f"{prefix}.register_rc")
        details[f"nonlog_{key}_registered"] = helper_fields.get(f"{prefix}.registered")
        details[f"nonlog_{key}_enable_rc"] = helper_fields.get(f"{prefix}.enable_rc")
        details[f"nonlog_{key}_enabled"] = helper_fields.get(f"{prefix}.enabled")
        details[f"nonlog_{key}_hit_count"] = helper_fields.get(f"{prefix}.hit_count")
        details[f"nonlog_{key}_first_hit_line"] = helper_fields.get(f"{prefix}.first_hit_line")
    return decision, pass_ok, reason, details


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    rollback = result.get("rollback", {})
    lines = [
        "# Native Init V1708 CNSS WLFW Start Branch Uprobe Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1708`",
        "- Type: one-run rollbackable CNSS WLFW start-branch tracefs uprobe classifier",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Evidence: `{result.get('out_dir')}`",
        f"- Rollback attempt: `{rollback.get('attempt')}`",
        f"- Rollback ok: `{rollback.get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- branch non-log label: `{gate.get('nonlog_label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- property lookup all_match: `{gate.get('property_lookup_all_match')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Branch Trace Targets",
        "",
    ]
    for key in EVENT_KEYS:
        lines.extend([
            f"- `{key}` offset `{gate.get(f'nonlog_{key}_offset')}` hit_count `{gate.get(f'nonlog_{key}_hit_count')}` registered/enabled `{gate.get(f'nonlog_{key}_registered')}` / `{gate.get(f'nonlog_{key}_enabled')}`",
            f"  first_hit: `{gate.get(f'nonlog_{key}_first_hit_line')}`",
        ])
    lines.extend([
        "",
        "## Existing Control Evidence",
        "",
        f"- tracefs path/available: `{gate.get('nonlog_tracefs_path')}` / `{gate.get('nonlog_tracefs_available')}`",
        f"- aggregate wlfw_start hit count: `{gate.get('nonlog_uprobe_hit_count')}`",
        f"- aggregate first hit line: `{gate.get('nonlog_uprobe_first_hit_line')}`",
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
        "- This V1708 run classifies where `wlfw_start` stops before the expected `wlfw_service_request` worker entry.",
        "- WLFW QMI/BDF remains downstream unless this run reaches the worker entry or later QMI call targets.",
        "- `wlfw_dms_initialize_call` without `wlfw_worker_pthread_create_call` means the block is in DMS initialization before worker creation.",
        "- `wlfw_worker_pthread_create_failure` means pthread_create returned nonzero and the worker was not created.",
        "- `wlfw_worker_pthread_create_success` without worker entry means the create call returned success but the expected worker entry was not observed.",
        "- This classifier does not start Wi-Fi HAL, scan, connect, or external network tests.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_base()
    base.base.base.classify_gate = classify_gate
    base.base.base.render_report = render_report
    return base.base.base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
