#!/usr/bin/env python3
"""V2013 rollbackable handoff for the long tftp data-window trace."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_post_cal_indication_handoff_v2009 as prev2009


CYCLE = "V2013"
OUT_DIR = prev2009.prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2013-tftp-data-window-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2012-handoff"
HANDOFF_REPORT = OUT_DIR / "v2012-handoff-report.md"
REPORT_PATH = prev2009.prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2013_TFTP_DATA_WINDOW_HANDOFF_2026-06-04.md"
)
V2012_OUT = prev2009.prev2007.prev2000.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2012-tftp-data-window-test-boot"
)
V2012_INIT = V2012_OUT / "init_v2012_tftp_data_window"
V2012_BOOT = V2012_OUT / "boot_linux_v2012_tftp_data_window.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2012/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.188 (v2012-tftp-data-window)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2012.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2012.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2012-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v375"
V2013_POST_BOOT_HOLD_SEC = 190.0

prev2007 = prev2009.prev2007
prev2000 = prev2009.prev2000
prev1998 = prev2009.prev1998
ORIGINAL_PATCH_PREV_MODULE = prev2009.ORIGINAL_PATCH_PREV_MODULE
ORIGINAL_COLLECT_DETAILS = prev2009.ORIGINAL_COLLECT_DETAILS


IND_EVENTS = prev2009.IND_EVENTS


def rel(path: Path) -> str:
    return prev2009.rel(path)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    return prev2009.event(fields, name)


def hit(events: dict[str, dict[str, str]], name: str) -> int:
    return prev2009.hit(events, name)


def first_event_value(data: dict[str, str], *keys: str) -> str:
    return prev2009.first_event_value(data, *keys)


def is_zero(value: str) -> bool:
    return prev2009.is_zero(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2012",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "--timeout-sec",
        "75",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
        "--pm-observer-private-cnss-daemon-sdx50m",
        "--private-cnss-daemon-path",
    )
    boot_required = (
        *init_required,
        EXPECTED_HELPER_VERSION,
        "sockaddr_len",
        "wlfw_cal_report_return",
        "wlfw_worker_cal_only_call",
        "wlfw_worker_done_signal",
        "wlfw_qmi_ind_cb_entry",
        "wlfw_handle_ind_entry",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=%d",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.single_child=tftp_server",
    )
    boot_forbidden: tuple[str, ...] = ()
    checks: dict[str, Any] = {}
    for path, required in ((V2012_INIT, init_required), (V2012_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2012_INIT else boot_forbidden
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_post_cal(fields: dict[str, str]) -> dict[str, Any]:
    post_bdf_tail = prev2007.collect_post_bdf_tail(fields)
    ind_events = {name: event(fields, name) for name in IND_EVENTS}
    return {
        **post_bdf_tail,
        "ind_events": ind_events,
        "worker_cal_rc": first_event_value(ind_events["wlfw_worker_cal_only_retcheck"], "rc"),
        "first_ind_msg_id": first_event_value(ind_events["wlfw_qmi_ind_cb_entry"], "msg_id"),
        "first_ind_payload_len": first_event_value(ind_events["wlfw_qmi_ind_cb_entry"], "payload_len"),
        "first_handle_type": first_event_value(ind_events["wlfw_handle_ind_type"], "ind_type"),
        "first_handle_0x28_status": first_event_value(ind_events["wlfw_handle_ind_type_0x28"], "fw_status"),
    }


def words_from_hex(hex_text: str) -> list[str]:
    if len(hex_text) % 8:
        return []
    try:
        data = bytes.fromhex(hex_text)
    except ValueError:
        return []
    words: list[str] = []
    for index in range(0, min(len(data), 32), 4):
        words.append(f"0x{int.from_bytes(data[index:index + 4], 'little'):x}")
    return words


def bytes_from_hex(hex_text: str) -> bytes:
    if not hex_text or len(hex_text) % 2:
        return b""
    try:
        return bytes.fromhex(hex_text)
    except ValueError:
        return b""


def decode_tftp_request(payload: bytes) -> tuple[int, str, str]:
    if len(payload) < 4:
        return 0, "", ""
    opcode = int.from_bytes(payload[:2], "big")
    if opcode not in {1, 2}:
        return opcode, "", ""
    tail = payload[2:]
    first_nul = tail.find(b"\0")
    if first_nul < 0:
        return opcode, "", ""
    second = tail[first_nul + 1:]
    second_nul = second.find(b"\0")
    path = tail[:first_nul].decode("ascii", "replace")
    mode = second[:second_nul if second_nul >= 0 else len(second)].decode("ascii", "replace")
    return opcode, path, mode


def collect_tftp_syscall_trace() -> dict[str, Any]:
    base = prev1998.collect_tftp_syscall_trace()
    text = prev1998.read_helper_text()
    fields = prev1998.parse_fields(text)
    record_pattern = re.compile(r"^wlan_pd_tftp_server_trace\.syscall\.tftp_server\.record_(\d+)\.(.+)$")
    records: dict[int, dict[str, str]] = {}
    for key, value in fields.items():
        match = record_pattern.match(key)
        if not match:
            continue
        records.setdefault(int(match.group(1)), {})[match.group(2)] = value

    source_family_counts: dict[str, int] = {}
    source_nodes: dict[str, int] = {}
    source_ports: dict[str, int] = {}
    recvfrom_source_records = 0
    recvfrom_qrtr_source_records = 0
    qrtr_control_records = 0
    qrtr_del_client_records = 0
    qrtr_control_ports: dict[str, int] = {}
    tftp_data_records = 0
    tftp_rrq_records = 0
    tftp_wrq_records = 0
    tftp_data_paths: dict[str, int] = {}
    first_source_records: list[str] = []
    first_payload_words: list[str] = []
    first_control_records: list[str] = []
    first_data_records: list[str] = []
    for index in sorted(records):
        record = records[index]
        if record.get("name") != "recvfrom":
            continue
        family = record.get("sockaddr.family_name", "")
        if family:
            recvfrom_source_records += 1
            source_family_counts[family] = source_family_counts.get(family, 0) + 1
            if family == "AF_QIPCRTR":
                recvfrom_qrtr_source_records += 1
        node = record.get("sockaddr.qrtr.node", "")
        port = record.get("sockaddr.qrtr.port", "")
        if node:
            source_nodes[node] = source_nodes.get(node, 0) + 1
        if port:
            source_ports[port] = source_ports.get(port, 0) + 1
        payload = record.get("payload.hex", "")
        payload_bytes = bytes_from_hex(payload)
        if family == "AF_QIPCRTR" and node == "1" and port == "4294967294" and len(payload_bytes) >= 12:
            words = [int.from_bytes(payload_bytes[offset:offset + 4], "little") for offset in range(0, min(len(payload_bytes), 20), 4)]
            command = words[0] if words else 0
            client_node = words[1] if len(words) > 1 else 0
            client_port = words[2] if len(words) > 2 else 0
            qrtr_control_records += 1
            qrtr_control_ports[str(client_port)] = qrtr_control_ports.get(str(client_port), 0) + 1
            if command == 6:
                qrtr_del_client_records += 1
            if len(first_control_records) < 12:
                first_control_records.append(
                    f"record_{index:03d} cmd={command} client_node={client_node} client_port={client_port}"
                )
        elif family == "AF_QIPCRTR" and payload_bytes:
            opcode, path, mode = decode_tftp_request(payload_bytes)
            if path:
                tftp_data_records += 1
                if opcode == 1:
                    tftp_rrq_records += 1
                elif opcode == 2:
                    tftp_wrq_records += 1
                tftp_data_paths[path] = tftp_data_paths.get(path, 0) + 1
                if len(first_data_records) < 12:
                    opname = "RRQ" if opcode == 1 else "WRQ" if opcode == 2 else str(opcode)
                    first_data_records.append(
                        f"record_{index:03d} {opname} node={node} port={port} path={path} mode={mode}"
                    )
        if payload and len(first_payload_words) < 8:
            first_payload_words.append(f"record_{index:03d} {' '.join(words_from_hex(payload))}")
        if len(first_source_records) < 12:
            first_source_records.append(
                f"record_{index:03d} ret={record.get('ret', '')} fd={record.get('fd.target', '')} "
                f"family={family or 'none'} node={node or 'none'} port={port or 'none'} "
                f"socklen={record.get('sockaddr_len.value', '')}/{record.get('sockaddr_len.effective_len', '')}"
            )

    base.update({
        "recvfrom_source_record_count": recvfrom_source_records,
        "recvfrom_qrtr_source_record_count": recvfrom_qrtr_source_records,
        "qrtr_control_record_count": qrtr_control_records,
        "qrtr_del_client_record_count": qrtr_del_client_records,
        "qrtr_control_ports": qrtr_control_ports,
        "tftp_data_record_count": tftp_data_records,
        "tftp_rrq_record_count": tftp_rrq_records,
        "tftp_wrq_record_count": tftp_wrq_records,
        "tftp_data_paths": tftp_data_paths,
        "tftp_data_wlanmdsp": any("wlanmdsp" in path.lower() for path in tftp_data_paths),
        "tftp_data_any_named_request": bool(tftp_data_paths),
        "source_family_counts": source_family_counts,
        "source_nodes": source_nodes,
        "source_ports": source_ports,
        "first_source_records": first_source_records,
        "first_payload_words": first_payload_words,
        "first_control_records": first_control_records,
        "first_data_records": first_data_records,
    })
    return base


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    fields = prev1998.parse_fields(prev1998.read_helper_text())
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    if helper:
        helper["version_ok"] = helper.get("result_file_version") == EXPECTED_HELPER_VERSION
        helper["ok"] = bool(
            helper.get("text_present")
            and helper.get("version_ok")
            and helper.get("probe_run_rc_ok")
            and helper.get("child_exit_code_ok")
            and helper.get("child_signal_ok")
            and helper.get("test_flash_ok")
            and helper.get("rollback_version_ok")
            and helper.get("rollback_selftest_fail_zero")
        )
    details["cascade"] = prev2000.collect_cascade(fields, details)
    details["post_cal_indication"] = collect_post_cal(fields)
    details["tftp_summary_fields"] = prev1998.collect_tftp_summary_fields()
    details["tftp_syscall_trace"] = collect_tftp_syscall_trace()
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = prev1998.ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    post = details.get("post_cal_indication") if isinstance(details.get("post_cal_indication"), dict) else {}
    cap = post.get("cap_events") if isinstance(post.get("cap_events"), dict) else {}
    bdf = post.get("bdf_events") if isinstance(post.get("bdf_events"), dict) else {}
    tail = post.get("tail_events") if isinstance(post.get("tail_events"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_trace = details.get("tftp_syscall_trace") if isinstance(details.get("tftp_syscall_trace"), dict) else {}
    cap_bdf_cal_success = (
        hit(cap, "wlfw_cap_success_branch") > 0
        and hit(bdf, "wlfw_bdf_return") > 0
        and is_zero(str(post.get("bdf_return_rc", "")))
        and hit(tail, "wlfw_cal_report_return") > 0
        and is_zero(str(post.get("cal_return_rc", "")))
    )
    tftp_data_seen = int(tftp_trace.get("tftp_data_record_count", 0)) > 0
    wlan_pd_up = int(cascade.get("wlan_pd_up", 0)) > 0
    holder_opened = bool(details.get("holder_opened"))
    lower_route_observed = (
        bool(base.get("combined"))
        or cap_bdf_cal_success
        or holder_opened
        or wlan_pd_up
        or tftp_data_seen
    )
    bridge_or_tftp_path_observed = (
        (bool(bridge.get("ok")) and bool(readwrite.get("ok")))
        or any(str(path).startswith("/readwrite/") for path in tftp_trace.get("tftp_data_paths", {}))
        or wlan_pd_up
    )
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and lower_route_observed
        and bridge_or_tftp_path_observed
        and bool(helper.get("ok"))
        and bool(tftp_trace.get("compiled_ok"))
        and bool(tftp_trace.get("safety_contract_ok"))
    )
    if not route_ok:
        label = "tftp-data-window-route-regression"
        reason = "V2012 did not preserve rollback, light observer, bridges, PM/CNSS, tftp trace, or cap/BDF/cal prerequisites"
        passed = False
    elif int(cascade.get("wlan0", 0)) > 0:
        label = "tftp-data-window-wlan0-progress"
        reason = "V2012 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif int(cascade.get("fw_ready", 0)) > 0:
        label = "tftp-data-window-fw-ready-progress"
        reason = "V2012 crossed into visible FW-ready progress"
        passed = True
    elif (
        trace.get("requested")
        or tftp_trace.get("wlanmdsp_seen")
        or tftp_trace.get("tftp_data_wlanmdsp")
        or int(tftp_summary.get("requested_wlanmdsp", 0)) > 0
    ):
        label = "tftp-data-window-wlanmdsp-request-progress"
        reason = "native tftp evidence exposed a wlanmdsp request/load edge with the downstream consumer chain running"
        passed = True
    elif int(tftp_trace.get("tftp_data_record_count", 0)) > 0:
        label = "tftp-data-window-data-request-no-wlanmdsp"
        reason = "native tftp_server received real modem RRQ/WRQ packets in the long window, but none requested wlanmdsp"
        passed = True
    elif (
        tftp_trace.get("server_check_seen")
        or tftp_trace.get("mcfg_seen")
        or tftp_trace.get("mbn_hw_seen")
        or tftp_trace.get("ota_firewall_seen")
        or tftp_trace.get("modem_seen")
        or int(tftp_summary.get("requested_server_check", 0)) > 0
        or int(tftp_summary.get("requested_mcfg", 0)) > 0
        or int(tftp_summary.get("requested_mbn_hw", 0)) > 0
        or int(tftp_summary.get("requested_ota_firewall", 0)) > 0
    ):
        label = "tftp-data-window-server-check-or-mcfg-no-wlanmdsp"
        reason = "native tftp saw early modem request tokens but not wlanmdsp; WLAN PD completion remains a modem-internal branch"
        passed = True
    elif int(tftp_trace.get("qrtr_del_client_record_count", 0)) > 0:
        label = "tftp-data-window-qrtr-control-only-no-data"
        reason = "long stock tftp_server trace saw QRTR DEL_CLIENT control notifications only; no modem RRQ/WRQ data packet arrived"
        passed = True
    elif int(tftp_trace.get("recv_payload_record_count", 0)) > 0:
        label = "tftp-data-window-nonqrtr-inbound-no-tokenized-tftp"
        reason = "stock tftp_server received inbound payloads, but their source was not decoded as QRTR and no path tokens appeared"
        passed = True
    else:
        label = "tftp-data-window-zero-request"
        reason = "bridges, tftp_server, and downstream consumer chain were present, but no modem tftp request reached native tftp_server"
        passed = True
    return {
        **base,
        "label": label,
        "decision": f"v2013-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "helper_completion_ok": bool(helper.get("ok")),
        "readwrite_bridge_ok": bool(readwrite.get("ok")),
        "rfs_bridge_ok": bool(bridge.get("ok")),
        "bridge_or_tftp_path_observed": bridge_or_tftp_path_observed,
        "lower_route_observed": lower_route_observed,
        "tftp_trace_ok": bool(tftp_trace.get("compiled_ok")) and bool(tftp_trace.get("safety_contract_ok")),
        "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        "route_ok": route_ok,
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    return prev2009.event_rows(events)


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_cal_indication"]
    tftp_summary = details["tftp_summary_fields"]
    tftp_trace = details["tftp_syscall_trace"]
    tftp_trace_summary = tftp_trace["summary"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["bridges", classification.get("bridge_or_tftp_path_observed"), f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')} tftp_paths={tftp_trace['tftp_data_paths']}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["tftp_summary", "", f"requested_any={cascade.get('requested_any')} server_check={cascade.get('server_check_request')} wlanmdsp={cascade.get('wlanmdsp_tftp')} pd_load={cascade.get('pd_load')} summary_wlanmdsp={tftp_summary.get('requested_wlanmdsp')}"],
        ["tftp_trace", classification.get("tftp_trace_active"), f"compiled={tftp_trace_summary['compiled']} attach_rc={tftp_trace_summary['late_attach_rc']} detach_rc={tftp_trace_summary['late_detach_rc']} records={tftp_trace['record_count']} stops={tftp_trace_summary['late_syscall_stop_count']} ms={tftp_trace_summary['late_duration_ms']} truncated={tftp_trace_summary['late_syscall_trace_truncated']}"],
        ["tftp_payloads", tftp_trace["any_named_request"], f"recv_payload={tftp_trace['recv_payload_record_count']} send_payload={tftp_trace['send_payload_record_count']} qipcrtr={tftp_trace['qipcrtr_record_count']} sources={tftp_trace['source_family_counts']} nodes={tftp_trace['source_nodes']} ports={tftp_trace['source_ports']}"],
        ["tftp_data", tftp_trace["tftp_data_any_named_request"], f"data={tftp_trace['tftp_data_record_count']} rrq={tftp_trace['tftp_rrq_record_count']} wrq={tftp_trace['tftp_wrq_record_count']} wlanmdsp={tftp_trace['tftp_data_wlanmdsp']} paths={tftp_trace['tftp_data_paths']}"],
        ["qrtr_control", "", f"control={tftp_trace['qrtr_control_record_count']} del_client={tftp_trace['qrtr_del_client_record_count']} ports={tftp_trace['qrtr_control_ports']}"],
        ["tftp_tokens", tftp_trace["token_hit_counts"], f"summary server_check={tftp_summary.get('requested_server_check')} mcfg={tftp_summary.get('requested_mcfg')} mbn_hw={tftp_summary.get('requested_mbn_hw')} ota={tftp_summary.get('requested_ota_firewall')} wlanmdsp={tftp_summary.get('requested_wlanmdsp')}"],
        ["cap_bdf_cal", "", f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
        ["indication", "", f"cb_hits={post['ind_events']['wlfw_qmi_ind_cb_entry']['hit_count']} first_msg={post['first_ind_msg_id']} len={post['first_ind_payload_len']} handle_type={post['first_handle_type']} fw_status={post['first_handle_0x28_status']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2013 TFTP Data-Window Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2013`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev1998.prev1992.prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## First TFTP Source Records",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_source_records"]),
        *([] if tftp_trace["first_source_records"] else ["- `none`"]),
        "",
        "## First TFTP Data Records",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_data_records"]),
        *([] if tftp_trace["first_data_records"] else ["- `none`"]),
        "",
        "## First QRTR Control Records",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_control_records"]),
        *([] if tftp_trace["first_control_records"] else ["- `none`"]),
        "",
        "## First TFTP Trace Records",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_records"]),
        *([] if tftp_trace["first_records"] else ["- `none`"]),
        "",
        "## First Payload Words",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_payload_words"]),
        *([] if tftp_trace["first_payload_words"] else ["- `none`"]),
        "",
        "## Tail Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["tail_events"])),
        "",
        "## Indication Events",
        "",
        prev1998.prev1992.prev.markdown_table(["event", "hits", "fetch", "first"], event_rows(post["ind_events"])),
        "",
        "## Branch",
        "",
        "- `tftp-data-window-wlan0-progress`: real interface appeared; keep HAL/scan/connect gated for a separate unit.",
        "- `tftp-data-window-wlanmdsp-request-progress`: request/load edge appeared with cnss-daemon running; chase downstream cascade only.",
        "- `tftp-data-window-data-request-no-wlanmdsp`: real tftp data reached stock `tftp_server`, but the modem did not ask for `wlanmdsp`.",
        "- `tftp-data-window-server-check-or-mcfg-no-wlanmdsp`: early modem tftp exists but no wlanmdsp; WLAN PD branch is modem-internal.",
        "- `tftp-data-window-qrtr-control-only-no-data`: the long window captured only QRTR control cleanup, not TFTP RRQ/WRQ data.",
        "- `tftp-data-window-zero-request`: no modem tftp reached stock tftp_server despite both bridges and downstream consumers.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.",
        "- The only ptrace was the bounded single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2012 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev2000.CYCLE = CYCLE
    prev2000.OUT_DIR = OUT_DIR
    prev2000.HANDOFF_DIR = HANDOFF_DIR
    prev2000.HANDOFF_REPORT = HANDOFF_REPORT
    prev2000.REPORT_PATH = REPORT_PATH
    prev1998.CYCLE = CYCLE
    prev1998.OUT_DIR = OUT_DIR
    prev1998.HANDOFF_DIR = HANDOFF_DIR
    prev1998.HANDOFF_REPORT = HANDOFF_REPORT
    prev1998.REPORT_PATH = REPORT_PATH
    prev1998.V1997_OUT = V2012_OUT
    prev1998.V1997_INIT = V2012_INIT
    prev1998.V1997_BOOT = V2012_BOOT
    prev1998.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1998.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1998.TEST_LOG_PATH = TEST_LOG_PATH
    prev1998.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1998.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1998.artifact_hook_check = artifact_hook_check
    prev1998.collect_details = collect_details
    prev1998.classify = classify
    prev1998.render_report = render_report
    v1688_runner = prev1998.prev1992.prev.parent.parent.base.v1847.runner()
    if not getattr(v1688_runner, "_v2013_tftp_data_window_hold_patched", False):
        original_parse_args = v1688_runner.parse_args

        def parse_args_with_v2013_hold(argv: list[str] | None = None) -> Any:
            args = original_parse_args(argv)
            args.post_boot_hold_sec = max(float(args.post_boot_hold_sec), V2013_POST_BOOT_HOLD_SEC)
            args.collect_timeout_sec = max(float(args.collect_timeout_sec), 240.0)
            return args

        v1688_runner.parse_args = parse_args_with_v2013_hold
        v1688_runner._v2013_tftp_data_window_hold_patched = True
    ORIGINAL_PATCH_PREV_MODULE()


def main(argv: list[str] | None = None) -> int:
    prev1998.patch_prev_module = patch_prev_module
    return prev1998.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
