#!/usr/bin/env python3
"""V1996 single-child pd-mapper syscall-trace handoff."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_rfs_bridge_wlanmdsp_handoff_v1992 as prev1992


CYCLE = "V1996"
OUT_DIR = prev1992.prev.repo_path("tmp/wifi/v1996-pd-mapper-syscall-trace-handoff")
HANDOFF_DIR = OUT_DIR / "v1995-handoff"
HANDOFF_REPORT = OUT_DIR / "v1995-handoff-report.md"
REPORT_PATH = prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V1996_PD_MAPPER_SYSCALL_TRACE_HANDOFF_2026-06-04.md"
)
V1995_OUT = prev1992.prev.repo_path("tmp/wifi/v1995-pd-mapper-syscall-trace-test-boot")
V1995_INIT = V1995_OUT / "init_v1995_pd_mapper_syscall_trace"
V1995_BOOT = V1995_OUT / "boot_linux_v1995_pd_mapper_syscall_trace.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1995/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.180 (v1995-pd-mapper-syscall-trace)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1995.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1995.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1995-helper.result"

ORIGINAL_PATCH_PREV_MODULE = prev1992.patch_prev_module
ORIGINAL_CLASSIFY = prev1992.classify
ORIGINAL_RENDER_REPORT = prev1992.render_report
ORIGINAL_COLLECT_DETAILS = prev1992.prev.collect_details


def rel(path: Path) -> str:
    return prev1992.prev.rel(path)


def read_helper_text() -> str:
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


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith("A90_EXECNS_PATH_"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def syscall_blocks(text: str, label: str, limit: int = 10) -> list[str]:
    escaped = re.escape(label)
    pattern = re.compile(
        rf"A90_EXECNS_PATH_({escaped}(?:_stall_task_[0-9]+)?_syscall)_BEGIN[^\n]*\n"
        rf"(.*?)\nA90_EXECNS_PATH_\1_END",
        re.S,
    )
    blocks: list[str] = []
    for match in pattern.finditer(text):
        body = " ".join(line.strip() for line in match.group(2).splitlines() if line.strip())
        if body:
            blocks.append(body[:240])
        if len(blocks) >= limit:
            break
    return blocks


def collect_producer_child_snapshot() -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    phases = ("after_holder_start", "after_post_listener_window")
    children = ("pd_mapper", "tftp_server")
    result: dict[str, Any] = {
        "text_present": bool(text),
        "phases": {},
        "raw_marker_count": text.count("wlan_pd_producer_child_snapshot."),
        "observer_contract": {
            "no_qmi_send": True,
            "no_qrtr_readback": True,
            "single_ptrace_child": "pd_mapper",
        },
    }
    for phase in phases:
        phase_info: dict[str, Any] = {
            "target_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.target_count"))),
            "alive_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.alive_count"))),
            "snapshot_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.snapshot_count"))),
            "children": {},
        }
        for child in children:
            label = f"wlan_pd_producer_{phase}_{child}"
            child_info = {
                "pid": fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.pid", ""),
                "alive": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.alive"))),
                "state": fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.state", ""),
                "fd_socket_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.fd_links.socket_count"))),
                "fd_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.fd_links.count"))),
                "stall_snapshot": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_snapshot.task_captured"))),
                "syscall_captured": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_snapshot.syscall_captured"))),
                "task_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_tasks.count"))),
                "syscall_blocks": syscall_blocks(text, label, limit=6),
            }
            phase_info["children"][child] = child_info
        result["phases"][phase] = phase_info
    result["ok"] = all(
        (result["phases"][phase]["target_count"] >= 2 and result["phases"][phase]["snapshot_count"] >= 2)
        for phase in phases
    )
    result["both_alive_after_holder"] = (
        result["phases"]["after_holder_start"]["children"]["pd_mapper"]["alive"] > 0
        and result["phases"]["after_holder_start"]["children"]["tftp_server"]["alive"] > 0
    )
    result["both_alive_after_window"] = (
        result["phases"]["after_post_listener_window"]["children"]["pd_mapper"]["alive"] > 0
        and result["phases"]["after_post_listener_window"]["children"]["tftp_server"]["alive"] > 0
    )
    return result


def collect_helper_completion(handoff: dict[str, Any]) -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    rollback = handoff.get("post_rollback_verification") if isinstance(handoff.get("post_rollback_verification"), dict) else {}
    result = {
        "text_present": bool(text),
        "result_file_version": fields.get("result_file_version", ""),
        "version_ok": fields.get("result_file_version") == "a90_android_execns_probe v367",
        "probe_run_rc": fields.get("probe_run_rc", ""),
        "probe_run_rc_ok": int(prev1992.prev.intish(fields.get("probe_run_rc"))) == 0,
        "child_exit_code": fields.get("child_exit_code", ""),
        "child_exit_code_ok": int(prev1992.prev.intish(fields.get("child_exit_code"))) == 0,
        "child_signal": fields.get("child_signal", ""),
        "child_signal_ok": int(prev1992.prev.intish(fields.get("child_signal"))) == 0,
        "timed_out": int(prev1992.prev.intish(fields.get("timed_out"))),
        "test_flash_ok": bool(handoff.get("test_flash_ok")),
        "rollback_version_ok": bool(rollback.get("version_ok")),
        "rollback_selftest_fail_zero": bool(rollback.get("selftest_fail_zero")),
    }
    result["ok"] = (
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


def collect_pd_mapper_syscall_trace() -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    record_pattern = re.compile(r"^wlan_pd_pd_mapper_trace\.syscall\.pd_mapper\.record_(\d+)\.(.+)$")
    records: dict[int, dict[str, str]] = {}
    for key, value in fields.items():
        match = record_pattern.match(key)
        if not match:
            continue
        index = int(match.group(1))
        records.setdefault(index, {})[match.group(2)] = value

    record_list = [records[index] for index in sorted(records)]
    payload_records: list[dict[str, str]] = []
    recv_payload_records: list[dict[str, str]] = []
    send_payload_records: list[dict[str, str]] = []
    qipcrtr_records: list[dict[str, str]] = []
    first_records: list[str] = []
    name_counts: dict[str, int] = {}

    for index, record in zip(sorted(records), record_list):
        name = record.get("name", "")
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
        has_payload = any(key.endswith(".hex") and bool(value) for key, value in record.items())
        has_qipcrtr = any(value == "AF_QIPCRTR" for value in record.values())
        if has_payload:
            payload_records.append(record)
            if name in {"recvmsg", "recvfrom"}:
                recv_payload_records.append(record)
            if name in {"sendmsg", "sendto"}:
                send_payload_records.append(record)
        if has_qipcrtr:
            qipcrtr_records.append(record)
        if len(first_records) < 10:
            fd_target = record.get("fd.target") or record.get("ret_fd.target") or ""
            detail = fd_target
            for key in (
                "msghdr_sockaddr.family_name",
                "msghdr_sockaddr.qrtr.node",
                "msghdr_sockaddr.qrtr.port",
                "sockaddr.family_name",
                "sockaddr.qrtr.node",
                "sockaddr.qrtr.port",
            ):
                if key in record:
                    detail = f"{detail} {key}={record[key]}".strip()
            first_records.append(f"record_{index:03d} {name} ret={record.get('ret', '')} {detail}".strip())

    summary = {
        "compiled": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_pd_mapper_syscall_trace.compiled"))),
        "single_child": fields.get("wifi_companion_start.wlan_pd_producer_pd_mapper_syscall_trace.single_child", ""),
        "late_attach_contract": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_pd_mapper_syscall_trace.late_attach"))),
        "no_qrtr_send": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_pd_mapper_syscall_trace.no_qrtr_send"))),
        "no_qmi_payload_send": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_pd_mapper_syscall_trace.no_qmi_payload_send"))),
        "late_available": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.available"))),
        "late_attach_rc": fields.get("wlan_pd_pd_mapper_trace.late_attach.attach_rc", ""),
        "late_detach_rc": fields.get("wlan_pd_pd_mapper_trace.late_attach.detach_rc", ""),
        "late_no_qrtr_send": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.no_qrtr_send"))),
        "late_no_qmi_payload_send": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.no_qmi_payload_send"))),
        "late_duration_ms": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.duration_ms"))),
        "late_syscall_stop_count": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.syscall_stop_count"))),
        "late_syscall_record_count": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.syscall_record_count"))),
        "late_syscall_trace_truncated": int(prev1992.prev.intish(fields.get("wlan_pd_pd_mapper_trace.late_attach.syscall_trace_truncated"))),
        "traced": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.traced"))),
        "trace_syscalls": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.trace_syscalls"))),
        "syscall_trace_started": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.syscall_trace_started"))),
        "syscall_trace_stop_limited": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.syscall_trace_stop_limited"))),
        "syscall_stop_count": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.syscall_stop_count"))),
        "syscall_record_count": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.syscall_record_count"))),
        "syscall_trace_truncated": int(prev1992.prev.intish(fields.get("pm_service_trigger_observer.child.pd_mapper.syscall_trace_truncated"))),
    }
    return {
        "text_present": bool(text),
        "summary": summary,
        "record_count": len(record_list),
        "name_counts": name_counts,
        "payload_record_count": len(payload_records),
        "recv_payload_record_count": len(recv_payload_records),
        "send_payload_record_count": len(send_payload_records),
        "qipcrtr_record_count": len(qipcrtr_records),
        "first_records": first_records,
        "compiled_ok": (
            summary["compiled"] == 1
            and summary["single_child"] == "pd_mapper"
            and summary["late_attach_contract"] == 1
        ),
        "safety_contract_ok": (
            summary["no_qrtr_send"] == 1
            and summary["no_qmi_payload_send"] == 1
            and summary["late_no_qrtr_send"] == 1
            and summary["late_no_qmi_payload_send"] == 1
        ),
        "trace_active": summary["late_attach_rc"] == "0" or len(record_list) > 0,
        "inbound_query_seen": len(recv_payload_records) > 0,
        "outbound_payload_seen": len(send_payload_records) > 0,
        "qipcrtr_seen": len(qipcrtr_records) > 0,
    }


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1995",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v367",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "wlan_pd_producer_pd_mapper_syscall_trace.compiled=%d",
        "wlan_pd_producer_pd_mapper_syscall_trace.single_child=pd_mapper",
        "wlan_pd_producer_pd_mapper_syscall_trace.late_attach=1",
        "wlan_pd_producer_pd_mapper_syscall_trace.no_qrtr_send=1",
        "wlan_pd_producer_pd_mapper_syscall_trace.no_qmi_payload_send=1",
        "wlan_pd_pd_mapper_trace",
        "sendmsg",
        "recvmsg",
        "AF_QIPCRTR",
        "wlan_pd_firmware_serve_gate.requested_wlanmdsp=%d",
        "tftp_server",
        "pd-mapper",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1995_INIT, init_required), (V1995_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in init_forbidden if path == V1995_INIT and token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    details["helper_completion"] = collect_helper_completion(handoff)
    details["producer_child_snapshot"] = collect_producer_child_snapshot()
    details["pd_mapper_syscall_trace"] = collect_pd_mapper_syscall_trace()
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    producer = details.get("producer_child_snapshot") if isinstance(details.get("producer_child_snapshot"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    pd_trace = details.get("pd_mapper_syscall_trace") if isinstance(details.get("pd_mapper_syscall_trace"), dict) else {}
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("combined"))
        and bool(base.get("rfs_bridge_ok"))
        and bool(helper.get("ok"))
        and bool(pd_trace.get("compiled_ok"))
        and bool(pd_trace.get("safety_contract_ok"))
    )
    if not route_ok:
        return {
            **base,
            "decision": f"v1996-{base.get('label', 'handoff-failed')}-rollback-blocked",
            "pass": False,
            "helper_completion_ok": bool(helper.get("ok")),
            "producer_child_snapshot_ok": bool(producer.get("ok")),
            "pd_mapper_trace_ok": bool(pd_trace.get("compiled_ok")) and bool(pd_trace.get("safety_contract_ok")),
            "pd_mapper_trace_active": bool(pd_trace.get("trace_active")),
        }
    if not pd_trace.get("trace_active"):
        label = "native-pd-mapper-trace-missing"
        return {
            **base,
            "label": label,
            "decision": f"v1996-{label}-rollback-blocked",
            "pass": False,
            "reason": "V1995 compiled the pd-mapper trace contract but captured no pd-mapper syscall trace records",
            "helper_completion_ok": True,
            "producer_child_snapshot_ok": bool(producer.get("ok")),
            "pd_mapper_trace_ok": True,
            "pd_mapper_trace_active": False,
        }
    if trace.get("requested") or base.get("publication_progress"):
        label = "native-pd-mapper-query-and-wlanmdsp-progress"
        return {
            **base,
            "label": label,
            "decision": f"v1996-{label}-rollback-pass",
            "pass": True,
            "reason": "V1995 single-child pd-mapper trace ran and native reached the wlanmdsp request/publication edge; stop before HAL/scan/connect",
            "helper_completion_ok": True,
            "producer_child_snapshot_ok": bool(producer.get("ok")),
            "pd_mapper_trace_ok": True,
            "pd_mapper_trace_active": True,
        }
    if pd_trace.get("inbound_query_seen"):
        label = "native-pd-mapper-query-seen-no-wlanmdsp-request"
        return {
            **base,
            "label": label,
            "decision": f"v1996-{label}-rollback-pass",
            "pass": True,
            "reason": "pd-mapper received QRTR payload before any wlanmdsp request, so the stall is after PD mapping traffic and before the modem's PD image request",
            "helper_completion_ok": True,
            "producer_child_snapshot_ok": bool(producer.get("ok")),
            "pd_mapper_trace_ok": True,
            "pd_mapper_trace_active": True,
        }
    label = "native-pd-mapper-no-modem-query-before-wlanmdsp"
    return {
        **base,
        "label": label,
        "decision": f"v1996-{label}-rollback-pass",
        "pass": True,
        "reason": "pd-mapper stayed traced without inbound QRTR payload and the modem still never requested wlanmdsp.mbn; the stall is before PD mapping/query reaches AP pd-mapper",
        "helper_completion_ok": True,
        "producer_child_snapshot_ok": bool(producer.get("ok")),
        "pd_mapper_trace_ok": True,
        "pd_mapper_trace_active": True,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    light = trace["light_observer"]
    helper = details["helper_completion"]
    producer = details["producer_child_snapshot"]
    pd_trace = details["pd_mapper_syscall_trace"]
    pd_summary = pd_trace["summary"]
    android = details["android_v1982"]
    rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper_completion", classification.get("helper_completion_ok"), f"version={helper['result_file_version']} probe_rc={helper['probe_run_rc']} child_exit={helper['child_exit_code']} timed_out={helper['timed_out']}"],
        ["rfs_bridge", classification.get("rfs_bridge_ok"), f"exact_exists={bridge['exact_exists']} nonzero={bridge['exact_nonzero']} open_rc={bridge['exact_open_rc']} source_nonzero={bridge['source_asset_nonzero']} sda29_write={bridge['sda29_write']}"],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["producer_alive", producer.get("both_alive_after_window"), f"holder={producer.get('both_alive_after_holder')} window={producer.get('both_alive_after_window')}"],
        ["pd_mapper_trace", classification.get("pd_mapper_trace_active"), f"compiled={pd_summary['compiled']} late={pd_summary['late_attach_contract']} attach_rc={pd_summary['late_attach_rc']} detach_rc={pd_summary['late_detach_rc']} records={pd_trace['record_count']} late_records={pd_summary['late_syscall_record_count']} late_stops={pd_summary['late_syscall_stop_count']} late_ms={pd_summary['late_duration_ms']} truncated={pd_summary['late_syscall_trace_truncated']}"],
        ["pd_mapper_payloads", pd_trace["inbound_query_seen"], f"inbound_recv={pd_trace['recv_payload_record_count']} outbound_send={pd_trace['send_payload_record_count']} total_payload={pd_trace['payload_record_count']} qipcrtr={pd_trace['qipcrtr_record_count']} names={pd_trace['name_counts']}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["wlanmdsp_request", trace["requested"], f"field={trace['requested_field']} tftp_lines={trace['tftp_wlanmdsp_lines']} failures={trace['wlanmdsp_failure_lines']}"],
        ["wlanmdsp_serve_load", bool(trace["requested"] and trace["served"]), f"available_nonzero={trace['served_nonzero']} pil_load={trace['pil_load_lines']} wlan_pd_up={trace['wlan_pd_up_lines']} wlfw69={trace['wlfw69_lines']} wlan0={trace['wlan0_lines']}"],
        ["android_v1982", android.get("requested_wlanmdsp", ""), f"wlan_pd={android.get('wlan_pd_up')} BDF={android.get('bdf')} wlan0={android.get('wlan0')} lines={android.get('wlanmdsp_line_count')}"],
    ]
    phase_lines: list[str] = []
    for phase, phase_info in producer["phases"].items():
        for child, child_info in phase_info["children"].items():
            phase_lines.append(
                f"- `{phase}/{child}` alive `{child_info['alive']}` state `{child_info['state']}` fd_socket_count `{child_info['fd_socket_count']}` task_count `{child_info['task_count']}`"
            )
            for block in child_info["syscall_blocks"][:2]:
                phase_lines.append(f"- `{phase}/{child}` syscall `{block}`")
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1996 PD-Mapper Syscall Trace Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1996`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev1992.prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "",
        "## First PD-Mapper Trace Records",
        "",
        *(f"- `{line}`" for line in pd_trace["first_records"]),
        *([] if pd_trace["first_records"] else ["- `none`"]),
        "",
        "## Producer Child Snapshot",
        "",
        *phase_lines,
        "",
        "## First Native Wlanmdsp Lines",
        "",
        *(f"- `{line}`" for line in trace["first_wlanmdsp_lines"]),
        *([] if trace["first_wlanmdsp_lines"] else ["- `none`"]),
        "",
        "## Branch",
        "",
        "- `native-pd-mapper-no-modem-query-before-wlanmdsp`: modem never reaches AP `pd-mapper` before the missing WLAN image request.",
        "- `native-pd-mapper-query-seen-no-wlanmdsp-request`: PD mapping traffic exists, but the modem still stalls before tftp `wlanmdsp.mbn`.",
        "- `native-pd-mapper-query-and-wlanmdsp-progress`: request/publication edge appeared; stop before HAL/scan/connect and continue downstream.",
        "",
        "## Android Comparator",
        "",
        f"- Report: `{android.get('report', rel(prev1992.prev.ANDROID_V1982_REPORT))}`",
        f"- Timeline: WLAN-PD UP `{android.get('wlan_pd_up')}`, BDF `{android.get('bdf')}`, wlan0 `{android.get('wlan0')}`.",
        f"- Request evidence: requested_wlanmdsp `{android.get('requested_wlanmdsp')}`, wlanmdsp line count `{android.get('wlanmdsp_line_count')}`.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.",
        "- The only ptrace was the bounded single-child syscall payload trace of stock `pd-mapper`; no AP-side multi-strace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1995 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev1992.CYCLE = CYCLE
    prev1992.OUT_DIR = OUT_DIR
    prev1992.HANDOFF_DIR = HANDOFF_DIR
    prev1992.HANDOFF_REPORT = HANDOFF_REPORT
    prev1992.REPORT_PATH = REPORT_PATH
    prev1992.V1991_OUT = V1995_OUT
    prev1992.V1991_INIT = V1995_INIT
    prev1992.V1991_BOOT = V1995_BOOT
    prev1992.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1992.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1992.TEST_LOG_PATH = TEST_LOG_PATH
    prev1992.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1992.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1992.artifact_hook_check = artifact_hook_check
    prev1992.classify = classify
    prev1992.render_report = render_report
    ORIGINAL_PATCH_PREV_MODULE()
    prev1992.prev.collect_details = collect_details


def main(argv: list[str] | None = None) -> int:
    prev1992.patch_prev_module = patch_prev_module
    return prev1992.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
