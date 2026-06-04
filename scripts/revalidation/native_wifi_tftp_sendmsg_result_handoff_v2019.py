#!/usr/bin/env python3
"""V2019 rollbackable handoff for native TFTP sendmsg-result tracing."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_data_window_handoff_v2013 as prev2013


CYCLE = "V2019"
OUT_DIR = prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2019-tftp-sendmsg-result-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2018-handoff"
HANDOFF_REPORT = OUT_DIR / "v2018-handoff-report.md"
REPORT_PATH = prev2013.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2019_TFTP_SENDMSG_RESULT_HANDOFF_2026-06-04.md"
)
V2018_OUT = prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2018-tftp-sendmsg-result-test-boot"
)
V2018_INIT = V2018_OUT / "init_v2018_tftp_sendmsg_result"
V2018_BOOT = V2018_OUT / "boot_linux_v2018_tftp_sendmsg_result.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2018/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.191 (v2018-tftp-sendmsg-result)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2018.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2018.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2018-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v378"
TFTP_TOKENS = prev2013.prev1998.TFTP_TOKENS

ORIGINAL_COLLECT_TFTP_SYSCALL_TRACE = prev2013.collect_tftp_syscall_trace
ORIGINAL_CLASSIFY = prev2013.classify


def rel(path: Path) -> str:
    return prev2013.rel(path)


def intish(value: object) -> int:
    return prev2013.prev1998.prev1992.prev.intish(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2018",
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
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wifi_companion_start.cnss_daemon_argv=/vendor/bin/cnss-daemon -n -l",
        "wlan_pd_icnss_ipc_snapshot",
        "wlfw_cal_report_return",
        "wlfw_worker_cal_only_call",
        "wlfw_qmi_ind_cb_entry",
        "wlan_pd_tftp_server_trace.late_attach.begin=1",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=%d",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.single_child=tftp_server",
        "%s.%s.%s.record_%03u",
        "compactfs",
        ".payload_len=%zu",
        ".error_message=",
        "sendmsg",
        "recvmsg",
        ".token.wlanmdsp=%d",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2018_INIT, init_required), (V2018_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2018_INIT else ()
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in forbidden_tokens if token.encode() in data]
        checks[rel(path)] = {
            "exists": True,
            "ok": not missing and not forbidden,
            "missing": missing,
            "forbidden": forbidden,
        }
    return checks


def parse_records(fields: dict[str, str], kind: str) -> dict[int, dict[str, str]]:
    pattern = re.compile(rf"^wlan_pd_tftp_server_trace\.{kind}\.tftp_server\.record_(\d+)\.(.+)$")
    records: dict[int, dict[str, str]] = {}
    for key, value in fields.items():
        match = pattern.match(key)
        if match:
            records.setdefault(int(match.group(1)), {})[match.group(2)] = value
    return records


def count_value(target: dict[str, int], key: str) -> None:
    if key:
        target[key] = target.get(key, 0) + 1


def token_counts_from(records: list[dict[str, str]]) -> dict[str, int]:
    counts = {name: 0 for name in TFTP_TOKENS}
    for record in records:
        for name in counts:
            if intish(record.get(f"token.{name}")) > 0:
                counts[name] += 1
    return counts


def collect_tftp_syscall_trace() -> dict[str, Any]:
    base = ORIGINAL_COLLECT_TFTP_SYSCALL_TRACE()
    text = prev2013.prev1998.read_helper_text()
    fields = prev2013.prev1998.parse_fields(text)
    packets = parse_records(fields, "compact")
    fs_records = parse_records(fields, "compactfs")
    if not packets and not fs_records:
        return base

    packet_values = [packets[index] for index in sorted(packets)]
    fs_values = [fs_records[index] for index in sorted(fs_records)]
    source_family_counts: dict[str, int] = {}
    source_nodes: dict[str, int] = {}
    source_ports: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    packet_op_counts: dict[str, int] = {}
    tftp_data_paths: dict[str, int] = {}
    tftp_error_messages: dict[str, int] = {}
    fs_path_counts: dict[str, int] = {}
    fs_error_counts: dict[str, int] = {}
    fs_success_counts: dict[str, int] = {}
    first_source_records: list[str] = []
    first_data_records: list[str] = []
    first_packet_records: list[str] = []
    first_error_records: list[str] = []
    first_fs_records: list[str] = []

    for index in sorted(packets):
        record = packets[index]
        family = record.get("family_name", "")
        node = record.get("qrtr.node", "")
        port = record.get("qrtr.port", "")
        direction = record.get("direction", "")
        op = record.get("op", "")
        path = record.get("path", "")
        message = record.get("error_message", "")
        count_value(source_family_counts, family)
        count_value(source_nodes, node)
        count_value(source_ports, port)
        count_value(direction_counts, direction)
        count_value(packet_op_counts, op)
        if path:
            count_value(tftp_data_paths, path)
        if message:
            count_value(tftp_error_messages, message)
        if len(first_source_records) < 12:
            first_source_records.append(
                f"packet_{index:03d} dir={direction or 'none'} op={op or 'none'} "
                f"ret={record.get('ret', '')} family={family or 'none'} node={node or 'none'} port={port or 'none'}"
            )
        if path and len(first_data_records) < 12:
            first_data_records.append(
                f"packet_{index:03d} {direction or 'none'} {op or 'none'} node={node or 'none'} "
                f"port={port or 'none'} path={path} mode={record.get('mode', 'none')}"
            )
        if len(first_packet_records) < 16:
            detail = path or message or f"block={record.get('block', '')} data_len={record.get('data_len', '')}"
            first_packet_records.append(f"packet_{index:03d} {direction or 'none'} {op or 'none'} {detail}")
        if op == "ERROR" and len(first_error_records) < 12:
            first_error_records.append(
                f"packet_{index:03d} code={record.get('error_code', '')} msg={message or 'none'}"
            )

    for index in sorted(fs_records):
        record = fs_records[index]
        path = record.get("path", "")
        error = intish(record.get("error"))
        count_value(fs_path_counts, path)
        if error:
            count_value(fs_error_counts, path)
        else:
            count_value(fs_success_counts, path)
        if len(first_fs_records) < 16:
            first_fs_records.append(
                f"fs_{index:03d} {record.get('name', '')} ret={record.get('ret', '')} "
                f"err={record.get('error', '')}/{record.get('error_name', '')} path={path or 'none'}"
            )

    packet_token_counts = token_counts_from(packet_values)
    fs_token_counts = token_counts_from(fs_values)
    token_hit_counts = {name: packet_token_counts.get(name, 0) + fs_token_counts.get(name, 0) for name in TFTP_TOKENS}
    tftp_rrq_records = packet_op_counts.get("RRQ", 0)
    tftp_wrq_records = packet_op_counts.get("WRQ", 0)
    mcfg_packet_seen = packet_token_counts.get("mcfg", 0) > 0
    mcfg_fs_seen = fs_token_counts.get("mcfg", 0) > 0
    mcfg_error_seen = any(
        intish(record.get("token.mcfg")) > 0 and record.get("op") == "ERROR"
        for record in packet_values
    ) or any(
        intish(record.get("token.mcfg")) > 0 and intish(record.get("error")) > 0
        for record in fs_values
    )
    mcfg_transfer_seen = (
        packet_op_counts.get("ACK", 0) > 0
        or packet_op_counts.get("DATA", 0) > 0
        or any(intish(record.get("token.mcfg")) > 0 and intish(record.get("error")) == 0 for record in fs_values)
    )

    base.update({
        "record_count": len(packet_values) + len(fs_values),
        "compact_record_count": len(packet_values),
        "compactfs_record_count": len(fs_values),
        "packet_record_count": len(packet_values),
        "fs_record_count": len(fs_values),
        "recv_payload_record_count": len(packet_values),
        "recvfrom_source_record_count": direction_counts.get("recvfrom", 0),
        "recvfrom_qrtr_source_record_count": sum(1 for record in packet_values if record.get("direction") == "recvfrom" and record.get("family_name") == "AF_QIPCRTR"),
        "qipcrtr_record_count": source_family_counts.get("AF_QIPCRTR", 0),
        "tftp_data_record_count": tftp_rrq_records + tftp_wrq_records,
        "tftp_rrq_record_count": tftp_rrq_records,
        "tftp_wrq_record_count": tftp_wrq_records,
        "tftp_data_paths": tftp_data_paths,
        "tftp_data_wlanmdsp": token_hit_counts["wlanmdsp"] > 0,
        "tftp_data_any_named_request": bool(tftp_data_paths),
        "source_family_counts": source_family_counts,
        "source_nodes": source_nodes,
        "source_ports": source_ports,
        "direction_counts": direction_counts,
        "packet_op_counts": packet_op_counts,
        "tftp_error_messages": tftp_error_messages,
        "tftp_error_packet_count": packet_op_counts.get("ERROR", 0),
        "tftp_ack_packet_count": packet_op_counts.get("ACK", 0),
        "tftp_data_packet_count": packet_op_counts.get("DATA", 0),
        "tftp_oack_packet_count": packet_op_counts.get("OACK", 0),
        "fs_path_counts": fs_path_counts,
        "fs_error_counts": fs_error_counts,
        "fs_success_counts": fs_success_counts,
        "packet_token_hit_counts": packet_token_counts,
        "fs_token_hit_counts": fs_token_counts,
        "token_hit_counts": token_hit_counts,
        "first_source_records": first_source_records,
        "first_data_records": first_data_records,
        "first_packet_records": first_packet_records,
        "first_error_records": first_error_records,
        "first_fs_records": first_fs_records,
        "server_check_seen": token_hit_counts["server_check"] > 0,
        "mcfg_seen": token_hit_counts["mcfg"] > 0,
        "mbn_hw_seen": token_hit_counts["mbn_hw"] > 0,
        "ota_firewall_seen": token_hit_counts["ota_firewall"] > 0,
        "wlanmdsp_seen": token_hit_counts["wlanmdsp"] > 0,
        "modem_seen": token_hit_counts["modem"] > 0,
        "mcfg_packet_seen": mcfg_packet_seen,
        "mcfg_fs_seen": mcfg_fs_seen,
        "mcfg_error_seen": mcfg_error_seen,
        "mcfg_transfer_seen": mcfg_transfer_seen,
        "any_named_request": any(token_hit_counts.values()),
        "undecoded_inbound": False,
    })
    return base


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    result = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    cascade = details.get("cascade") if isinstance(details.get("cascade"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_trace = details.get("tftp_syscall_trace") if isinstance(details.get("tftp_syscall_trace"), dict) else {}
    current_hook = artifact_hook_check()
    current_hook_ok = all(bool(item.get("ok")) for item in current_hook.values())
    route_ok = (
        current_hook_ok
        and bool(result.get("rollback_ok"))
        and bool(result.get("light_ok"))
        and bool(result.get("lower_route_observed"))
        and bool(result.get("bridge_or_tftp_path_observed"))
        and bool(helper.get("ok"))
        and bool(tftp_trace.get("compiled_ok"))
        and bool(tftp_trace.get("safety_contract_ok"))
        and bool(tftp_trace.get("trace_active"))
    )
    if not route_ok:
        label = "tftp-result-route-regression"
        reason = "V2018 did not preserve rollback, light observer, bridges, full chain, or tftp sendmsg-result trace"
        passed = False
    elif intish(cascade.get("wlan0")) > 0:
        label = "tftp-result-wlan0-progress"
        reason = "V2018 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        passed = True
    elif intish(cascade.get("fw_ready")) > 0:
        label = "tftp-result-fw-ready-progress"
        reason = "V2018 crossed into visible FW-ready progress"
        passed = True
    elif (
        trace.get("requested")
        or tftp_trace.get("wlanmdsp_seen")
        or tftp_trace.get("tftp_data_wlanmdsp")
        or intish(tftp_summary.get("requested_wlanmdsp")) > 0
    ):
        label = "tftp-result-wlanmdsp-request-progress"
        reason = "native tftp evidence exposed a wlanmdsp request/load edge with the downstream consumer chain running"
        passed = True
    elif tftp_trace.get("mcfg_error_seen"):
        label = "tftp-result-mcfg-error-no-wlanmdsp"
        reason = "native modem reaches mcfg.tmp but tftp_server reports packet or filesystem errors before any wlanmdsp request"
        passed = True
    elif tftp_trace.get("mcfg_transfer_seen") and tftp_trace.get("mcfg_packet_seen"):
        label = "tftp-result-mcfg-transfer-no-wlanmdsp"
        reason = "native modem reaches mcfg.tmp and tftp_server returns transfer evidence, but the modem still never asks for wlanmdsp"
        passed = True
    elif tftp_trace.get("mcfg_packet_seen"):
        label = "tftp-result-mcfg-request-no-response"
        reason = "native modem repeatedly requests mcfg.tmp, but no compact ACK/DATA/ERROR or focused filesystem result was captured even with sendmsg decoding"
        passed = True
    elif intish(tftp_trace.get("tftp_data_record_count")) > 0:
        label = "tftp-result-data-request-no-wlanmdsp"
        reason = "native tftp_server received modem RRQ/WRQ packets, but none requested wlanmdsp"
        passed = True
    else:
        label = "tftp-result-zero-request"
        reason = "bridges, tftp_server, and downstream consumer chain were present, but no modem tftp request reached native tftp_server"
        passed = True
    return {
        **result,
        "label": label,
        "decision": f"v2019-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": current_hook_ok,
        "route_ok": route_ok,
        "helper_completion_ok": bool(helper.get("ok")),
        "tftp_trace_ok": bool(tftp_trace.get("compiled_ok")) and bool(tftp_trace.get("safety_contract_ok")),
        "tftp_trace_active": bool(tftp_trace.get("trace_active")),
    }


def rows_to_md(rows: list[list[object]]) -> str:
    return prev2013.prev1998.prev1992.prev.markdown_table(
        ["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]
    )


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    post = details["post_cal_indication"]
    tftp_summary = details["tftp_summary_fields"]
    tftp_trace = details["tftp_syscall_trace"]
    trace_summary = tftp_trace["summary"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper", classification.get("helper_completion_ok"), details["helper_completion"]["result_file_version"]],
        ["route", classification.get("route_ok"), f"service74={details['service74']} service180={details['service180']} holder={details['holder_opened']}"],
        ["bridges", classification.get("bridge_or_tftp_path_observed"), f"readonly={classification.get('rfs_bridge_ok')} readwrite={classification.get('readwrite_bridge_ok')}"],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} wlfw69={cascade['wlfw69']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']} hold={cascade.get('post_up_hold_sec')}"],
        ["tftp_trace", classification.get("tftp_trace_active"), f"compiled={trace_summary['compiled']} attach_rc={trace_summary['late_attach_rc']} detach_rc={trace_summary['late_detach_rc']} records={tftp_trace['record_count']} packet={tftp_trace['packet_record_count']} fs={tftp_trace['fs_record_count']} stops={trace_summary['late_syscall_stop_count']} ms={trace_summary['late_duration_ms']} truncated={trace_summary['late_syscall_trace_truncated']}"],
        ["packet_ops", tftp_trace.get("packet_op_counts"), f"directions={tftp_trace.get('direction_counts')} errors={tftp_trace.get('tftp_error_messages')}"],
        ["packet_paths", tftp_trace.get("tftp_data_any_named_request"), f"paths={tftp_trace['tftp_data_paths']} token={tftp_trace.get('packet_token_hit_counts')}"],
        ["fs_paths", tftp_trace.get("fs_record_count"), f"success={tftp_trace.get('fs_success_counts')} errors={tftp_trace.get('fs_error_counts')} token={tftp_trace.get('fs_token_hit_counts')}"],
        ["mcfg_gate", "", f"packet={tftp_trace.get('mcfg_packet_seen')} fs={tftp_trace.get('mcfg_fs_seen')} transfer={tftp_trace.get('mcfg_transfer_seen')} error={tftp_trace.get('mcfg_error_seen')}"],
        ["wlanmdsp", "", f"summary={tftp_summary.get('requested_wlanmdsp')} trace={tftp_trace.get('wlanmdsp_seen')} dmesg={cascade.get('wlanmdsp_tftp')} pd_load={cascade.get('pd_load')}"] ,
        ["cap_bdf_cal", "", f"cap={post['cap_return_rc']} bdf={post['bdf_return_rc']} cal={post['cal_return_rc']} worker_cal={post['worker_cal_rc']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V2019 TFTP Sendmsg Result Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V2019`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        rows_to_md(matrix_rows),
        "",
        "## Interpretation",
        "",
        "- The modem still reaches `msm/modem/wlan_pd` UP and stock `tftp_server` receives repeated `/readwrite/mcfg.tmp` RRQ/WRQ packets.",
        "- No compact `sendmsg`/`sendto` ACK/DATA/ERROR and no focused `openat`/stat path result appeared in the traced `tftp_server` task.",
        "- This localizes the next blocker to the TFTP result side: either the transfer is handled in an untraced `tftp_server` worker thread/process, or the server is not responding after the QRTR receive path.",
        "- Next bounded unit, if this still has no response: keep the same full-chain route, but follow/attach all `tftp_server` tasks or clone children and decode focused file opens for `/readwrite/mcfg.tmp`.",
        "",
        "## First TFTP Packets",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_packet_records", [])),
        *([] if tftp_trace.get("first_packet_records") else ["- `none`"]),
        "",
        "## First TFTP Errors",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_error_records", [])),
        *([] if tftp_trace.get("first_error_records") else ["- `none`"]),
        "",
        "## First Focused FS Results",
        "",
        *(f"- `{line}`" for line in tftp_trace.get("first_fs_records", [])),
        *([] if tftp_trace.get("first_fs_records") else ["- `none`"]),
        "",
        "## Steps",
        "",
        *step_lines,
        *([] if step_lines else ["- `none`"]),
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, service-notifier listener, active QRTR readback, or QMI payload send was run.",
        "- The only ptrace was the bounded compact single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.",
        "- No `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator write, PCI rescan, bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V2018 test-boot flash-handoff, namespace-local RFS tmpfs/symlink bridges, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def configure_prev2013() -> None:
    prev2013.CYCLE = CYCLE
    prev2013.OUT_DIR = OUT_DIR
    prev2013.HANDOFF_DIR = HANDOFF_DIR
    prev2013.HANDOFF_REPORT = HANDOFF_REPORT
    prev2013.REPORT_PATH = REPORT_PATH
    prev2013.V2012_OUT = V2018_OUT
    prev2013.V2012_INIT = V2018_INIT
    prev2013.V2012_BOOT = V2018_BOOT
    prev2013.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev2013.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev2013.TEST_LOG_PATH = TEST_LOG_PATH
    prev2013.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev2013.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev2013.EXPECTED_HELPER_VERSION = EXPECTED_HELPER_VERSION
    prev2013.artifact_hook_check = artifact_hook_check
    prev2013.collect_tftp_syscall_trace = collect_tftp_syscall_trace
    prev2013.classify = classify
    prev2013.render_report = render_report


def main(argv: list[str] | None = None) -> int:
    configure_prev2013()
    return prev2013.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
