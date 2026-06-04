#!/usr/bin/env python3
"""V2057 rollbackable handoff for readwrite-transition pre-wlanmdsp ordering."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_fallback_persist_rfs_mcfg_handoff_v2046 as prev2046


CYCLE = "V2057"
OUT_DIR = prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2057-readwrite-transition-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2056-handoff"
HANDOFF_REPORT = OUT_DIR / "v2056-handoff-report.md"
REPORT_PATH = prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2057_READWRITE_TRANSITION_HANDOFF_2026-06-04.md"
)
V2056_OUT = prev2046.prev2035.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2056-tftp-readwrite-transition-pre-wlanmdsp-trigger-test-boot"
)
V2056_INIT = V2056_OUT / "init_v2056_tftp_readwrite_transition_pre_wlanmdsp_trigger"
V2056_BOOT = V2056_OUT / "boot_linux_v2056_tftp_readwrite_transition_pre_wlanmdsp_trigger.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2056/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.207 (v2056-tftp-readwrite-transition-pre-wlanmdsp-trigger)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2056.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2056.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2056-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v392"

ORIGINAL_ARTIFACT_HOOK = prev2046.artifact_hook_check
ORIGINAL_COLLECT_DETAILS = prev2046.collect_details

ORDER_KEYS = (
    "start_monotonic_ms",
    "first_relevant_monotonic_ms",
    "first_relevant_delta_ms",
    "first_tftp_server_monotonic_ms",
    "first_tftp_server_delta_ms",
    "first_server_check_monotonic_ms",
    "first_server_check_delta_ms",
    "first_ota_firewall_monotonic_ms",
    "first_ota_firewall_delta_ms",
    "first_mcfg_monotonic_ms",
    "first_mcfg_delta_ms",
    "first_wlanmdsp_monotonic_ms",
    "first_wlanmdsp_delta_ms",
    "first_rrq_monotonic_ms",
    "first_rrq_delta_ms",
    "first_wrq_monotonic_ms",
    "first_wrq_delta_ms",
)


def rel(path: Path) -> str:
    return prev2046.rel(path)


def intish(value: object) -> int:
    return prev2046.intish(value)


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    return prev2046.markdown_table(headers, rows)


def helper_text() -> str:
    parts: list[str] = []
    for path in (
        HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        HANDOFF_DIR / "test-v1393-log.stdout.txt",
        HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def parse_fields() -> dict[str, str]:
    return prev2046.prev2035.prev1998.parse_fields(helper_text())


def trace_ts(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s", line)
    return float(match.group(1)) if match else None


def dmesg_ts(line: str) -> float | None:
    match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
    return float(match.group(1)) if match else None


def current_dmesg_lines() -> list[str]:
    path = HANDOFF_DIR / "test-v1393-dmesg.stdout.txt"
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def collect_current_cascade(details: dict[str, Any]) -> dict[str, Any]:
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    lines = current_dmesg_lines()
    wlan_pd_lines = [
        f"{rel(HANDOFF_DIR / 'test-v1393-dmesg.stdout.txt')}: {line}"
        for line in lines
        if "root_service_service_ind_cb" in line and "msm/modem/wlan_pd" in line and "0x1fffffff" in line
    ]
    icnss_lines = [
        f"{rel(HANDOFF_DIR / 'test-v1393-dmesg.stdout.txt')}: {line}"
        for line in lines
        if "icnss_qmi: QMI Server Connected" in line
    ]
    fw_ready_lines = [
        f"{rel(HANDOFF_DIR / 'test-v1393-dmesg.stdout.txt')}: {line}"
        for line in lines
        if "WLAN FW is ready" in line
    ]
    wlan0_lines = [
        f"{rel(HANDOFF_DIR / 'test-v1393-dmesg.stdout.txt')}: {line}"
        for line in lines
        if "wlan0" in line
    ]
    timestamps = [value for value in (dmesg_ts(line) for line in lines) if value is not None]
    up_ts = dmesg_ts(wlan_pd_lines[0]) if wlan_pd_lines else None
    last_ts = timestamps[-1] if timestamps else None
    cascade.update({
        "first_wlan_pd_up_lines": wlan_pd_lines[:4],
        "first_icnss_qmi_lines": icnss_lines[:4],
        "first_fw_ready_lines": fw_ready_lines[:4],
        "first_wlan0_lines": wlan0_lines[:4],
        "wlan_pd_up": 1 if wlan_pd_lines else 0,
        "wlan_pd_up_ts": up_ts,
        "icnss_qmi_connected": 1 if icnss_lines else 0,
        "fw_ready": 1 if fw_ready_lines else 0,
        "wlan0": 1 if wlan0_lines else 0,
        "last_dmesg_ts": last_ts,
        "post_up_hold_sec": (last_ts - up_ts) if up_ts is not None and last_ts is not None else 0,
        "post_up_hold_ge_30": bool(up_ts is not None and last_ts is not None and (last_ts - up_ts) >= 30.0),
    })
    return cascade


def event_first(fields: dict[str, str], name: str) -> dict[str, Any]:
    line = fields.get(
        f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}.first_hit_line",
        "",
    )
    return {
        "line": line,
        "trace_ts": trace_ts(line),
        "hit_count": intish(fields.get(f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}.hit_count")),
    }


def rc_from_line(line: str) -> str:
    match = re.search(r"\brc=(0x[0-9a-fA-F]+)", line)
    return match.group(1) if match else ""


def collect_current_post_cal(fields: dict[str, str], details: dict[str, Any]) -> dict[str, Any]:
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    cap_success = event_first(fields, "wlfw_cap_success_branch")
    bdf_return = event_first(fields, "wlfw_bdf_return")
    cal_return = event_first(fields, "wlfw_cal_report_return")
    worker_cal = event_first(fields, "wlfw_worker_cal_only_retcheck")
    post.update({
        "cap_return_rc": "0x0" if intish(cap_success.get("hit_count")) > 0 else "",
        "bdf_return_rc": rc_from_line(str(bdf_return.get("line", ""))),
        "cal_return_rc": rc_from_line(str(cal_return.get("line", ""))),
        "worker_cal_rc": rc_from_line(str(worker_cal.get("line", ""))),
    })
    return post


def collect_tftp_order(fields: dict[str, str], details: dict[str, Any]) -> dict[str, Any]:
    summary = {}
    for key in ORDER_KEYS:
        summary[key] = intish(fields.get(f"tftp_logdw_sink.summary.{key}"))
    summary["order_timestamps"] = intish(fields.get("tftp_logdw_sink.order_timestamps"))
    if summary["start_monotonic_ms"] <= 0:
        summary["start_monotonic_ms"] = intish(fields.get("tftp_logdw_sink.start_monotonic_ms"))
    summary["ota_firewall"] = intish(fields.get("tftp_logdw_sink.summary.ota_firewall"))

    records: list[dict[str, Any]] = []
    for index in range(96):
        prefix = f"tftp_logdw_sink.record_{index:03d}"
        payload = fields.get(f"{prefix}.payload")
        if payload is None:
            continue
        records.append({
            "index": index,
            "monotonic_ms": intish(fields.get(f"{prefix}.monotonic_ms")),
            "delta_ms": intish(fields.get(f"{prefix}.delta_ms")),
            "server_check": intish(fields.get(f"{prefix}.token.server_check")),
            "ota_firewall": intish(fields.get(f"{prefix}.token.ota_firewall")),
            "mcfg": 1 if "mcfg" in payload.lower() else 0,
            "wlanmdsp": intish(fields.get(f"{prefix}.token.wlanmdsp")),
            "fallback_wlanmdsp": intish(fields.get(f"{prefix}.token.fallback_wlanmdsp")),
            "rrq": intish(fields.get(f"{prefix}.token.rrq")),
            "wrq": intish(fields.get(f"{prefix}.token.wrq")),
            "oack": intish(fields.get(f"{prefix}.token.oack")),
            "end_transfer": intish(fields.get(f"{prefix}.token.end_transfer")),
            "total_bytes_4251884": intish(fields.get(f"{prefix}.token.total_bytes_4251884")),
            "payload": payload[:260],
        })

    if records:
        first = records[0]
        derived = {
            "first_relevant": first,
            "first_tftp_server": next((record for record in records if record["payload"].lower().find("tftp_server") >= 0), None),
            "first_server_check": next((record for record in records if record["server_check"] > 0), None),
            "first_ota_firewall": next((record for record in records if record["ota_firewall"] > 0), None),
            "first_mcfg": next((record for record in records if record["mcfg"] > 0), None),
            "first_wlanmdsp": next((record for record in records if record["wlanmdsp"] > 0), None),
            "first_rrq": next((record for record in records if record["rrq"] > 0), None),
            "first_wrq": next((record for record in records if record["wrq"] > 0), None),
        }
        for name, record in derived.items():
            if record is None:
                continue
            if summary.get(f"{name}_monotonic_ms", 0) <= 0:
                summary[f"{name}_monotonic_ms"] = record.get("monotonic_ms", 0)
            if summary.get(f"{name}_delta_ms", 0) <= 0:
                summary[f"{name}_delta_ms"] = record.get("delta_ms", -1)
        if summary["start_monotonic_ms"] <= 0:
            first_monotonic = intish(first.get("monotonic_ms"))
            first_delta = intish(first.get("delta_ms"))
            if first_monotonic > 0 and first_delta >= 0:
                summary["start_monotonic_ms"] = first_monotonic - first_delta

    cascade = collect_current_cascade(details)
    details["cascade"] = cascade
    first_wlan_pd = ""
    first_wlan_pd_lines = cascade.get("first_wlan_pd_up_lines")
    if isinstance(first_wlan_pd_lines, list) and first_wlan_pd_lines:
        first_wlan_pd = str(first_wlan_pd_lines[0])

    return {
        "summary": summary,
        "records": records,
        "wlfw_start": event_first(fields, "wlfw_start"),
        "wlfw_service_request": event_first(fields, "wlfw_service_request"),
        "wlfw_client_init": event_first(fields, "wlfw_client_init_instance_retcheck"),
        "wlfw_cap_qmi": event_first(fields, "wlfw_cap_qmi"),
        "wlan_pd_up_line": first_wlan_pd,
        "wlan_pd_up_ts": dmesg_ts(first_wlan_pd),
    }


def collect_helper_completion(fields: dict[str, str], handoff: dict[str, Any]) -> dict[str, Any]:
    rollback = handoff.get("post_rollback_verification") if isinstance(handoff.get("post_rollback_verification"), dict) else {}
    result = {
        "text_present": bool(fields),
        "result_file_version": fields.get("result_file_version", ""),
        "version_ok": fields.get("result_file_version") == EXPECTED_HELPER_VERSION,
        "probe_run_rc": fields.get("probe_run_rc", ""),
        "probe_run_rc_ok": intish(fields.get("probe_run_rc")) == 0,
        "child_exit_code": fields.get("child_exit_code", ""),
        "child_exit_code_ok": intish(fields.get("child_exit_code")) == 0,
        "child_signal": fields.get("child_signal", ""),
        "child_signal_ok": intish(fields.get("child_signal")) == 0,
        "timed_out": intish(fields.get("timed_out")),
        "test_flash_ok": bool(handoff.get("test_flash_ok")),
        "rollback_version_ok": bool(rollback.get("version_ok")),
        "rollback_selftest_fail_zero": bool(rollback.get("selftest_fail_zero")),
    }
    result["ok"] = bool(
        result["text_present"]
        and result["version_ok"]
        and result["probe_run_rc_ok"]
        and result["child_exit_code_ok"]
        and result["child_signal_ok"]
        and result["test_flash_ok"]
        and result["rollback_version_ok"]
        and result["rollback_selftest_fail_zero"]
    )
    return result


def collect_rfs_bridge(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_firmware_serve_gate.rfs_bridge"
    result = {
        "android_parity": fields.get(f"{prefix}.android_parity", ""),
        "probe_path": fields.get(f"{prefix}.probe.host_path", ""),
        "probe_exists": intish(fields.get(f"{prefix}.probe.exists")),
        "probe_nonzero": intish(fields.get(f"{prefix}.probe.nonzero")),
        "probe_size": fields.get(f"{prefix}.probe.size", ""),
        "probe_open_rc": fields.get(f"{prefix}.probe.open_rc", ""),
        "probe_open_errno": fields.get(f"{prefix}.probe.open_errno", ""),
        "fallback_path": fields.get(f"{prefix}.fallback.host_path", ""),
        "fallback_exists": intish(fields.get(f"{prefix}.fallback.exists")),
        "fallback_nonzero": intish(fields.get(f"{prefix}.fallback.nonzero")),
        "fallback_size": fields.get(f"{prefix}.fallback.size", ""),
        "fallback_open_rc": fields.get(f"{prefix}.fallback.open_rc", ""),
        "fallback_open_errno": fields.get(f"{prefix}.fallback.open_errno", ""),
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.sda29_write")),
    }
    result["ok"] = bool(
        result["android_parity"] == "firmware_mnt_probe_absent_firmware_fallback_present"
        and result["probe_exists"] == 0
        and result["probe_open_rc"] == "-1"
        and result["probe_open_errno"] == "2"
        and result["fallback_exists"] == 1
        and result["fallback_nonzero"] == 1
        and result["fallback_open_rc"] == "0"
        and result["rootfs_namespace_only"] == 1
        and result["sda29_write"] == 0
    )
    return result


def collect_readwrite_bridge(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_firmware_serve_gate.rfs_bridge"
    result = {
        "readwrite_path": fields.get(f"{prefix}.readwrite.path", ""),
        "readwrite_exists": intish(fields.get(f"{prefix}.readwrite.exists")),
        "readwrite_is_dir": intish(fields.get(f"{prefix}.readwrite.is_dir")),
        "readwrite_is_symlink": intish(fields.get(f"{prefix}.readwrite.is_symlink")),
        "readwrite_mode": fields.get(f"{prefix}.readwrite.mode", ""),
        "readwrite_uid": fields.get(f"{prefix}.readwrite.uid", ""),
        "readwrite_gid": fields.get(f"{prefix}.readwrite.gid", ""),
        "readwrite_errno": fields.get(f"{prefix}.readwrite.errno", ""),
        "readwrite_tmpfs_requested": intish(fields.get(f"{prefix}.readwrite.tmpfs_requested")),
        "server_check_path": fields.get(f"{prefix}.server_check.host_path", ""),
        "server_check_exists": intish(fields.get(f"{prefix}.server_check.exists")),
        "server_check_is_reg": intish(fields.get(f"{prefix}.server_check.is_reg")),
        "server_check_size": fields.get(f"{prefix}.server_check.size", ""),
        "server_check_errno": fields.get(f"{prefix}.server_check.stat_errno", ""),
        "rootfs_namespace_only": intish(fields.get(f"{prefix}.rootfs_namespace_only")),
        "sda29_write": intish(fields.get(f"{prefix}.sda29_write")),
    }
    result["ok"] = bool(
        result["readwrite_exists"] == 1
        and result["readwrite_is_dir"] == 1
        and result["readwrite_tmpfs_requested"] == 1
        and result["server_check_exists"] == 1
        and result["server_check_is_reg"] == 1
        and result["rootfs_namespace_only"] == 1
        and result["sda29_write"] == 0
    )
    return result


def collect_persist_bridge(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "wlan_pd_firmware_serve_gate.rfs_bridge"
    return {
        "tmpfs_requested": intish(fields.get(f"{prefix}.persist_rfs.tmpfs_requested")),
        "rfs_path": fields.get(f"{prefix}.persist_rfs.host_path", ""),
        "rfs_exists": intish(fields.get(f"{prefix}.persist_rfs.exists")),
        "rfs_is_dir": intish(fields.get(f"{prefix}.persist_rfs.is_dir")),
        "hlos_path": fields.get(f"{prefix}.persist_hlos_rfs.host_path", ""),
        "hlos_exists": intish(fields.get(f"{prefix}.persist_hlos_rfs.exists")),
        "hlos_is_dir": intish(fields.get(f"{prefix}.persist_hlos_rfs.is_dir")),
        "rfs_readwrite_path": fields.get(f"{prefix}.persist_rfs.readwrite.host_path", ""),
        "rfs_readwrite_exists": intish(fields.get(f"{prefix}.persist_rfs.readwrite.exists")),
        "rfs_readwrite_is_dir": intish(fields.get(f"{prefix}.persist_rfs.readwrite.is_dir")),
        "hlos_readwrite_path": fields.get(f"{prefix}.persist_hlos_rfs.readwrite.host_path", ""),
        "hlos_readwrite_exists": intish(fields.get(f"{prefix}.persist_hlos_rfs.readwrite.exists")),
        "hlos_readwrite_is_dir": intish(fields.get(f"{prefix}.persist_hlos_rfs.readwrite.is_dir")),
    }


def artifact_hook_check() -> dict[str, Any]:
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_forbidden = (
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=1",
        "PTRACE_ATTACH",
    )
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2056",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    boot_required = (
        EXPECTED_HELPER_VERSION,
        "tftp_readwrite_transition.mode=read-only-stat-open-on-change",
        "tftp_readwrite_transition.summary.first_server_check_file_delta_ms=%ld",
        "tftp_readwrite_transition.sample_%03u.%s.exists=%d",
        "tftp_ready_before_wlfw_vote.mode=alive-socket-plus-android-order-settle",
        "tftp_ready_before_wlfw_vote.no_qrtr_send=1",
        "tftp_ready_before_wlfw_vote.no_qmi_send=1",
        "tftp_logdw_sink.order_timestamps=1",
        "tftp_logdw_sink.record_%03u.monotonic_ms=%ld",
        "tftp_logdw_sink.summary.first_server_check_delta_ms=%ld",
        "tftp_logdw_sink.summary.first_wlanmdsp_delta_ms=%ld",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2056_INIT, init_required), (V2056_BOOT, boot_required)):
        key = rel(path)
        forbidden_tokens = init_forbidden if path == V2056_INIT else boot_forbidden
        data = path.read_bytes() if path.exists() else b""
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[key] = {
            "exists": path.exists(),
            "ok": path.exists() and not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def collect_tftp_ready(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "tftp_ready_before_wlfw_vote"
    return {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "wait_limit_ms": intish(fields.get(f"{prefix}.wait_limit_ms")),
        "min_settle_ms": intish(fields.get(f"{prefix}.min_settle_ms")),
        "poll_interval_ms": intish(fields.get(f"{prefix}.poll_interval_ms")),
        "polls": intish(fields.get(f"{prefix}.polls")),
        "elapsed_ms": intish(fields.get(f"{prefix}.elapsed_ms")),
        "alive": intish(fields.get(f"{prefix}.alive")),
        "state": fields.get(f"{prefix}.state", ""),
        "fd_count": intish(fields.get(f"{prefix}.fd_count")),
        "socket_fd_count": intish(fields.get(f"{prefix}.socket_fd_count")),
        "logdw_datagrams": intish(fields.get(f"{prefix}.logdw.datagrams")),
        "logdw_tftp_server": intish(fields.get(f"{prefix}.logdw.tftp_server")),
        "logdw_server_check": intish(fields.get(f"{prefix}.logdw.server_check")),
        "logdw_ota_firewall": intish(fields.get(f"{prefix}.logdw.ota_firewall")),
        "logdw_wlanmdsp": intish(fields.get(f"{prefix}.logdw.wlanmdsp")),
        "logdw_mcfg_seen": intish(fields.get(f"{prefix}.logdw.mcfg_seen")),
        "ready": intish(fields.get(f"{prefix}.ready")),
        "gate_open": intish(fields.get(f"{prefix}.gate_open")),
        "safe": bool(
            intish(fields.get(f"{prefix}.no_ptrace")) == 1
            and intish(fields.get(f"{prefix}.no_qrtr_send")) == 1
            and intish(fields.get(f"{prefix}.no_qmi_send")) == 1
            and intish(fields.get(f"{prefix}.no_wifi_hal")) == 1
        ),
    }


def collect_readwrite_transition(fields: dict[str, str]) -> dict[str, Any]:
    prefix = "tftp_readwrite_transition"
    summary = {
        "begin": intish(fields.get(f"{prefix}.begin")),
        "mode": fields.get(f"{prefix}.mode", ""),
        "samples": intish(fields.get(f"{prefix}.summary.samples")),
        "dropped": intish(fields.get(f"{prefix}.summary.dropped")),
        "server_check_seen": intish(fields.get(f"{prefix}.summary.server_check_seen")),
        "ota_ruleset_seen": intish(fields.get(f"{prefix}.summary.ota_ruleset_seen")),
        "mcfg_seen": intish(fields.get(f"{prefix}.summary.mcfg_seen")),
        "first_server_check_file_monotonic_ms": intish(fields.get(f"{prefix}.summary.first_server_check_file_monotonic_ms")),
        "first_server_check_file_delta_ms": intish(fields.get(f"{prefix}.summary.first_server_check_file_delta_ms")),
        "first_ota_ruleset_file_monotonic_ms": intish(fields.get(f"{prefix}.summary.first_ota_ruleset_file_monotonic_ms")),
        "first_ota_ruleset_file_delta_ms": intish(fields.get(f"{prefix}.summary.first_ota_ruleset_file_delta_ms")),
        "first_mcfg_file_monotonic_ms": intish(fields.get(f"{prefix}.summary.first_mcfg_file_monotonic_ms")),
        "first_mcfg_file_delta_ms": intish(fields.get(f"{prefix}.summary.first_mcfg_file_delta_ms")),
        "safe": bool(
            intish(fields.get(f"{prefix}.no_ptrace")) == 1
            and intish(fields.get(f"{prefix}.no_qrtr_send")) == 1
            and intish(fields.get(f"{prefix}.no_qmi_send")) == 1
            and intish(fields.get(f"{prefix}.no_wifi_hal")) == 1
        ),
    }
    samples: list[dict[str, Any]] = []
    for index in range(96):
        sample_prefix = f"{prefix}.sample_{index:03d}"
        if fields.get(f"{sample_prefix}.phase") is None:
            continue
        row: dict[str, Any] = {
            "index": index,
            "phase": fields.get(f"{sample_prefix}.phase", ""),
            "monotonic_ms": intish(fields.get(f"{sample_prefix}.monotonic_ms")),
            "delta_ms": intish(fields.get(f"{sample_prefix}.delta_ms")),
            "server_check_changed": intish(fields.get(f"{sample_prefix}.server_check_changed")),
            "ota_ruleset_changed": intish(fields.get(f"{sample_prefix}.ota_ruleset_changed")),
            "mcfg_changed": intish(fields.get(f"{sample_prefix}.mcfg_changed")),
        }
        for name in ("server_check", "ota_ruleset", "mcfg"):
            row[f"{name}_exists"] = intish(fields.get(f"{sample_prefix}.{name}.exists"))
            row[f"{name}_size"] = intish(fields.get(f"{sample_prefix}.{name}.size"))
            row[f"{name}_read_len"] = intish(fields.get(f"{sample_prefix}.{name}.read_len"))
            row[f"{name}_payload"] = fields.get(f"{sample_prefix}.{name}.payload", "")
        samples.append(row)
    if samples and summary["samples"] <= 0:
        summary["samples"] = len(samples)
        summary["server_check_seen"] = 1 if any(intish(sample.get("server_check_exists")) for sample in samples) else 0
        summary["ota_ruleset_seen"] = 1 if any(intish(sample.get("ota_ruleset_exists")) for sample in samples) else 0
        summary["mcfg_seen"] = 1 if any(intish(sample.get("mcfg_exists")) for sample in samples) else 0
        for name, field in (
            ("server_check", "first_server_check_file"),
            ("ota_ruleset", "first_ota_ruleset_file"),
            ("mcfg", "first_mcfg_file"),
        ):
            first = next((sample for sample in samples if intish(sample.get(f"{name}_exists"))), None)
            if first is not None:
                summary[f"{field}_monotonic_ms"] = intish(first.get("monotonic_ms"))
                summary[f"{field}_delta_ms"] = intish(first.get("delta_ms"))
    return {"summary": summary, "samples": samples}


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = parse_fields()
    details["helper_completion"] = collect_helper_completion(fields, handoff)
    details["cascade"] = collect_current_cascade(details)
    details["post_cal_indication"] = collect_current_post_cal(fields, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    trace["rfs_bridge"] = collect_rfs_bridge(fields)
    trace["served"] = bool(trace["rfs_bridge"].get("ok"))
    trace["served_nonzero"] = bool(trace["rfs_bridge"].get("fallback_nonzero"))
    details["wlanmdsp_trace"] = trace
    details["readwrite_bridge"] = collect_readwrite_bridge(fields)
    details["persist_rfs_bridge"] = collect_persist_bridge(fields)
    details["mcfg_readback"] = prev2046.collect_mcfg_readback(fields)
    details["tftp_ready_before_wlfw_vote"] = collect_tftp_ready(fields)
    details["readwrite_transition"] = collect_readwrite_transition(fields)
    order = collect_tftp_order(fields, details)
    records = order.get("records") if isinstance(order.get("records"), list) else []
    derived_summary = {
        "datagrams": len(records),
        "stored_records": len(records),
        "truncated_records": 0,
        "tftp_server": sum(1 for record in records if "tftp_server" in str(record.get("payload", "")).lower()),
        "server_check": sum(intish(record.get("server_check")) for record in records if isinstance(record, dict)),
        "ota_firewall": sum(intish(record.get("ota_firewall")) for record in records if isinstance(record, dict)),
        "mcfg": sum(intish(record.get("mcfg")) for record in records if isinstance(record, dict)),
        "wlanmdsp": sum(intish(record.get("wlanmdsp")) for record in records if isinstance(record, dict)),
        "fallback_wlanmdsp": sum(intish(record.get("fallback_wlanmdsp")) for record in records if isinstance(record, dict)),
        "rrq": sum(intish(record.get("rrq")) for record in records if isinstance(record, dict)),
        "oack": sum(intish(record.get("oack")) for record in records if isinstance(record, dict)),
        "data": 0,
        "ack": 0,
        "end_transfer": sum(intish(record.get("end_transfer")) for record in records if isinstance(record, dict)),
        "success": 0,
        "total_bytes": 1 if any("total-bytes" in str(record.get("payload", "")).lower() for record in records if isinstance(record, dict)) else 0,
        "total_bytes_4251884": sum(intish(record.get("total_bytes_4251884")) for record in records if isinstance(record, dict)),
        "enoent": sum(1 for record in records if "no such file" in str(record.get("payload", "")).lower()),
    }
    logdw = details.get("tftp_logdw") if isinstance(details.get("tftp_logdw"), dict) else {}
    logdw_summary = logdw.get("summary") if isinstance(logdw.get("summary"), dict) else {}
    logdw_summary.update(derived_summary)
    logdw["summary"] = logdw_summary
    logdw["records"] = records
    logdw["record_count"] = len(records)
    details["tftp_logdw"] = logdw
    details["pre_rrq_order"] = order
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev2046.ORIGINAL_V2035_CLASSIFY(handoff, hook, steps, details)
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    persist = details.get("persist_rfs_bridge") if isinstance(details.get("persist_rfs_bridge"), dict) else {}
    readback = details.get("mcfg_readback") if isinstance(details.get("mcfg_readback"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    order = details.get("pre_rrq_order") if isinstance(details.get("pre_rrq_order"), dict) else {}
    order_summary = order.get("summary") if isinstance(order.get("summary"), dict) else {}
    summary = prev2046.logdw_summary(details)
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    ready_gate = details.get("tftp_ready_before_wlfw_vote") if isinstance(details.get("tftp_ready_before_wlfw_vote"), dict) else {}
    transition = details.get("readwrite_transition") if isinstance(details.get("readwrite_transition"), dict) else {}
    transition_summary = transition.get("summary") if isinstance(transition.get("summary"), dict) else {}

    hook_ok = all(bool(item.get("ok")) for item in hook.values())
    cnss_pm_worker_ok = bool(
        intish(order.get("wlfw_start", {}).get("hit_count")) > 0
        and intish(order.get("wlfw_service_request", {}).get("hit_count")) > 0
        and bool(cascade.get("cnss_daemon_running"))
    )
    route_ok = bool(
        hook_ok
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(helper.get("ok"))
        and bool(bridge.get("ok"))
        and bool(readwrite.get("ok"))
        and prev2046.persist_ok(persist)
        and intish(readback.get("begin")) == 1
        and intish(order_summary.get("order_timestamps")) == 1
        and intish(ready_gate.get("begin")) == 1
        and bool(ready_gate.get("safe"))
        and intish(transition_summary.get("begin")) == 1
        and bool(transition_summary.get("safe"))
        and cnss_pm_worker_ok
        and intish(cascade.get("wlan_pd_up")) > 0
        and bool(cascade.get("post_up_hold_ge_30"))
    )
    wlan0 = intish(cascade.get("wlan0")) > 0
    fw_ready = intish(cascade.get("fw_ready")) > 0
    wlan_pd_up = intish(cascade.get("wlan_pd_up")) > 0
    server_check = intish(summary.get("server_check"))
    ota_firewall = intish(order_summary.get("ota_firewall"))
    wlanmdsp = intish(summary.get("wlanmdsp")) + intish(summary.get("fallback_wlanmdsp"))
    mcfg = intish(summary.get("mcfg"))
    datagrams = intish(summary.get("datagrams"))

    gate_open = intish(ready_gate.get("gate_open")) == 1
    server_check_file_seen = intish(transition_summary.get("server_check_seen")) == 1
    ota_ruleset_file_seen = intish(transition_summary.get("ota_ruleset_seen")) == 1
    mcfg_file_seen = intish(transition_summary.get("mcfg_seen")) == 1

    if not route_ok:
        label = "pre-wlanmdsp-rrq-order-route-regression"
        reason = "V2056 did not preserve rollback, route prerequisites, bridges, passive order timestamps, readwrite transition sampling, or long lower window"
        passed = False
    elif wlan0:
        label = "pre-wlanmdsp-rrq-order-wlan0-progress"
        reason = "native reached wlan0; stop before credentials/scan/connect until the dedicated Wi-Fi gate"
        passed = True
    elif fw_ready:
        label = "pre-wlanmdsp-rrq-order-fw-ready-progress"
        reason = "native reached WLAN firmware-ready progress"
        passed = True
    elif wlanmdsp > 0:
        label = "pre-wlanmdsp-rrq-order-wlanmdsp-requested"
        reason = "native entered the WLAN image request branch; the next gate is serve/transfer/FW-ready, not mcfg"
        passed = True
    elif server_check > 0 or ota_firewall > 0:
        label = "tftp-ready-pre-vote-android-branch-started-no-wlanmdsp"
        reason = "native entered Android's server_check/ota_firewall branch but did not request wlanmdsp"
        passed = True
    elif server_check_file_seen or ota_ruleset_file_seen:
        label = "readwrite-file-transition-seen-no-wlanmdsp"
        reason = "read-only file sampling saw the readwrite bootstrap file transition, but passive tftp logs still had no wlanmdsp request"
        passed = True
    elif not gate_open:
        label = "tftp-ready-pre-vote-gate-closed-no-android-branch"
        reason = "the bounded pre-vote wait did not prove tftp_server ready before the WLFW vote; no server_check/ota/wlanmdsp branch followed"
        passed = True
    elif mcfg > 0:
        label = "tftp-ready-pre-vote-mcfg-only-no-android-branch"
        reason = "tftp_server was ready before the WLFW vote, but the modem still emitted only mcfg traffic and skipped Android's server_check/ota_firewall/wlanmdsp branch"
        passed = True
    elif wlan_pd_up and datagrams == 0:
        label = "pre-wlanmdsp-rrq-order-wlan-pd-up-zero-tftp"
        reason = "native reached WLAN-PD UP but passive logdw saw no modem tftp branch"
        passed = True
    else:
        label = "pre-wlanmdsp-rrq-order-no-trigger"
        reason = "native route completed without WLAN image request or classified first-branch traffic"
        passed = True

    return {
        **base,
        "label": label,
        "decision": f"v2057-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "hook_ok": hook_ok,
        "helper_completion_ok": bool(helper.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "persist_rfs_ok": prev2046.persist_ok(persist),
        "mcfg_observer_ok": intish(readback.get("begin")) == 1,
        "cnss_pm_worker_ok": cnss_pm_worker_ok,
        "tftp_ready_gate_open": gate_open,
        "tftp_ready_safe": bool(ready_gate.get("safe")),
        "readwrite_transition_ok": intish(transition_summary.get("begin")) == 1 and bool(transition_summary.get("safe")),
        "server_check_file_seen": server_check_file_seen,
        "ota_ruleset_file_seen": ota_ruleset_file_seen,
        "mcfg_file_seen": mcfg_file_seen,
        "post_up_hold_ok": bool(cascade.get("post_up_hold_ge_30")),
        "order_timestamp_ok": intish(order_summary.get("order_timestamps")) == 1,
        "cap_bdf_cal_success": bool(
            post.get("cap_return_rc") == "0x0"
            and post.get("bdf_return_rc") == "0x0"
            and post.get("cal_return_rc") == "0x0"
        ),
        "server_check_seen": server_check > 0,
        "ota_firewall_seen": ota_firewall > 0,
        "wlanmdsp_seen": wlanmdsp > 0,
        "mcfg_seen": mcfg > 0,
        "datagrams": datagrams,
    }


def order_rows(details: dict[str, Any]) -> list[list[object]]:
    order = details.get("pre_rrq_order") if isinstance(details.get("pre_rrq_order"), dict) else {}
    summary = order.get("summary") if isinstance(order.get("summary"), dict) else {}
    return [
        ["tftp_sink_start", summary.get("start_monotonic_ms", 0), "delta=0", ""],
        ["first_tftp_relevant", summary.get("first_relevant_monotonic_ms", 0), summary.get("first_relevant_delta_ms", -1), ""],
        ["first_tftp_server", summary.get("first_tftp_server_monotonic_ms", 0), summary.get("first_tftp_server_delta_ms", -1), ""],
        ["first_server_check", summary.get("first_server_check_monotonic_ms", 0), summary.get("first_server_check_delta_ms", -1), ""],
        ["first_ota_firewall", summary.get("first_ota_firewall_monotonic_ms", 0), summary.get("first_ota_firewall_delta_ms", -1), ""],
        ["first_mcfg", summary.get("first_mcfg_monotonic_ms", 0), summary.get("first_mcfg_delta_ms", -1), ""],
        ["first_wlanmdsp", summary.get("first_wlanmdsp_monotonic_ms", 0), summary.get("first_wlanmdsp_delta_ms", -1), ""],
        ["cnss_wlfw_start", "", "", order.get("wlfw_start", {}).get("line", "")],
        ["cnss_wlfw_service_request", "", "", order.get("wlfw_service_request", {}).get("line", "")],
        ["wlan_pd_up", "", "", order.get("wlan_pd_up_line", "")],
    ]


def record_rows(details: dict[str, Any]) -> list[list[object]]:
    order = details.get("pre_rrq_order") if isinstance(details.get("pre_rrq_order"), dict) else {}
    records = order.get("records") if isinstance(order.get("records"), list) else []
    return [
        [
            f"{record.get('index', 0):03d}",
            record.get("delta_ms", -1),
            record.get("server_check", 0),
            record.get("ota_firewall", 0),
            record.get("mcfg", 0),
            record.get("wlanmdsp", 0),
            record.get("fallback_wlanmdsp", 0),
            record.get("rrq", 0),
            record.get("wrq", 0),
            record.get("payload", ""),
        ]
        for record in records[:32]
        if isinstance(record, dict)
    ]


def transition_rows(details: dict[str, Any]) -> list[list[object]]:
    transition = details.get("readwrite_transition") if isinstance(details.get("readwrite_transition"), dict) else {}
    samples = transition.get("samples") if isinstance(transition.get("samples"), list) else []
    return [
        [
            f"{sample.get('index', 0):03d}",
            sample.get("phase", ""),
            sample.get("delta_ms", -1),
            sample.get("server_check_exists", 0),
            sample.get("server_check_size", 0),
            sample.get("server_check_payload", ""),
            sample.get("ota_ruleset_exists", 0),
            sample.get("ota_ruleset_size", 0),
            sample.get("mcfg_exists", 0),
            sample.get("mcfg_size", 0),
            sample.get("mcfg_payload", ""),
        ]
        for sample in samples[:32]
        if isinstance(sample, dict)
    ]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    readwrite = details["readwrite_bridge"]
    persist = details["persist_rfs_bridge"]
    post = details["post_cal_indication"]
    ready_gate = details["tftp_ready_before_wlfw_vote"]
    transition = details["readwrite_transition"]
    transition_summary = transition["summary"]
    summary = prev2046.logdw_summary(details)
    order = details["pre_rrq_order"]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"hook={classification.get('hook_ok')} order_ts={classification.get('order_timestamp_ok')} holder={details['holder_opened']} cnss={cascade.get('cnss_daemon_running')}"],
        ["readonly_fallback", classification.get("rfs_bridge_ok"), f"path={bridge.get('fallback_path')} size={bridge.get('fallback_size')} open_rc={bridge.get('fallback_open_rc')}"],
        ["readwrite", classification.get("readwrite_bridge_ok"), f"server_check_file={readwrite.get('server_check_exists')} tmpfs={readwrite.get('readwrite_tmpfs_requested')} path={readwrite.get('readwrite_path')}"],
        ["persist", classification.get("persist_rfs_ok"), f"rfs={persist.get('rfs_path')} hlos={persist.get('hlos_path')}"],
        ["tftp_ready", classification.get("tftp_ready_gate_open"), f"ready={ready_gate.get('ready')} safe={classification.get('tftp_ready_safe')} elapsed_ms={ready_gate.get('elapsed_ms')} sockets={ready_gate.get('socket_fd_count')} early_logdw={ready_gate.get('logdw_datagrams')}"],
        ["readwrite_transition", classification.get("readwrite_transition_ok"), f"server_check_file={classification.get('server_check_file_seen')} ota_file={classification.get('ota_ruleset_file_seen')} mcfg_file={classification.get('mcfg_file_seen')} samples={transition_summary.get('samples')}"],
        ["cascade", "", f"wlan_pd={cascade.get('wlan_pd_up')} icnss_qmi={cascade.get('icnss_qmi_connected')} fw_ready={cascade.get('fw_ready')} wlan0={cascade.get('wlan0')} post_up={cascade.get('post_up_hold_sec')}"],
        ["tftp_branch", "", f"datagrams={summary.get('datagrams')} server_check={summary.get('server_check')} ota={summary.get('ota_firewall')} mcfg={summary.get('mcfg')} wlanmdsp={summary.get('wlanmdsp')} fallback={summary.get('fallback_wlanmdsp')} 4251884={summary.get('total_bytes_4251884')}"],
        ["cnss_order", "", f"wlfw_start={order['wlfw_start'].get('trace_ts')} wlfw_service_request={order['wlfw_service_request'].get('trace_ts')} wlan_pd_up={order.get('wlan_pd_up_ts')}"],
        ["cap_bdf_cal", classification.get("cap_bdf_cal_success"), f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
    ]
    return "\n".join([
        "# Native Init V2057 Readwrite Transition Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2057`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], matrix_rows),
        "",
        "## Native Ordering",
        "",
        markdown_table(["event", "monotonic_ms", "delta_ms", "line"], order_rows(details)),
        "",
        "## TFTP Readiness Gate",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", ready_gate.get("mode", "")],
                ["safe", ready_gate.get("safe", "")],
                ["ready", ready_gate.get("ready", "")],
                ["gate_open", ready_gate.get("gate_open", "")],
                ["elapsed_ms", ready_gate.get("elapsed_ms", "")],
                ["socket_fd_count", ready_gate.get("socket_fd_count", "")],
                ["fd_count", ready_gate.get("fd_count", "")],
                ["early_logdw_datagrams", ready_gate.get("logdw_datagrams", "")],
                ["early_server_check", ready_gate.get("logdw_server_check", "")],
                ["early_ota_firewall", ready_gate.get("logdw_ota_firewall", "")],
                ["early_wlanmdsp", ready_gate.get("logdw_wlanmdsp", "")],
                ["early_mcfg_seen", ready_gate.get("logdw_mcfg_seen", "")],
            ],
        ),
        "",
        "## Readwrite Transitions",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["mode", transition_summary.get("mode", "")],
                ["safe", transition_summary.get("safe", "")],
                ["samples", transition_summary.get("samples", "")],
                ["dropped", transition_summary.get("dropped", "")],
                ["server_check_seen", transition_summary.get("server_check_seen", "")],
                ["server_check_delta_ms", transition_summary.get("first_server_check_file_delta_ms", "")],
                ["ota_ruleset_seen", transition_summary.get("ota_ruleset_seen", "")],
                ["ota_ruleset_delta_ms", transition_summary.get("first_ota_ruleset_file_delta_ms", "")],
                ["mcfg_seen", transition_summary.get("mcfg_seen", "")],
                ["mcfg_delta_ms", transition_summary.get("first_mcfg_file_delta_ms", "")],
            ],
        ),
        "",
        markdown_table(
            ["idx", "phase", "delta_ms", "server_check", "server_check_size", "server_check_payload", "ota", "ota_size", "mcfg", "mcfg_size", "mcfg_payload"],
            transition_rows(details) or [["none", "", -1, 0, 0, "", 0, 0, 0, 0, ""]],
        ),
        "",
        "## TFTP Records",
        "",
        markdown_table(
            ["idx", "delta_ms", "server_check", "ota", "mcfg", "wlanmdsp", "fallback", "rrq", "wrq", "payload"],
            record_rows(details) or [["none", -1, 0, 0, 0, 0, 0, 0, 0, ""]],
        ),
        "",
        "## Branch",
        "",
        "- `mcfg` is not treated as the WLAN trigger; it is only a reachability marker.",
        "- Android's normal branch is `server_check.txt` -> `ota_firewall/ruleset` -> `wlanmdsp.mbn`; this report classifies whether native enters that branch.",
        "- If native remains `mcfg-only`, the next target is the modem-side condition that selects the Android WLAN image-request branch after cnss/PM prerequisites, not mcfg readback.",
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, QMI payload send, or `tftp_server` ptrace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2056 test-boot flash-handoff, namespace-local fallback readonly/readwrite RFS bridges, namespace-local persist-RFS tmpfs mirrors, private tmp-root `/dev/socket/logdw`, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2046() -> None:
    prev2046.CYCLE = CYCLE
    prev2046.OUT_DIR = OUT_DIR
    prev2046.HANDOFF_DIR = HANDOFF_DIR
    prev2046.HANDOFF_REPORT = HANDOFF_REPORT
    prev2046.REPORT_PATH = REPORT_PATH
    prev2046.V2045_OUT = V2056_OUT
    prev2046.V2045_INIT = V2056_INIT
    prev2046.V2045_BOOT = V2056_BOOT
    prev2046.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2046.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2046.TEST_LOG_PATH = TEST_LOG_PATH
    prev2046.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2046.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2046.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2046.artifact_hook_check = artifact_hook_check
    prev2046.collect_details = collect_details
    prev2046.classify = classify
    prev2046.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2046()
    return prev2046.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
