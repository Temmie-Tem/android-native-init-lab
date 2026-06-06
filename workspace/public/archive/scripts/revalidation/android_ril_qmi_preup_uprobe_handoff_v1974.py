#!/usr/bin/env python3
"""V1974 Android-good pre-UP RIL QMI send uprobe capture.

This extends the proven V1934 rollbackable Android handoff with pre-armed
tracefs uprobes on libqmi_cci send entrypoints.  The target is the producer
side of the normal internal-modem WLAN-PD edge: whether RIL emits QMI sends,
or at least DMS/NAS/WDS service lookups, before msm/modem/wlan_pd reaches UP.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

import android_libqmi_service69_positive_control_handoff_v1934 as v1934
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


CYCLE = "V1974"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1974-android-ril-qmi-preup-uprobe-handoff")
DEFAULT_REPORT_PATH = Path(
    "docs/reports/NATIVE_INIT_V1974_ANDROID_RIL_QMI_PREUP_UPROBE_2026-06-04.md"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1974-android-ril-qmi-preup-uprobe.txt")
MODULE_NAME = "a90_v1974_ril_qmi_preup"
REMOTE_MODULE_DIR = f"/data/adb/modules/{MODULE_NAME}"
REMOTE_EVIDENCE_DIR = "/data/local/tmp/a90-v1974-ril-qmi-preup"
REMOTE_STAGE_PREFIX = "/data/local/tmp/a90_v1974_ril_qmi_preup"
TRACEFS_GROUP = "a90rilqmi1974"

V1934_POST_FS_DATA_SCRIPT = v1934.post_fs_data_script
V1934_ANALYZE = v1934.analyze_pulled_evidence

SEND_EVENT_NAMES = (
    "libqmi_send_msg_sync_entry",
    "libqmi_send_msg_async_entry",
    "libqmi_send_raw_msg_sync_entry",
    "libqmi_send_raw_msg_async_entry",
)
TRACE_LINE_RE = re.compile(
    r"^\s*(?P<comm>.+?)-(?P<pid>\d+)\s+\[\d+\]\s+\S+\s+(?P<time>\d+\.\d+):\s+"
    r"(?P<event>[A-Za-z0-9_]+):(?P<body>.*)$"
)
KEY_VALUE_RE = re.compile(r"\b(?P<key>[A-Za-z0-9_]+)=(?P<value>0x[0-9a-fA-F]+|-?\d+)\b")
RIL_COMM_RE = re.compile(r"\brild\b|RILD", re.IGNORECASE)
LEAD_SERVICES = {0x01: "WDS", 0x02: "DMS", 0x03: "NAS"}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def module_prop() -> str:
    return "\n".join(
        [
            f"id={MODULE_NAME}",
            "name=A90 V1974 RIL QMI pre-UP observer",
            "version=1",
            "versionCode=1",
            "author=A90 native-init project",
            "description=Temporary read-only Android-good RIL QMI pre-UP uprobe observer. Remove after capture.",
            "",
        ]
    )


def patch_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise RuntimeError(f"post-fs-data patch anchor not found: {old[:120]!r}")
    return text.replace(old, new, 1)


def post_fs_data_script(samples: int, delay_us: int) -> str:
    original_event_names = v1934.LIBQMI_EVENT_NAMES
    v1934.LIBQMI_EVENT_NAMES = tuple(dict.fromkeys(original_event_names + SEND_EVENT_NAMES))
    try:
        text = V1934_POST_FS_DATA_SCRIPT(samples, delay_us)
    finally:
        v1934.LIBQMI_EVENT_NAMES = original_event_names

    text = text.replace(" -f -tt -s 256 -yy -e ", " -f -tt -s 256 -e ", 1)
    text = patch_once(
        text,
        "  register_libqmi_uprobe_event libqmi_xport_new_server_callback_call 4990 'svc_id=%x0 addr=%x1 event=%x2 version=%x3 cb=%x4' || true\n"
        "  LIBQMI_UPROBE_ARMED=1\n",
        "  register_libqmi_uprobe_event libqmi_xport_new_server_callback_call 4990 'svc_id=%x0 addr=%x1 event=%x2 version=%x3 cb=%x4' || true\n"
        "  register_libqmi_uprobe_event libqmi_send_msg_sync_entry 6dc0 'client=%x0 msg_id=%x1 req=%x2 req_len=%x3 resp=%x4 resp_len=%x5 timeout=%x6' || true\n"
        "  register_libqmi_uprobe_event libqmi_send_msg_async_entry 659c 'client=%x0 msg_id=%x1 req=%x2 req_len=%x3 resp_cb=%x4 resp_cb_data=%x5 txn_handle=%x6' || true\n"
        "  register_libqmi_uprobe_event libqmi_send_raw_msg_sync_entry 6ae0 'client=%x0 msg_id=%x1 req=%x2 req_len=%x3 resp=%x4 resp_len=%x5 timeout=%x6' || true\n"
        "  register_libqmi_uprobe_event libqmi_send_raw_msg_async_entry 5f88 'client=%x0 msg_id=%x1 req=%x2 req_len=%x3 resp_cb=%x4 resp_cb_data=%x5 txn_handle=%x6' || true\n"
        "  LIBQMI_UPROBE_ARMED=1\n",
    )
    text = patch_once(
        text,
        '  libqmi_new69_hits="$(grep -Ec "libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=0x45|libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=69" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  echo "hit_count=${libqmi_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n',
        '  libqmi_new69_hits="$(grep -Ec "libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=0x45|libqmi_xport_new_server_(service|signal|callback_call):.*svc_id=69" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  libqmi_send_hits="$(grep -Ec "libqmi_send_(msg|raw)_msg?_|libqmi_send_" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  libqmi_rild_send_hits="$(grep -Ec "rild-[0-9].*libqmi_send_|RILD-[0-9].*libqmi_send_" "$LIBQMI_UPROBE" 2>/dev/null || true)"\n'
        '  echo "hit_count=${libqmi_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        '  echo "send_hit_count=${libqmi_send_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n'
        '  echo "rild_send_hit_count=${libqmi_rild_send_hits:-0}" >> "$LIBQMI_UPROBE_SUMMARY"\n',
    )
    return text


def parse_trace_line(line: str) -> dict[str, Any] | None:
    match = TRACE_LINE_RE.match(line)
    if not match:
        return None
    body = match.group("body")
    fields: dict[str, int] = {}
    for kv in KEY_VALUE_RE.finditer(body):
        fields[kv.group("key")] = int(kv.group("value"), 0)
    return {
        "comm": match.group("comm").strip(),
        "pid": int(match.group("pid")),
        "time": float(match.group("time")),
        "event": match.group("event"),
        "fields": fields,
        "line": line.strip(),
    }


def read_file(path: Path, limit: int = 4_000_000) -> str:
    return v1934.read_file(path, limit=limit)


def trace_events(trace: str) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for line in trace.splitlines():
        event = parse_trace_line(line)
        if event:
            parsed.append(event)
    return parsed


def is_rild(event: dict[str, Any]) -> bool:
    return bool(RIL_COMM_RE.search(event["comm"]))


def hex_list(values: list[int]) -> list[str]:
    return [f"0x{value:04x}" for value in values]


def service_name(value: int) -> str:
    return LEAD_SERVICES.get(value, f"service{value}")


def summarize_uprobe_edges(events: list[dict[str, Any]], wlan_pd_time: float | None) -> dict[str, Any]:
    send_events = [event for event in events if event["event"] in SEND_EVENT_NAMES]
    rild_send_events = [event for event in send_events if is_rild(event)]
    lookup_events = [event for event in events if event["event"] == "libqmi_get_service_list_lookup_call"]
    lead_lookup_events = [
        event for event in lookup_events if event["fields"].get("svc_id") in LEAD_SERVICES
    ]
    rild_lookup_events = [event for event in lookup_events if is_rild(event)]
    rild_lead_lookup_events = [
        event for event in rild_lookup_events if event["fields"].get("svc_id") in LEAD_SERVICES
    ]

    def before_up(event: dict[str, Any]) -> bool:
        return wlan_pd_time is not None and event["time"] < wlan_pd_time

    send_pre = [event for event in send_events if before_up(event)]
    rild_send_pre = [event for event in rild_send_events if before_up(event)]
    lead_lookup_pre = [event for event in lead_lookup_events if before_up(event)]
    rild_lead_lookup_pre = [event for event in rild_lead_lookup_events if before_up(event)]
    rild_lookup_pre = [event for event in rild_lookup_events if before_up(event)]

    first_send_pre = send_pre[0]["line"] if send_pre else ""
    first_rild_send = rild_send_events[0]["line"] if rild_send_events else ""
    first_rild_send_pre = rild_send_pre[0]["line"] if rild_send_pre else ""
    first_lead_lookup_pre = lead_lookup_pre[0]["line"] if lead_lookup_pre else ""
    first_rild_lead_lookup_pre = rild_lead_lookup_pre[0]["line"] if rild_lead_lookup_pre else ""

    lead_lookup_services = sorted({event["fields"].get("svc_id") for event in lead_lookup_events if event["fields"].get("svc_id") is not None})
    lead_lookup_pre_services = sorted({event["fields"].get("svc_id") for event in lead_lookup_pre if event["fields"].get("svc_id") is not None})
    rild_lead_lookup_services = sorted({event["fields"].get("svc_id") for event in rild_lead_lookup_events if event["fields"].get("svc_id") is not None})
    rild_lead_lookup_pre_services = sorted({event["fields"].get("svc_id") for event in rild_lead_lookup_pre if event["fields"].get("svc_id") is not None})
    send_pre_msg_ids = sorted({event["fields"].get("msg_id") for event in send_pre if event["fields"].get("msg_id") is not None})
    rild_send_msg_ids = sorted({event["fields"].get("msg_id") for event in rild_send_events if event["fields"].get("msg_id") is not None})
    rild_send_pre_msg_ids = sorted({event["fields"].get("msg_id") for event in rild_send_pre if event["fields"].get("msg_id") is not None})

    return {
        "libqmi_event_count": len(events),
        "send_event_count": len(send_events),
        "send_pre_wlanpd_count": len(send_pre),
        "send_pre_wlanpd_msg_ids": hex_list(send_pre_msg_ids),
        "rild_send_event_count": len(rild_send_events),
        "rild_send_pre_wlanpd_count": len(rild_send_pre),
        "rild_lookup_event_count": len(rild_lookup_events),
        "rild_lookup_pre_wlanpd_count": len(rild_lookup_pre),
        "lead_lookup_event_count": len(lead_lookup_events),
        "lead_lookup_pre_wlanpd_count": len(lead_lookup_pre),
        "lead_lookup_services": [service_name(value) for value in lead_lookup_services],
        "lead_lookup_pre_wlanpd_services": [service_name(value) for value in lead_lookup_pre_services],
        "rild_lead_lookup_event_count": len(rild_lead_lookup_events),
        "rild_lead_lookup_pre_wlanpd_count": len(rild_lead_lookup_pre),
        "explicit_rild_lead_lookup_services": [service_name(value) for value in rild_lead_lookup_services],
        "explicit_rild_lead_lookup_pre_wlanpd_services": [service_name(value) for value in rild_lead_lookup_pre_services],
        "rild_send_msg_ids": hex_list(rild_send_msg_ids),
        "rild_send_pre_wlanpd_msg_ids": hex_list(rild_send_pre_msg_ids),
        "first_send_pre_wlanpd": first_send_pre,
        "first_rild_send": first_rild_send,
        "first_rild_send_pre_wlanpd": first_rild_send_pre,
        "first_lead_lookup_pre_wlanpd": first_lead_lookup_pre,
        "first_explicit_rild_lead_lookup_pre_wlanpd": first_rild_lead_lookup_pre,
    }


def analyze_pulled_evidence(store: v1934.EvidenceStore) -> dict[str, Any]:
    analysis = V1934_ANALYZE(store)
    evidence_dir = v1934.base.evidence_base(store)
    libqmi_trace = read_file(evidence_dir / "libqmi-uprobe-trace.txt")
    dmesg = analysis.get("dmesg") or {}
    wlan_pd_time = dmesg.get("wlan_pd_indication_time_s")
    events = trace_events(libqmi_trace)
    analysis["v1974_uprobe"] = summarize_uprobe_edges(events, wlan_pd_time)
    return analysis


def stateup_complete(analysis: dict[str, Any]) -> bool:
    dmesg = analysis.get("dmesg") or {}
    return (
        int(analysis.get("pm_vote_count") or 0) > 0
        and int(analysis.get("wlfw_service_request_count") or 0) > 0
        and int(analysis.get("wlan_pd_indication_count") or 0) > 0
        and int(analysis.get("wlanmdsp_count") or 0) > 0
        and dmesg.get("wlan0_time_s") is not None
    )


def contaminated(analysis: dict[str, Any]) -> bool:
    dmesg = analysis.get("dmesg") or {}
    return (
        bool(dmesg.get("degraded_257s_like"))
        or int(dmesg.get("pcie_mhi_before_wlan0") or 0) > 0
        or int(dmesg.get("esoc_boot_failed_before_wlan0") or 0) > 0
    )


def classify_result(
    base_decision: str,
    base_pass: bool,
    context: dict[str, Any],
    parser_results: dict[str, Any],
    selftest_ok: bool,
) -> tuple[str, bool, str, str]:
    if not selftest_ok:
        return "v1974-rollback-selftest-failed", False, "native rollback did not prove selftest fail=0", "rollback-selftest-failed"
    if not base_pass:
        return f"v1974-base-handoff-failed-{base_decision}", False, "underlying Android handoff did not complete", "android-handoff-failed"
    analysis = context.get("analysis") or {}
    if contaminated(analysis):
        return (
            "v1974-android-capture-rejected-degraded-or-pcie-mhi",
            False,
            "Android capture was rejected because it is degraded or has pre-wlan0 PCIe/MHI/eSoC contamination",
            "android-capture-rejected-degraded-or-pcie-mhi",
        )
    if not stateup_complete(analysis):
        return (
            "v1974-android-normal-stateup-incomplete-rollback-pass",
            False,
            "capture does not contain the normal PM vote -> wlan_pd -> wlanmdsp -> wlan0 state-up sequence",
            "android-normal-stateup-incomplete",
        )
    parser_ok = bool((parser_results.get("v1894") or {}).get("pass")) and bool((parser_results.get("v1888") or {}).get("pass"))
    if not parser_ok:
        return "v1974-parser-chain-failed-rollback-pass", False, "Android capture succeeded but V1894/V1888 parser chain did not pass", "parser-chain-failed"

    uprobe = analysis.get("v1974_uprobe") or {}
    if int(uprobe.get("send_event_count") or 0) <= 0:
        return (
            "v1974-libqmi-send-uprobe-incomplete-rollback-pass",
            False,
            "normal Android state-up completed, but libqmi send uprobes did not produce send events",
            "libqmi-send-uprobe-incomplete",
        )
    if int(uprobe.get("rild_send_pre_wlanpd_count") or 0) > 0:
        return (
            "v1974-rild-qmi-send-pre-wlanpd-up-rollback-pass",
            True,
            "pre-armed libqmi send uprobes captured rild QMI sends before wlan_pd UP",
            "rild-qmi-send-pre-wlanpd-up",
        )
    if int(uprobe.get("rild_lead_lookup_pre_wlanpd_count") or 0) > 0:
        return (
            "v1974-rild-dms-nas-wds-lookup-preup-no-send-preup-rollback-pass",
            True,
            "rild performed DMS/NAS/WDS service lookups before wlan_pd UP, but no rild QMI send was captured before the edge",
            "rild-lead-lookup-preup-no-send-preup",
        )
    if int(uprobe.get("lead_lookup_pre_wlanpd_count") or 0) > 0:
        return (
            "v1974-anonymous-dms-nas-wds-lookup-preup-no-explicit-rild-preup-rollback-pass",
            True,
            "DMS/NAS/WDS service lookups occurred before wlan_pd UP, but no explicit rild comm was present before the edge; the pre-UP producer is not proven to be RIL",
            "anonymous-lead-lookup-preup-no-explicit-rild-preup",
        )
    return (
        "v1974-no-rild-qmi-producer-before-wlanpd-up-rollback-pass",
        True,
        "normal Android state-up completed and libqmi send uprobes worked, but no rild send or DMS/NAS/WDS lookup was captured before wlan_pd UP",
        "no-rild-qmi-producer-before-wlanpd-up",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    context = manifest["context"]
    analysis = context.get("analysis") or {}
    dmesg = analysis.get("dmesg") or {}
    uprobe = analysis.get("v1974_uprobe") or {}
    parser_results = manifest.get("parser_results") or {}
    rows = [
        ["wlan_pd UP", dmesg.get("wlan_pd_indication_time_s")],
        ["wlan0", dmesg.get("wlan0_time_s")],
        ["contamination pcie-mhi/esoc/degraded257", f"{dmesg.get('pcie_mhi_before_wlan0')}/{dmesg.get('esoc_boot_failed_before_wlan0')}/{dmesg.get('degraded_257s_like')}"],
        ["libqmi events/send/rild-send", f"{uprobe.get('libqmi_event_count')}/{uprobe.get('send_event_count')}/{uprobe.get('rild_send_event_count')}"],
        ["all send pre-UP count", uprobe.get("send_pre_wlanpd_count")],
        ["all send pre-UP msg IDs", json.dumps(uprobe.get("send_pre_wlanpd_msg_ids") or [])],
        ["rild send pre-UP count", uprobe.get("rild_send_pre_wlanpd_count")],
        ["rild send pre-UP msg IDs", json.dumps(uprobe.get("rild_send_pre_wlanpd_msg_ids") or [])],
        ["any lead lookup pre-UP count", uprobe.get("lead_lookup_pre_wlanpd_count")],
        ["any lead lookup pre-UP services", json.dumps(uprobe.get("lead_lookup_pre_wlanpd_services") or [])],
        ["explicit rild lead lookup pre-UP count", uprobe.get("rild_lead_lookup_pre_wlanpd_count")],
        ["explicit rild lead lookup pre-UP services", json.dumps(uprobe.get("explicit_rild_lead_lookup_pre_wlanpd_services") or [])],
        ["first send pre-UP", uprobe.get("first_send_pre_wlanpd")],
        ["first rild send", uprobe.get("first_rild_send")],
        ["first rild send pre-UP", uprobe.get("first_rild_send_pre_wlanpd")],
        ["first lead lookup pre-UP", uprobe.get("first_lead_lookup_pre_wlanpd")],
        ["first explicit rild lead lookup pre-UP", uprobe.get("first_explicit_rild_lead_lookup_pre_wlanpd")],
    ]
    return "\n".join(
        [
            "# Native Init V1974 Android RIL QMI Pre-UP Uprobe",
            "",
            "## Summary",
            "",
            f"- Cycle: `{CYCLE}`",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Pass: `{manifest['pass']}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Producer Edge",
            "",
            markdown_table(["field", "value"], [[str(cell) for cell in row] for row in rows]),
            "",
            "## Parser Chain",
            "",
            markdown_table(
                ["parser", "decision", "label", "pass", "out_dir"],
                [
                    [
                        "V1894",
                        (parser_results.get("v1894") or {}).get("decision"),
                        (parser_results.get("v1894") or {}).get("label"),
                        (parser_results.get("v1894") or {}).get("pass"),
                        (parser_results.get("v1894") or {}).get("out_dir"),
                    ],
                    [
                        "V1888",
                        (parser_results.get("v1888") or {}).get("decision"),
                        (parser_results.get("v1888") or {}).get("label"),
                        (parser_results.get("v1888") or {}).get("pass"),
                        (parser_results.get("v1888") or {}).get("out_dir"),
                    ],
                ],
            ),
            "",
            "## Scope",
            "",
            "- Internal-modem Android-good producer measurement only.",
            "- Direct send-path uprobes are pre-armed on `/vendor/lib64/libqmi_cci.so` before `rild` starts.",
            "- The result is a producer classifier, not a native Wi-Fi bring-up attempt.",
            "",
            "## Safety",
            "",
            "Rollbackable Android-handoff to native v724 only. Android-side writes are limited to the temporary Magisk module, bounded evidence directory, and bounded tracefs uprobe/kprobe controls for observation. No Wi-Fi HAL start, scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or partition write beyond declared boot-image handoff/rollback.",
            "",
            "## Rollback Gate",
            "",
            f"- native rollback selftest fail=0: `{manifest['rollback_selftest_fail0']}`",
            f"- base handoff decision/pass: `{manifest['base_decision']}` / `{manifest['base_pass']}`",
            "",
        ]
    )


def configure_v1974() -> None:
    v1934.CYCLE = CYCLE
    v1934.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1934.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    v1934.LATEST_POINTER = LATEST_POINTER
    v1934.MODULE_NAME = MODULE_NAME
    v1934.REMOTE_MODULE_DIR = REMOTE_MODULE_DIR
    v1934.REMOTE_EVIDENCE_DIR = REMOTE_EVIDENCE_DIR
    v1934.REMOTE_STAGE_PREFIX = REMOTE_STAGE_PREFIX
    v1934.TRACEFS_GROUP = TRACEFS_GROUP
    v1934.module_prop = module_prop
    v1934.post_fs_data_script = post_fs_data_script
    v1934.analyze_pulled_evidence = analyze_pulled_evidence
    v1934.classify_result = classify_result
    v1934.render_summary = render_summary


def main() -> int:
    configure_v1974()
    v1934.configure_base()
    args = v1934.base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    execute = args.command == "run"
    v1934.base.configure_v1521_engine()
    steps, context, base_decision, base_pass = v1934.base.v1521.execute_plan(args, store, execute=execute)
    parser_results: dict[str, Any] = {}
    if execute and base_pass:
        android_dir = v1934.base.evidence_base(store)
        for name, command, timeout, manifest_path in v1934.parser_commands(store, android_dir):
            step = v1934.base.execute_parser_step(store, name, command, timeout, execute=True)
            steps.append(step)
            key = "v1894" if "v1894" in name else "v1888"
            parser_results[key] = v1934.base.read_json(manifest_path)
    elif not execute:
        for name, command, timeout, _manifest_path in v1934.parser_commands(store, v1934.base.evidence_base(store)):
            steps.append(v1934.base.execute_parser_step(store, name, command, timeout, execute=False))

    selftest_ok = v1934.base.rollback_selftest_ok(store, steps) if execute else False
    if execute:
        decision, pass_ok, reason, label = classify_result(base_decision, base_pass, context, parser_results, selftest_ok)
    else:
        decision = (
            "v1974-android-ril-qmi-preup-uprobe-plan-ready"
            if args.command == "plan"
            else "v1974-android-ril-qmi-preup-uprobe-dryrun-ready"
        )
        pass_ok = bool(base_pass)
        reason = "plan/dry-run completed without Android-good live capture"
        label = "android-ril-qmi-preup-uprobe-handoff-ready"

    manifest = {
        "cycle": CYCLE,
        "generated_at": now_iso(),
        "command": args.command,
        "base_decision": base_decision,
        "base_pass": base_pass,
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "reason": reason,
        "out_dir": rel(store.run_dir),
        "host": collect_host_metadata(),
        "context": context,
        "parser_results": parser_results,
        "rollback_selftest_fail0": selftest_ok,
        "steps": [asdict(step) for step in steps],
        "device_commands_executed": execute,
        "device_mutations": execute,
        "temporary_magisk_module_executed": execute,
        "temporary_magisk_module_cleanup_requested": execute,
        "tracefs_uprobe_control_executed": execute,
        "tracefs_kprobe_control_executed": execute,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "pmic_gpio_gdsc_regulator_write_executed": False,
        "forced_rc1_case_write_executed": False,
        "subsys_esoc0_open_executed": False,
        "fake_online_executed": False,
        "blind_esoc_notify_executed": False,
        "boot_done_spoof_executed": False,
        "global_pci_rescan_executed": False,
        "platform_bind_unbind_executed": False,
        "flash_executed": execute,
        "boot_image_write_executed": execute,
        "partition_write_executed": False,
    }
    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.write_report:
        write_private_text(repo_path(DEFAULT_REPORT_PATH), summary)
    print(f"decision: {manifest['decision']}")
    print(f"pass:     {manifest['pass']}")
    print(f"label:    {manifest['label']}")
    print(f"reason:   {manifest['reason']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
