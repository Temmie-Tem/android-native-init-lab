#!/usr/bin/env python3
"""V1713 one-run CNSS WLFW prologue-adjacent uprobe handoff."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_cnss_tracefs_uprobe_handoff_v1700 as base


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1713"
V1712_OUT = REPO_ROOT / "tmp" / "wifi" / "v1712-cnss-wlfw-prologue-adjacent-uprobe-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1712/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1713-cnss-wlfw-prologue-adjacent-uprobe-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1713_CNSS_WLFW_PROLOGUE_ADJACENT_UPROBE_HANDOFF_2026-06-02.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.132 (v1712-cnss-wlfw-prologue-adjacent-uprobe)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1712.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1712.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1712-helper.result"
DMESG_PATTERN = (
    base.DMESG_PATTERN.replace("A90v1699", "A90v1712")
    + "|wlfw_log_arg_severity|wlfw_log_call|wlfw_post_log_branch"
    + "|wlfw_optional_pm_init1_call|wlfw_optional_pm_init1_return|wlfw_optional_pm_init2_call"
    + "|wlfw_common_state_base|wlfw_cal_mutex_arg|wlfw_cal_mutex_null_attr"
)
VALID_PROLOGUE_LABELS = {
    "wlfw-worker-thread-started-qmi-cap-sent",
    "wlfw-worker-thread-started-qmi-ind-register-sent",
    "wlfw-worker-thread-started-waiting-for-qmi-service",
    "wlfw-start-pthread-create-success-worker-missing",
    "wlfw-start-pthread-create-failed",
    "wlfw-start-pthread-create-call-no-return",
    "wlfw-start-dms-init-failed-before-worker",
    "wlfw-start-dms-init-blocked-before-worker",
    "wlfw-start-pre-dms-init-failed-before-worker",
    "wlfw-start-cond-rsp-retcheck-no-dms",
    "wlfw-start-cond-rsp-call-no-return",
    "wlfw-start-cond-retcheck-no-cond-rsp",
    "wlfw-start-cond-call-no-return",
    "wlfw-start-mutex-retcheck-no-cond",
    "wlfw-start-mutex-call-no-return",
    "wlfw-start-cal-mutex-retcheck-no-mutex",
    "wlfw-start-cal-mutex-call-no-return",
    "wlfw-start-cal-mutex-edge-no-call",
    "wlfw-start-cal-mutex-arg-no-null-attr",
    "wlfw-start-common-path-no-cal-mutex-arg",
    "wlfw-start-optional-pm-init2-call-no-return",
    "wlfw-start-optional-pm-init1-return-no-init2",
    "wlfw-start-optional-pm-init1-call-no-return",
    "wlfw-start-post-log-branch-no-common-path",
    "wlfw-start-log-call-no-return",
    "wlfw-start-log-arg-no-log-call",
    "wlfw-start-no-log-arg",
    "cnss-target-unavailable",
}
EVENT_KEYS = (
    "wlfw_start",
    "wlfw_service_request",
    "wlfw_ind_register_qmi",
    "wlfw_cap_qmi",
    "dms_service_request",
    "wlfw_log_arg_severity",
    "wlfw_log_call",
    "wlfw_post_log_branch",
    "wlfw_optional_pm_init1_call",
    "wlfw_optional_pm_init1_return",
    "wlfw_optional_pm_init2_call",
    "wlfw_common_state_base",
    "wlfw_cal_mutex_arg",
    "wlfw_cal_mutex_null_attr",
    "wlfw_cal_mutex_call",
    "wlfw_cal_mutex_retcheck",
    "wlfw_cal_mutex_fail",
    "wlfw_mutex_call",
    "wlfw_mutex_retcheck",
    "wlfw_mutex_fail",
    "wlfw_cond_call",
    "wlfw_cond_retcheck",
    "wlfw_cond_fail",
    "wlfw_cond_rsp_call",
    "wlfw_cond_rsp_retcheck",
    "wlfw_cond_rsp_fail",
    "wlfw_dms_initialize_call",
    "wlfw_dms_initialize_retcheck",
    "wlfw_worker_pthread_create_call",
    "wlfw_worker_pthread_create_failure",
    "wlfw_worker_pthread_create_success",
)


def configure_base() -> None:
    base.CYCLE = CYCLE
    base.V1699_OUT = V1712_OUT
    base.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    base.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    base.TEST_LOG_PATH = TEST_LOG_PATH
    base.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    base.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    base.DMESG_PATTERN = DMESG_PATTERN
    base.VALID_NONLOG_LABELS = set(VALID_PROLOGUE_LABELS)
    base.base.CYCLE = CYCLE
    base.base.V1690_OUT = V1712_OUT
    base.base.base.V1687_OUT = V1712_OUT
    base.base.base.DEFAULT_SOURCE_MANIFEST = V1712_OUT / "manifest.json"
    base.base.base.DEFAULT_TEST_IMAGE = V1712_OUT / "boot_linux_v1712_cnss_wlfw_prologue_adjacent_uprobe.img"
    base.base.base.LOCAL_PROPERTY_ROOT = V1712_OUT / "property-runtime" / "layout" / "dev" / "__properties__"
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
        "# Native Init V1713 CNSS WLFW Prologue Adjacent Uprobe Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1713`",
        "- Type: one-run rollbackable CNSS `wlfw_start` adjacent-prologue tracefs uprobe classifier",
        f"- Decision: `{result.get('decision')}`",
        f"- Result: `{'PASS' if result.get('pass') else 'FAIL'}`",
        f"- Evidence: `{result.get('out_dir')}`",
        f"- Rollback attempt: `{rollback.get('attempt')}`",
        f"- Rollback ok: `{rollback.get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- output label: `{gate.get('label')}`",
        f"- prologue non-log label: `{gate.get('nonlog_label')}`",
        f"- legacy firmware-serve label: `{gate.get('old_firmware_serve_label')}`",
        f"- property lookup all_match: `{gate.get('property_lookup_all_match')}`",
        f"- cnss-daemon running: `{gate.get('cnss_daemon_running')}`",
        f"- tftp running: `{gate.get('tftp_running')}`",
        f"- companion order: `{gate.get('companion_order')}`",
        "",
        "## Prologue Trace Targets",
        "",
    ]
    for key in EVENT_KEYS:
        lines.extend([
            f"- `{key}` offset `{gate.get(f'nonlog_{key}_offset')}` hit_count `{gate.get(f'nonlog_{key}_hit_count')}` registered/enabled `{gate.get(f'nonlog_{key}_registered')}` / `{gate.get(f'nonlog_{key}_enabled')}`",
            f"  first_hit: `{gate.get(f'nonlog_{key}_first_hit_line')}`",
        ])
    lines.extend([
        "",
        "## Control Evidence",
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
        "- This V1713 run distinguishes the `wlfw_start` entry-only gap from V1710.",
        "- `wlfw-start-log-call-no-return` means the unconditional log wrapper at `0xec24` is the first live blocker.",
        "- `wlfw-start-post-log-branch-no-common-path` or optional setup labels indicate the function returned from logging but did not reach the common state setup.",
        "- `wlfw-start-cal-mutex-call-no-return` moves the blocker back to the first pthread init call.",
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
