#!/usr/bin/env python3
"""V1998 native tftp-any/readwrite RFS discriminator handoff."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_rfs_bridge_wlanmdsp_handoff_v1992 as prev1992


CYCLE = "V1998"
OUT_DIR = prev1992.prev.repo_path("tmp/wifi/v1998-tftp-any-readwrite-handoff")
HANDOFF_DIR = OUT_DIR / "v1997-handoff"
HANDOFF_REPORT = OUT_DIR / "v1997-handoff-report.md"
REPORT_PATH = prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V1998_TFTP_ANY_READWRITE_HANDOFF_2026-06-04.md"
)
V1997_OUT = prev1992.prev.repo_path("tmp/wifi/v1997-tftp-any-readwrite-test-boot")
V1997_INIT = V1997_OUT / "init_v1997_tftp_any_readwrite"
V1997_BOOT = V1997_OUT / "boot_linux_v1997_tftp_any_readwrite.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1997/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.181 (v1997-tftp-any-readwrite)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1997.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1997.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1997-helper.result"

ORIGINAL_PATCH_PREV_MODULE = prev1992.patch_prev_module
ORIGINAL_CLASSIFY = prev1992.classify
ORIGINAL_RENDER_REPORT = prev1992.render_report
ORIGINAL_COLLECT_DETAILS = prev1992.prev.collect_details

TFTP_TOKENS = {
    "server_check": ("server_check.txt", "server_check", "readwrite/server_check"),
    "ota_firewall": ("ota_firewall", "ruleset"),
    "mcfg": ("mcfg",),
    "mbn_hw": ("mbn_hw",),
    "wlanmdsp": ("wlanmdsp", "wlanmdsp.mbn"),
    "modem": ("modem.mdt", "modem.b00", "modem.mbn"),
}


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


def syscall_blocks(text: str, label: str, limit: int = 8) -> list[str]:
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
            blocks.append(body[:260])
        if len(blocks) >= limit:
            break
    return blocks


def hex_to_ascii_fragments(hex_text: str) -> list[str]:
    if not hex_text or len(hex_text) % 2:
        return []
    try:
        data = bytes.fromhex(hex_text)
    except ValueError:
        return []
    decoded = "".join(chr(byte) if 32 <= byte < 127 else " " for byte in data)
    return [match.group(0) for match in re.finditer(r"[ -~]{4,}", decoded)]


def token_hits(blob: str) -> dict[str, bool]:
    lower = blob.lower()
    return {
        name: any(token.lower() in lower for token in tokens)
        for name, tokens in TFTP_TOKENS.items()
    }


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1997",
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
        "a90_android_execns_probe v368",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "server_check.absolute=/vendor/rfs/msm/mpss/readwrite/server_check.txt",
        "readwrite.tmpfs_requested=1",
        "wlan_pd_firmware_serve_gate.requested_server_check=%d",
        "wlan_pd_firmware_serve_gate.requested_mcfg=%d",
        "wlan_pd_firmware_serve_gate.requested_mbn_hw=%d",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled=%d",
        "wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.single_child=tftp_server",
        "wlan_pd_tftp_server_trace",
        "tftp_server",
        "pd-mapper",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1997_INIT, init_required), (V1997_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in init_forbidden if path == V1997_INIT and token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_helper_completion(handoff: dict[str, Any]) -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    rollback = handoff.get("post_rollback_verification") if isinstance(handoff.get("post_rollback_verification"), dict) else {}
    result = {
        "text_present": bool(text),
        "result_file_version": fields.get("result_file_version", ""),
        "version_ok": fields.get("result_file_version") == "a90_android_execns_probe v368",
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


def collect_readwrite_bridge() -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    result = {
        "text_present": bool(text),
        "readwrite_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.path", ""),
        "readwrite_exists": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.exists"))),
        "readwrite_is_dir": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.is_dir"))),
        "readwrite_is_symlink": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.is_symlink"))),
        "readwrite_mode": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.mode", ""),
        "readwrite_uid": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.uid", ""),
        "readwrite_gid": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.gid", ""),
        "readwrite_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.errno", ""),
        "readwrite_tmpfs_requested": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.readwrite.tmpfs_requested"))),
        "server_check_path": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.server_check.host_path", ""),
        "server_check_exists": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.server_check.exists"))),
        "server_check_is_reg": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.server_check.is_reg"))),
        "server_check_size": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.server_check.size", ""),
        "server_check_errno": fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.server_check.stat_errno", ""),
        "rootfs_namespace_only": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.rootfs_namespace_only"))),
        "sda29_write": int(prev1992.prev.intish(fields.get("wlan_pd_firmware_serve_gate.rfs_bridge.sda29_write"))),
    }
    result["ok"] = (
        result["readwrite_exists"] > 0
        and result["readwrite_is_dir"] > 0
        and result["readwrite_tmpfs_requested"] == 1
        and result["rootfs_namespace_only"] == 1
        and result["sda29_write"] == 0
    )
    return result


def collect_tftp_summary_fields() -> dict[str, Any]:
    fields = parse_fields(read_helper_text())
    keys = {
        "requested_wlanmdsp": "wlan_pd_firmware_serve_gate.requested_wlanmdsp",
        "requested_modem": "wlan_pd_firmware_serve_gate.requested_modem",
        "requested_server_check": "wlan_pd_firmware_serve_gate.requested_server_check",
        "requested_ota_firewall": "wlan_pd_firmware_serve_gate.requested_ota_firewall",
        "requested_mcfg": "wlan_pd_firmware_serve_gate.requested_mcfg",
        "requested_mbn_hw": "wlan_pd_firmware_serve_gate.requested_mbn_hw",
        "requested_any": "wlan_pd_firmware_serve_gate.requested_any",
        "tftp_child_present": "wlan_pd_firmware_serve_gate.tftp_child_present",
        "tftp_observable": "wlan_pd_firmware_serve_gate.tftp_observable",
        "tftp_running": "wlan_pd_firmware_serve_gate.tftp_running",
        "label": "wlan_pd_firmware_serve_gate.label",
    }
    return {
        key: (fields.get(field, "") if key == "label" else int(prev1992.prev.intish(fields.get(field))))
        for key, field in keys.items()
    }


def collect_tftp_syscall_trace() -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    record_pattern = re.compile(r"^wlan_pd_tftp_server_trace\.syscall\.tftp_server\.record_(\d+)\.(.+)$")
    records: dict[int, dict[str, str]] = {}
    for key, value in fields.items():
        match = record_pattern.match(key)
        if not match:
            continue
        index = int(match.group(1))
        records.setdefault(index, {})[match.group(2)] = value

    record_list = [records[index] for index in sorted(records)]
    first_records: list[str] = []
    first_payload_fragments: list[str] = []
    name_counts: dict[str, int] = {}
    hit_counts = {name: 0 for name in TFTP_TOKENS}
    recv_payload_records = 0
    send_payload_records = 0
    qipcrtr_records = 0
    path_records = 0

    for index in sorted(records):
        record = records[index]
        name = record.get("name", "")
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
        pieces: list[str] = []
        if record.get("path.text"):
            path_records += 1
            pieces.append(record["path.text"])
        for key, value in record.items():
            if value == "AF_QIPCRTR":
                qipcrtr_records += 1
            if key.endswith(".hex") and value:
                fragments = hex_to_ascii_fragments(value)
                pieces.extend(fragments)
                if fragments and len(first_payload_fragments) < 8:
                    first_payload_fragments.extend(fragments[: 8 - len(first_payload_fragments)])
                if name in {"recvmsg", "recvfrom"}:
                    recv_payload_records += 1
                if name in {"sendmsg", "sendto"}:
                    send_payload_records += 1
        blob = " ".join(pieces)
        hits = token_hits(blob)
        for token_name, present in hits.items():
            if present:
                hit_counts[token_name] += 1
        if len(first_records) < 12:
            fd_target = record.get("fd.target") or record.get("ret_fd.target") or ""
            path_text = record.get("path.text", "")
            sockaddr = ""
            for key in (
                "msghdr_sockaddr.family_name",
                "msghdr_sockaddr.qrtr.node",
                "msghdr_sockaddr.qrtr.port",
                "sockaddr.family_name",
                "sockaddr.qrtr.node",
                "sockaddr.qrtr.port",
            ):
                if key in record:
                    sockaddr = f"{sockaddr} {key}={record[key]}".strip()
            detail = path_text or fd_target or sockaddr
            first_records.append(f"record_{index:03d} {name} ret={record.get('ret', '')} {detail}".strip())

    summary = {
        "compiled": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.compiled"))),
        "single_child": fields.get("wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.single_child", ""),
        "late_attach_contract": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.late_attach"))),
        "no_qrtr_send": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.no_qrtr_send"))),
        "no_qmi_payload_send": int(prev1992.prev.intish(fields.get("wifi_companion_start.wlan_pd_producer_tftp_server_syscall_trace.no_qmi_payload_send"))),
        "late_available": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.available"))),
        "late_attach_rc": fields.get("wlan_pd_tftp_server_trace.late_attach.attach_rc", ""),
        "late_detach_rc": fields.get("wlan_pd_tftp_server_trace.late_attach.detach_rc", ""),
        "late_no_qrtr_send": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.no_qrtr_send"))),
        "late_no_qmi_payload_send": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.no_qmi_payload_send"))),
        "late_duration_ms": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.duration_ms"))),
        "late_syscall_stop_count": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.syscall_stop_count"))),
        "late_syscall_record_count": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.syscall_record_count"))),
        "late_syscall_trace_truncated": int(prev1992.prev.intish(fields.get("wlan_pd_tftp_server_trace.late_attach.syscall_trace_truncated"))),
    }
    any_named_request = any(hit_counts.values())
    undecoded_inbound = recv_payload_records > 0 and not any_named_request
    return {
        "text_present": bool(text),
        "summary": summary,
        "record_count": len(record_list),
        "name_counts": name_counts,
        "recv_payload_record_count": recv_payload_records,
        "send_payload_record_count": send_payload_records,
        "qipcrtr_record_count": qipcrtr_records,
        "path_record_count": path_records,
        "token_hit_counts": hit_counts,
        "first_records": first_records,
        "first_payload_fragments": first_payload_fragments[:8],
        "compiled_ok": (
            summary["compiled"] == 1
            and summary["single_child"] == "tftp_server"
            and summary["late_attach_contract"] == 1
        ),
        "safety_contract_ok": (
            summary["no_qrtr_send"] == 1
            and summary["no_qmi_payload_send"] == 1
            and summary["late_no_qrtr_send"] == 1
            and summary["late_no_qmi_payload_send"] == 1
        ),
        "trace_active": summary["late_attach_rc"] == "0" or len(record_list) > 0,
        "any_named_request": any_named_request,
        "undecoded_inbound": undecoded_inbound,
        "server_check_seen": hit_counts["server_check"] > 0,
        "mcfg_seen": hit_counts["mcfg"] > 0,
        "mbn_hw_seen": hit_counts["mbn_hw"] > 0,
        "ota_firewall_seen": hit_counts["ota_firewall"] > 0,
        "wlanmdsp_seen": hit_counts["wlanmdsp"] > 0,
        "modem_seen": hit_counts["modem"] > 0,
    }


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    details["helper_completion"] = collect_helper_completion(handoff)
    details["readwrite_bridge"] = collect_readwrite_bridge()
    details["tftp_summary_fields"] = collect_tftp_summary_fields()
    details["tftp_syscall_trace"] = collect_tftp_syscall_trace()
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    bridge = trace.get("rfs_bridge") if isinstance(trace.get("rfs_bridge"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    readwrite = details.get("readwrite_bridge") if isinstance(details.get("readwrite_bridge"), dict) else {}
    tftp_summary = details.get("tftp_summary_fields") if isinstance(details.get("tftp_summary_fields"), dict) else {}
    tftp_trace = details.get("tftp_syscall_trace") if isinstance(details.get("tftp_syscall_trace"), dict) else {}
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("combined"))
        and bool(base.get("rfs_bridge_ok"))
        and bool(helper.get("ok"))
        and bool(readwrite.get("ok"))
        and bool(tftp_trace.get("compiled_ok"))
        and bool(tftp_trace.get("safety_contract_ok"))
    )
    if not route_ok:
        return {
            **base,
            "decision": f"v1998-{base.get('label', 'handoff-failed')}-rollback-blocked",
            "pass": False,
            "helper_completion_ok": bool(helper.get("ok")),
            "readwrite_bridge_ok": bool(readwrite.get("ok")),
            "tftp_trace_ok": bool(tftp_trace.get("compiled_ok")) and bool(tftp_trace.get("safety_contract_ok")),
            "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        }
    if int(tftp_summary.get("tftp_child_present", 0)) == 0 or int(tftp_summary.get("tftp_running", 0)) == 0:
        label = "native-tftp-server-not-running-readwrite-present"
        return {
            **base,
            "label": label,
            "decision": f"v1998-{label}-rollback-pass",
            "pass": True,
            "reason": "readwrite tmpfs bridge is present, but native tftp_server was absent or exited before the lower-window discriminator",
            "helper_completion_ok": True,
            "readwrite_bridge_ok": True,
            "tftp_trace_ok": True,
            "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        }
    if trace.get("requested") or tftp_trace.get("wlanmdsp_seen"):
        label = "native-tftp-wlanmdsp-request-progress"
        return {
            **base,
            "label": label,
            "decision": f"v1998-{label}-rollback-pass",
            "pass": True,
            "reason": "native tftp_server exposed a wlanmdsp request/progress edge after the readwrite bridge; stop before HAL/scan/connect",
            "helper_completion_ok": True,
            "readwrite_bridge_ok": True,
            "tftp_trace_ok": True,
            "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        }
    if base.get("publication_progress") or trace.get("loaded_or_up") or int(trace.get("wlan_pd_up_lines", 0)) > 0:
        label = "native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp"
        return {
            **base,
            "label": label,
            "decision": f"v1998-{label}-rollback-pass",
            "pass": True,
            "reason": "readwrite tmpfs bridge let the modem create server_check and native reached WLAN-PD UP; late tftp trace did not decode request path tokens",
            "helper_completion_ok": True,
            "readwrite_bridge_ok": True,
            "tftp_trace_ok": True,
            "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        }
    if (
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
        label = "native-tftp-server-check-or-mcfg-no-wlanmdsp"
        return {
            **base,
            "label": label,
            "decision": f"v1998-{label}-rollback-pass",
            "pass": True,
            "reason": "native tftp_server saw early modem tftp traffic, but not wlanmdsp; WLAN PD spawn remains the modem-internal decision",
            "helper_completion_ok": True,
            "readwrite_bridge_ok": True,
            "tftp_trace_ok": True,
            "tftp_trace_active": bool(tftp_trace.get("trace_active")),
        }
    if tftp_trace.get("undecoded_inbound"):
        label = "native-tftp-undecoded-inbound-no-wlanmdsp"
        return {
            **base,
            "label": label,
            "decision": f"v1998-{label}-rollback-pass",
            "pass": True,
            "reason": "native tftp_server received inbound QRTR payloads without decoded path tokens; decode offline before assuming zero tftp",
            "helper_completion_ok": True,
            "readwrite_bridge_ok": True,
            "tftp_trace_ok": True,
            "tftp_trace_active": True,
        }
    label = "native-tftp-zero-request-readwrite-present"
    return {
        **base,
        "label": label,
        "decision": f"v1998-{label}-rollback-pass",
        "pass": True,
        "reason": "readwrite tmpfs bridge and tftp_server were present, but no server_check/mcfg/mbn_hw/ota/wlanmdsp tftp request reached native tftp_server",
        "helper_completion_ok": True,
        "readwrite_bridge_ok": True,
        "tftp_trace_ok": True,
        "tftp_trace_active": bool(tftp_trace.get("trace_active")),
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    readwrite = details["readwrite_bridge"]
    tftp_summary = details["tftp_summary_fields"]
    tftp_trace = details["tftp_syscall_trace"]
    tftp_trace_summary = tftp_trace["summary"]
    light = trace["light_observer"]
    android = details["android_v1982"]
    rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper_completion", classification.get("helper_completion_ok"), f"version={details['helper_completion']['result_file_version']} probe_rc={details['helper_completion']['probe_run_rc']} child_exit={details['helper_completion']['child_exit_code']} timed_out={details['helper_completion']['timed_out']}"],
        ["readonly_bridge", classification.get("rfs_bridge_ok"), f"exact_exists={bridge['exact_exists']} nonzero={bridge['exact_nonzero']} open_rc={bridge['exact_open_rc']} sda29_write={bridge['sda29_write']}"],
        ["readwrite_bridge", classification.get("readwrite_bridge_ok"), f"exists={readwrite['readwrite_exists']} is_dir={readwrite['readwrite_is_dir']} mode={readwrite['readwrite_mode']} uid={readwrite['readwrite_uid']} gid={readwrite['readwrite_gid']} tmpfs={readwrite['readwrite_tmpfs_requested']} server_check_exists={readwrite['server_check_exists']}"],
        ["tftp_child", bool(tftp_summary.get("tftp_running")), f"present={tftp_summary.get('tftp_child_present')} observable={tftp_summary.get('tftp_observable')} running={tftp_summary.get('tftp_running')} summary_label={tftp_summary.get('label')}"],
        ["tftp_trace", classification.get("tftp_trace_active"), f"compiled={tftp_trace_summary['compiled']} attach_rc={tftp_trace_summary['late_attach_rc']} detach_rc={tftp_trace_summary['late_detach_rc']} records={tftp_trace['record_count']} stops={tftp_trace_summary['late_syscall_stop_count']} ms={tftp_trace_summary['late_duration_ms']} truncated={tftp_trace_summary['late_syscall_trace_truncated']}"],
        ["tftp_payloads", tftp_trace["any_named_request"], f"recv_payload={tftp_trace['recv_payload_record_count']} send_payload={tftp_trace['send_payload_record_count']} qipcrtr={tftp_trace['qipcrtr_record_count']} paths={tftp_trace['path_record_count']} names={tftp_trace['name_counts']}"],
        ["tftp_tokens", tftp_trace["token_hit_counts"], f"summary server_check={tftp_summary.get('requested_server_check')} mcfg={tftp_summary.get('requested_mcfg')} mbn_hw={tftp_summary.get('requested_mbn_hw')} ota={tftp_summary.get('requested_ota_firewall')} wlanmdsp={tftp_summary.get('requested_wlanmdsp')}"],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["wlanmdsp_request", trace["requested"], f"field={trace['requested_field']} tftp_lines={trace['tftp_wlanmdsp_lines']} failures={trace['wlanmdsp_failure_lines']}"],
        ["wlan_pd_publication", bool(trace.get("wlan_pd_up_lines")), f"pil_load={trace['pil_load_lines']} wlan_pd_up={trace['wlan_pd_up_lines']} wlfw69={trace['wlfw69_lines']} wlan0={trace['wlan0_lines']}"],
        ["android_v1982", android.get("requested_wlanmdsp", ""), f"wlan_pd={android.get('wlan_pd_up')} BDF={android.get('bdf')} wlan0={android.get('wlan0')} lines={android.get('wlanmdsp_line_count')}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1998 TFTP-Any Readwrite Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1998`",
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
        "## First TFTP Trace Records",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_records"]),
        *([] if tftp_trace["first_records"] else ["- `none`"]),
        "",
        "## First Decoded Payload Fragments",
        "",
        *(f"- `{line}`" for line in tftp_trace["first_payload_fragments"]),
        *([] if tftp_trace["first_payload_fragments"] else ["- `none`"]),
        "",
        "## First Native Wlanmdsp Lines",
        "",
        *(f"- `{line}`" for line in trace["first_wlanmdsp_lines"]),
        *([] if trace["first_wlanmdsp_lines"] else ["- `none`"]),
        "",
        "## First Native Load/UP Lines",
        "",
        *(f"- `{line}`" for line in trace["first_load_lines"]),
        *([] if trace["first_load_lines"] else ["- `none`"]),
        "",
        "## Branch",
        "",
        "- `native-tftp-zero-request-readwrite-present`: AP-side tftp infra is still not reached by the modem; next target is tftp service registration/reachability, not RIL/CNSS/pm-service strace.",
        "- `native-tftp-server-check-or-mcfg-no-wlanmdsp`: early tftp exists; WLAN PD spawn remains modem-internal and should move to modem-side DIAG.",
        "- `native-tftp-undecoded-inbound-no-wlanmdsp`: decode captured payloads offline before assigning zero-tftp.",
        "- `native-tftp-wlanmdsp-request-progress`: request/load edge appeared in tftp evidence; stop before Wi-Fi HAL/scan/connect.",
        "- `native-readwrite-bridge-wlan-pd-up-no-tokenized-tftp`: WLAN-PD reached UP after the readwrite bridge, but late tftp path tokens were not captured.",
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
        "- The only ptrace was the bounded single-child syscall trace of stock `tftp_server`; no AP-side multi-strace was run.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1997 test-boot flash-handoff, namespace-local tmpfs readwrite bridge, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev1992.CYCLE = CYCLE
    prev1992.OUT_DIR = OUT_DIR
    prev1992.HANDOFF_DIR = HANDOFF_DIR
    prev1992.HANDOFF_REPORT = HANDOFF_REPORT
    prev1992.REPORT_PATH = REPORT_PATH
    prev1992.V1991_OUT = V1997_OUT
    prev1992.V1991_INIT = V1997_INIT
    prev1992.V1991_BOOT = V1997_BOOT
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
