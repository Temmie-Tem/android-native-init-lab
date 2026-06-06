#!/usr/bin/env python3
"""V2015 rollbackable handoff for compact tftp plus full downstream chain."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_tftp_data_window_handoff_v2013 as prev2013


CYCLE = "V2015"
OUT_DIR = prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2015-compact-tftp-full-chain-handoff"
)
HANDOFF_DIR = OUT_DIR / "v2014-handoff"
HANDOFF_REPORT = OUT_DIR / "v2014-handoff-report.md"
REPORT_PATH = prev2013.prev1998.prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V2015_COMPACT_TFTP_FULL_CHAIN_HANDOFF_2026-06-04.md"
)
V2014_OUT = prev2013.prev1998.prev1992.prev.repo_path(
    "tmp/wifi/v2014-compact-tftp-full-chain-test-boot"
)
V2014_INIT = V2014_OUT / "init_v2014_compact_tftp_full_chain"
V2014_BOOT = V2014_OUT / "boot_linux_v2014_compact_tftp_full_chain.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v2014/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.189 (v2014-compact-tftp-full-chain)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v2014.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v2014.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v2014-helper.result"
EXPECTED_HELPER_VERSION = "a90_android_execns_probe v376"

ORIGINAL_COLLECT_TFTP_SYSCALL_TRACE = prev2013.collect_tftp_syscall_trace
ORIGINAL_CLASSIFY = prev2013.classify
ORIGINAL_RENDER_REPORT = prev2013.render_report


def rel(path: Path) -> str:
    return prev2013.rel(path)


def intish(value: object) -> int:
    return prev2013.prev1998.prev1992.prev.intish(value)


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v2014",
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
        ".compact.%s.record_%03u",
        ".token.wlanmdsp=%d",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V2014_INIT, init_required), (V2014_BOOT, boot_required)):
        forbidden_tokens = init_forbidden if path == V2014_INIT else ()
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


def collect_tftp_syscall_trace() -> dict[str, Any]:
    base = ORIGINAL_COLLECT_TFTP_SYSCALL_TRACE()
    text = prev2013.prev1998.read_helper_text()
    fields = prev2013.prev1998.parse_fields(text)
    record_pattern = re.compile(r"^wlan_pd_tftp_server_trace\.compact\.tftp_server\.record_(\d+)\.(.+)$")
    records: dict[int, dict[str, str]] = {}
    for key, value in fields.items():
        match = record_pattern.match(key)
        if not match:
            continue
        records.setdefault(int(match.group(1)), {})[match.group(2)] = value

    source_family_counts: dict[str, int] = {}
    source_nodes: dict[str, int] = {}
    source_ports: dict[str, int] = {}
    tftp_data_paths: dict[str, int] = {}
    token_hit_counts = {name: 0 for name in prev2013.prev1998.TFTP_TOKENS}
    tftp_rrq_records = 0
    tftp_wrq_records = 0
    first_source_records: list[str] = []
    first_data_records: list[str] = []

    for index in sorted(records):
        record = records[index]
        family = record.get("family_name", "")
        node = record.get("qrtr.node", "")
        port = record.get("qrtr.port", "")
        op = record.get("op", "")
        path = record.get("path", "")
        mode = record.get("mode", "")
        if family:
            source_family_counts[family] = source_family_counts.get(family, 0) + 1
        if node:
            source_nodes[node] = source_nodes.get(node, 0) + 1
        if port:
            source_ports[port] = source_ports.get(port, 0) + 1
        if path:
            tftp_data_paths[path] = tftp_data_paths.get(path, 0) + 1
        if op == "RRQ":
            tftp_rrq_records += 1
        elif op == "WRQ":
            tftp_wrq_records += 1
        for token_name in token_hit_counts:
            if intish(record.get(f"token.{token_name}")) > 0:
                token_hit_counts[token_name] += 1
        if len(first_source_records) < 12:
            first_source_records.append(
                f"record_{index:03d} ret={record.get('ret', '')} fd={record.get('fd', '')} "
                f"family={family or 'none'} node={node or 'none'} port={port or 'none'}"
            )
        if len(first_data_records) < 12:
            first_data_records.append(
                f"record_{index:03d} {op or record.get('opcode', '')} node={node or 'none'} "
                f"port={port or 'none'} path={path or 'none'} mode={mode or 'none'}"
            )

    compact_count = len(records)
    if compact_count == 0:
        return base

    base.update({
        "record_count": compact_count,
        "compact_record_count": compact_count,
        "recv_payload_record_count": compact_count,
        "recvfrom_source_record_count": compact_count,
        "recvfrom_qrtr_source_record_count": source_family_counts.get("AF_QIPCRTR", 0),
        "qipcrtr_record_count": source_family_counts.get("AF_QIPCRTR", 0),
        "tftp_data_record_count": compact_count,
        "tftp_rrq_record_count": tftp_rrq_records,
        "tftp_wrq_record_count": tftp_wrq_records,
        "tftp_data_paths": tftp_data_paths,
        "tftp_data_wlanmdsp": token_hit_counts["wlanmdsp"] > 0,
        "tftp_data_any_named_request": bool(tftp_data_paths),
        "source_family_counts": source_family_counts,
        "source_nodes": source_nodes,
        "source_ports": source_ports,
        "token_hit_counts": token_hit_counts,
        "first_source_records": first_source_records,
        "first_data_records": first_data_records,
        "server_check_seen": token_hit_counts["server_check"] > 0,
        "mcfg_seen": token_hit_counts["mcfg"] > 0,
        "mbn_hw_seen": token_hit_counts["mbn_hw"] > 0,
        "ota_firewall_seen": token_hit_counts["ota_firewall"] > 0,
        "wlanmdsp_seen": token_hit_counts["wlanmdsp"] > 0,
        "modem_seen": token_hit_counts["modem"] > 0,
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
    v2015_route_ok = (
        bool(result.get("hook_ok"))
        and bool(result.get("rollback_ok"))
        and bool(result.get("light_ok"))
        and bool(result.get("lower_route_observed"))
        and bool(result.get("bridge_or_tftp_path_observed"))
        and bool(helper.get("ok"))
        and bool(tftp_trace.get("compiled_ok"))
        and bool(tftp_trace.get("safety_contract_ok"))
        and bool(tftp_trace.get("trace_active"))
    )
    if result.get("label") == "tftp-data-window-route-regression" and v2015_route_ok:
        if intish(cascade.get("wlan0")) > 0:
            label = "tftp-data-window-wlan0-progress"
            reason = "V2014 reached wlan0; stop before credentials/scan/connect until a dedicated gated unit"
        elif intish(cascade.get("fw_ready")) > 0:
            label = "tftp-data-window-fw-ready-progress"
            reason = "V2014 crossed into visible FW-ready progress"
        elif (
            trace.get("requested")
            or tftp_trace.get("wlanmdsp_seen")
            or tftp_trace.get("tftp_data_wlanmdsp")
            or intish(tftp_summary.get("requested_wlanmdsp")) > 0
        ):
            label = "tftp-data-window-wlanmdsp-request-progress"
            reason = "native tftp evidence exposed a wlanmdsp request/load edge with the downstream consumer chain running"
        elif intish(tftp_trace.get("tftp_data_record_count")) > 0:
            label = "tftp-data-window-data-request-no-wlanmdsp"
            reason = (
                "full consumer chain ran with compact stock tftp_server RRQ/WRQ tracing; "
                "native saw tftp data but no wlanmdsp request"
            )
        elif (
            tftp_trace.get("server_check_seen")
            or tftp_trace.get("mcfg_seen")
            or tftp_trace.get("mbn_hw_seen")
            or tftp_trace.get("ota_firewall_seen")
            or tftp_trace.get("modem_seen")
            or intish(tftp_summary.get("requested_server_check")) > 0
            or intish(tftp_summary.get("requested_mcfg")) > 0
            or intish(tftp_summary.get("requested_mbn_hw")) > 0
            or intish(tftp_summary.get("requested_ota_firewall")) > 0
        ):
            label = "tftp-data-window-server-check-or-mcfg-no-wlanmdsp"
            reason = "native tftp saw early modem request tokens but not wlanmdsp; WLAN PD completion remains a modem-internal branch"
        elif intish(tftp_trace.get("qrtr_del_client_record_count")) > 0:
            label = "tftp-data-window-qrtr-control-only-no-data"
            reason = "compact stock tftp_server trace saw QRTR DEL_CLIENT control notifications only; no modem RRQ/WRQ data packet arrived"
        elif intish(tftp_trace.get("recv_payload_record_count")) > 0:
            label = "tftp-data-window-nonqrtr-inbound-no-tokenized-tftp"
            reason = "stock tftp_server received inbound payloads, but no path tokens appeared"
        else:
            label = "tftp-data-window-zero-request"
            reason = "bridges, tftp_server, and downstream consumer chain were present, but no modem tftp request reached native tftp_server"
        result.update({
            "label": label,
            "decision": f"v2013-{label}-rollback-pass",
            "pass": True,
            "reason": reason,
            "route_ok": True,
            "v2015_route_override": True,
        })
    result["decision"] = str(result["decision"]).replace("v2013-", "v2015-", 1)
    if result["label"] == "tftp-data-window-data-request-no-wlanmdsp":
        result["reason"] = (
            "full consumer chain ran with compact stock tftp_server RRQ/WRQ tracing; "
            "native saw tftp data but no wlanmdsp request"
        )
    return result


def render_report(manifest: dict[str, Any]) -> str:
    text = ORIGINAL_RENDER_REPORT(manifest)
    replacements = {
        "# Native Init V2013 TFTP Data-Window Handoff": "# Native Init V2015 Compact TFTP Full-Chain Handoff",
        "- Cycle: `V2013`": "- Cycle: `V2015`",
        "V2012": "V2014",
        "V2013": "V2015",
        "long tftp data-window trace": "compact tftp full-chain trace",
        "long window": "compact full-chain window",
        "bounded single-child syscall trace": "bounded compact single-child syscall trace",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def configure_prev2013() -> None:
    prev2013.CYCLE = CYCLE
    prev2013.OUT_DIR = OUT_DIR
    prev2013.HANDOFF_DIR = HANDOFF_DIR
    prev2013.HANDOFF_REPORT = HANDOFF_REPORT
    prev2013.REPORT_PATH = REPORT_PATH
    prev2013.V2012_OUT = V2014_OUT
    prev2013.V2012_INIT = V2014_INIT
    prev2013.V2012_BOOT = V2014_BOOT
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
