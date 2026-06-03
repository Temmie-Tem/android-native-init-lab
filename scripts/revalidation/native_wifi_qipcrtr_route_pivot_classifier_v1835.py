#!/usr/bin/env python3
"""V1835 host-only classifier for the post-bound-QIPCRTR route pivot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1835"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1834-qipcrtr-bound-recv-poll-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1835-qipcrtr-route-pivot-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1835_QIPCRTR_ROUTE_PIVOT_CLASSIFIER_2026-06-03.md"
)


BOUND_KEYS = [
    "qipcrtr_bound_recv_label",
    "qipcrtr_bound_recv_contract_ok",
    "qipcrtr_bound_recv_safety_ok",
    "qipcrtr_bound_recv_mode",
    "qipcrtr_bound_recv_family",
    "qipcrtr_bound_recv_type",
    "qipcrtr_bound_recv_open_rc",
    "qipcrtr_bound_recv_before_rc",
    "qipcrtr_bound_recv_before_node",
    "qipcrtr_bound_recv_before_port",
    "qipcrtr_bound_recv_request_family",
    "qipcrtr_bound_recv_request_node",
    "qipcrtr_bound_recv_request_port",
    "qipcrtr_bound_recv_bind_rc",
    "qipcrtr_bound_recv_after_rc",
    "qipcrtr_bound_recv_after_family",
    "qipcrtr_bound_recv_after_node",
    "qipcrtr_bound_recv_after_port",
    "qipcrtr_bound_recv_poll_attempted",
    "qipcrtr_bound_recv_poll_timeout_ms",
    "qipcrtr_bound_recv_set_nonblock_rc",
    "qipcrtr_bound_recv_poll_rc",
    "qipcrtr_bound_recv_poll_timeout",
    "qipcrtr_bound_recv_poll_revents",
    "qipcrtr_bound_recv_recv_rc",
    "qipcrtr_bound_recv_recv_skipped",
    "qipcrtr_bound_recv_recv_skip_reason",
    "qipcrtr_bound_recv_close_rc",
    "qipcrtr_bound_recv_before_sockets",
    "qipcrtr_bound_recv_while_before_poll_sockets",
    "qipcrtr_bound_recv_while_after_poll_sockets",
    "qipcrtr_bound_recv_after_close_sockets",
    "qipcrtr_bound_recv_no_connect",
    "qipcrtr_bound_recv_no_send",
    "qipcrtr_bound_recv_no_lookup_send",
    "qipcrtr_bound_recv_no_control_payload",
    "qipcrtr_bound_recv_no_service_start",
    "qipcrtr_bound_recv_poll_timed_out",
    "qipcrtr_bound_recv_port_nonzero",
    "qipcrtr_bound_recv_closed",
    "qipcrtr_bound_recv_packet_received",
]

QRTR_CASE_KEYS = [
    "service",
    "instance",
    "qmi_attempted",
    "send_attempted",
    "new_lookup_send.rc",
    "del_lookup_send.rc",
    "readback.events",
    "readback.service_events",
    "readback.empty_events",
    "readback.end_of_list",
    "readback.timeout",
    "status",
]

NOTIFIER_KEYS = [
    "allowed",
    "qmi_payload",
    "service",
    "instance",
    "service_name",
    "phase",
    "endpoint.status",
    "endpoint.node",
    "endpoint.port",
    "send_attempted",
    "register_send.rc",
    "response_success",
    "response_curr_state",
    "response_curr_state_name",
    "indication_seen",
    "ack_sent",
    "timing.hold_ms",
    "timing.poll_timeout",
    "result",
]

LATE_PROBE_KEYS = [
    "allowed",
    "qmi_payload",
    "service",
    "instance",
    "service_name",
    "phase",
    "endpoint.status",
    "endpoint.node",
    "endpoint.port",
    "lookup_attempted",
    "result",
]

SERVLOC_KEYS = [
    "allowed",
    "qmi_payload",
    "service",
    "instance",
    "service_name",
    "endpoint.status",
    "endpoint.node",
    "endpoint.port",
    "send_attempted",
    "send.rc",
    "response_success",
    "result",
    "domain_count",
    "wlan_like_domains",
    "domain.0.name",
    "domain.0.instance_id",
]


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    return prev1796.intish(value)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value) and str(value) not in {"0", "False", "false", "None", ""}


def collect(fields: dict[str, str], prefix: str, keys: list[str]) -> dict[str, str]:
    return {key: fields.get(prefix + key, "") for key in keys}


def qrtr_case(fields: dict[str, str], index: int) -> dict[str, str]:
    return collect(fields, f"wifi_companion_qrtr_readback.case_{index}.", QRTR_CASE_KEYS)


def wlfw_case_empty(case: dict[str, str]) -> bool:
    return (
        intish(case.get("readback.service_events")) == 0
        and intish(case.get("readback.empty_events")) > 0
        and intish(case.get("readback.end_of_list")) > 0
        and intish(case.get("readback.timeout")) == 0
        and case.get("status") == "complete"
    )


def notifier_uninit(listener: dict[str, str]) -> bool:
    return (
        listener.get("allowed") == "1"
        and listener.get("qmi_payload") == "1"
        and listener.get("endpoint.status") == "found"
        and listener.get("response_success") == "1"
        and listener.get("response_curr_state_name") == "uninit"
        and intish(listener.get("indication_seen")) == 0
        and listener.get("result") == "listener-response-success"
    )


def collect_details(source: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    gate = source.get("gate", {})
    details: dict[str, Any] = {
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_DIR / "manifest.json"),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "safety_ok": gate.get("safety_ok"),
        "lower_safety_ok": gate.get("lower_safety_ok"),
        "klog_safety_ok": gate.get("klog_safety_ok"),
        "devnode_safety_ok": gate.get("devnode_safety_ok"),
        "qipcrtr_socket_safety_ok": gate.get("qipcrtr_socket_safety_ok"),
        "qipcrtr_autobind_safety_ok": gate.get("qipcrtr_autobind_safety_ok"),
        "qipcrtr_local_bind_safety_ok": gate.get("qipcrtr_local_bind_safety_ok"),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "service74_raw_klog_label": gate.get("service74_raw_klog_label", ""),
        "pm_service_devnode_projection_label": gate.get("pm_service_devnode_projection_label", ""),
        "pm_service_entry_names": gate.get("pm_service_entry_names", ""),
        "pm_service_entry_devnodes": gate.get("pm_service_entry_devnodes", ""),
        "pm_service_list_commit_hits": gate.get("pm_service_add_peripheral_list_commit_hits", ""),
        "pm_service_init_fail_hits": gate.get("pm_service_add_peripheral_init_fail_hits", ""),
        "pm_client_register_rc": gate.get("pm_client_register_rc", ""),
        "pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
        "pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
        "provider_seen": gate.get("provider_seen", ""),
        "as_interface_hits": gate.get("as_interface_hits", ""),
        "register_tx_hits": gate.get("register_tx_hits", ""),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "raw_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "raw_servloc_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "raw_wlan_fw_counts": gate.get("raw_wlan_fw_counts", ""),
        "raw_wlan_pd_domain_counts": gate.get("raw_wlan_pd_domain_counts", ""),
        "raw_qmi_server_connected_counts": gate.get("raw_qmi_server_connected_counts", ""),
        "raw_service180_text_counts": gate.get("raw_service180_text_counts", ""),
        "raw_service74_text_counts": gate.get("raw_service74_text_counts", ""),
        "raw_wlan_pd_text_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "raw_wlfw_counts": gate.get("raw_wlfw_counts", ""),
        "raw_service74_text_positive": gate.get("raw_service74_text_positive"),
        "raw_wlan_pd_text_positive": gate.get("raw_wlan_pd_text_positive"),
        "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "lower_mhi_present": gate.get("lower_mhi_present"),
        "lower_service69_progress": gate.get("lower_service69_progress"),
        "lower_wlan0_present": gate.get("lower_wlan0_present"),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen", ""),
        "wlan0_present": gate.get("wlan0_present", ""),
        "service_notifier_early_state": gate.get("service_notifier_early_state", ""),
        "service_notifier_late_state": gate.get("service_notifier_late_state", ""),
        "qrtr_readback_label": gate.get("qrtr_readback_label", ""),
        "servloc_domain_label": gate.get("servloc_domain_label", ""),
        "servnotif_label": gate.get("servnotif_label", ""),
    }
    details.update({key: gate.get(key, "") for key in BOUND_KEYS})
    details.update(
        {
            "qrtr_readback_allowed": fields.get("wifi_companion_qrtr_readback.allowed", ""),
            "qrtr_readback_matrix": fields.get("wifi_companion_qrtr_readback.matrix", ""),
            "qrtr_readback_qmi_payload": fields.get("wifi_companion_qrtr_readback.qmi_payload", ""),
            "qrtr_readback_send_attempted": fields.get("wifi_companion_qrtr_readback.send_attempted", ""),
            "qrtr_readback_result": fields.get("wifi_companion_qrtr_readback.result", ""),
            "qrtr_case_0": qrtr_case(fields, 0),
            "qrtr_case_1": qrtr_case(fields, 1),
            "servloc_domain": collect(fields, "wifi_companion_servloc_domain_list.", SERVLOC_KEYS),
            "service_notifier_early": collect(fields, "wifi_companion_service_notifier_listener.", NOTIFIER_KEYS),
            "service_notifier_late_probe": collect(fields, "wifi_companion_service_notifier_late_probe.", LATE_PROBE_KEYS),
            "service_notifier_late": collect(fields, "wifi_companion_service_notifier_late_listener.", NOTIFIER_KEYS),
        }
    )
    if not details["qrtr_readback_label"]:
        details["qrtr_readback_label"] = (
            "wlfw-readback-empty"
            if (
                details["qrtr_readback_allowed"] == "1"
                and details["qrtr_readback_qmi_payload"] == "0"
                and details["qrtr_readback_send_attempted"] == "1"
                and details["qrtr_readback_result"] == "complete"
                and wlfw_case_empty(details["qrtr_case_0"])
                and wlfw_case_empty(details["qrtr_case_1"])
            )
            else "wlfw-readback-review"
        )
    if not details["servloc_domain_label"]:
        servloc = details["servloc_domain"]
        details["servloc_domain_label"] = (
            "servloc-domain-wlan-pd-instance180"
            if (
                servloc.get("allowed") == "1"
                and servloc.get("qmi_payload") == "1"
                and servloc.get("response_success") == "1"
                and servloc.get("result") == "domain-list-response-success"
                and servloc.get("domain.0.name") == "msm/modem/wlan_pd"
                and servloc.get("domain.0.instance_id") == "180"
            )
            else "servloc-domain-review"
        )
    if not details["servnotif_label"]:
        details["servnotif_label"] = (
            "service-notifier-uninit"
            if notifier_uninit(details["service_notifier_early"])
            and notifier_uninit(details["service_notifier_late"])
            else "service-notifier-review"
        )
    return details


def bound_poll_timeout_shape(details: dict[str, Any]) -> bool:
    return (
        details.get("qipcrtr_bound_recv_label") == "qipcrtr-bound-recv-poll-timeout-passive"
        and boolish(details.get("qipcrtr_bound_recv_contract_ok"))
        and boolish(details.get("qipcrtr_bound_recv_safety_ok"))
        and details.get("qipcrtr_bound_recv_mode") == "observed-local-node-bind-poll-recv-close"
        and details.get("qipcrtr_bound_recv_family") == "AF_QIPCRTR"
        and details.get("qipcrtr_bound_recv_type") == "SOCK_DGRAM"
        and details.get("qipcrtr_bound_recv_open_rc") == "0"
        and details.get("qipcrtr_bound_recv_bind_rc") == "0"
        and details.get("qipcrtr_bound_recv_close_rc") == "0"
        and details.get("qipcrtr_bound_recv_before_node") == "1"
        and details.get("qipcrtr_bound_recv_before_port") == "0"
        and details.get("qipcrtr_bound_recv_request_family") == "42"
        and details.get("qipcrtr_bound_recv_request_node") == "1"
        and details.get("qipcrtr_bound_recv_request_port") == "0"
        and details.get("qipcrtr_bound_recv_after_family") == "42"
        and details.get("qipcrtr_bound_recv_after_node") == "1"
        and intish(details.get("qipcrtr_bound_recv_after_port")) > 0
        and details.get("qipcrtr_bound_recv_poll_attempted") == "1"
        and details.get("qipcrtr_bound_recv_poll_timeout_ms") == "250"
        and details.get("qipcrtr_bound_recv_set_nonblock_rc") == "0"
        and details.get("qipcrtr_bound_recv_poll_rc") == "0"
        and details.get("qipcrtr_bound_recv_poll_timeout") == "1"
        and details.get("qipcrtr_bound_recv_poll_revents") == "0"
        and details.get("qipcrtr_bound_recv_recv_skipped") == "1"
        and details.get("qipcrtr_bound_recv_recv_skip_reason") == "poll-timeout"
        and not boolish(details.get("qipcrtr_bound_recv_packet_received"))
        and all(
            intish(details.get(key)) == 0
            for key in (
                "qipcrtr_bound_recv_before_sockets",
                "qipcrtr_bound_recv_while_before_poll_sockets",
                "qipcrtr_bound_recv_while_after_poll_sockets",
                "qipcrtr_bound_recv_after_close_sockets",
            )
        )
        and all(
            details.get(key) == "1"
            for key in (
                "qipcrtr_bound_recv_no_connect",
                "qipcrtr_bound_recv_no_send",
                "qipcrtr_bound_recv_no_lookup_send",
                "qipcrtr_bound_recv_no_control_payload",
                "qipcrtr_bound_recv_no_service_start",
            )
        )
    )


def inherited_qrtr_qmi_shape(details: dict[str, Any]) -> bool:
    servloc = details["servloc_domain"]
    early = details["service_notifier_early"]
    late_probe = details["service_notifier_late_probe"]
    late = details["service_notifier_late"]
    return (
        details.get("qrtr_readback_label") == "wlfw-readback-empty"
        and details.get("qrtr_readback_allowed") == "1"
        and details.get("qrtr_readback_qmi_payload") == "0"
        and details.get("qrtr_readback_send_attempted") == "1"
        and details.get("qrtr_readback_result") == "complete"
        and wlfw_case_empty(details["qrtr_case_0"])
        and wlfw_case_empty(details["qrtr_case_1"])
        and details.get("servloc_domain_label") == "servloc-domain-wlan-pd-instance180"
        and servloc.get("allowed") == "1"
        and servloc.get("qmi_payload") == "1"
        and servloc.get("endpoint.status") == "found"
        and servloc.get("response_success") == "1"
        and servloc.get("result") == "domain-list-response-success"
        and servloc.get("domain.0.name") == "msm/modem/wlan_pd"
        and servloc.get("domain.0.instance_id") == "180"
        and details.get("servnotif_label") == "service-notifier-uninit"
        and notifier_uninit(early)
        and late_probe.get("allowed") == "1"
        and late_probe.get("qmi_payload") == "0"
        and late_probe.get("endpoint.status") == "found"
        and late_probe.get("result") == "endpoint-found"
        and notifier_uninit(late)
    )


def lower_still_blocked(details: dict[str, Any]) -> bool:
    return (
        details.get("post_pm_lower_state_label") == "stable-mdm3-offlining"
        and details.get("service74_raw_klog_label") == "service74-raw-absent"
        and details.get("raw_service180_text_counts") == "1,1,1"
        and details.get("raw_service74_text_counts") == "0,0,0"
        and details.get("raw_wlan_pd_text_counts") == "0,0,0"
        and details.get("service_notifier_early_state") == "uninit"
        and details.get("service_notifier_late_state") == "uninit"
        and details.get("lower_mdm3_states") == "OFFLINING"
        and not boolish(details.get("lower_mhi_present"))
        and not boolish(details.get("lower_service69_progress"))
        and not boolish(details.get("lower_wlan0_present"))
        and details.get("wlfw_service69_seen") == "0"
        and details.get("wlan0_present") == "0"
    )


def classify(details: dict[str, Any]) -> tuple[str, str]:
    if not bool(details.get("source_pass")):
        return "source-v1834-not-pass", "V1834 source manifest was not PASS"
    if not bool(details.get("rollback_ok")):
        return "source-v1834-rollback-missing", "V1834 did not verify rollback to v724"
    if not boolish(details.get("safety_ok")):
        return "source-v1834-safety-regression", "V1834 safety gate was not clean"
    if not bound_poll_timeout_shape(details):
        return "qipcrtr-bound-poll-shape-incomplete", "V1834 bound QIPCRTR poll/recv timeout shape was incomplete"
    if boolish(details.get("raw_service74_text_positive")) or boolish(details.get("raw_wlan_pd_text_positive")):
        return "lower-publication-progress", "service74 or wlan_pd publication text appeared"
    if intish(details["qrtr_case_0"].get("readback.service_events")) > 0 or intish(details["qrtr_case_1"].get("readback.service_events")) > 0:
        return "wlfw-service69-progress", "QRTR readback saw WLFW service 69"
    if intish(details["service_notifier_early"].get("indication_seen")) > 0 or intish(details["service_notifier_late"].get("indication_seen")) > 0:
        return "wlan-pd-servnotif-indication-progress", "service-notifier emitted a wlan_pd state indication"
    if not inherited_qrtr_qmi_shape(details):
        return "inherited-qrtr-qmi-shape-incomplete", "inherited WLFW readback, service-locator, or service-notifier shape was incomplete"
    if not lower_still_blocked(details):
        return "lower-blocker-shape-incomplete", "lower publication state did not match the expected wlan_pd-uninit blocker"
    return (
        "qipcrtr-mechanics-cleared-wlan-pd-uninit-blocker",
        "Bound local QRTR port works but ambient poll times out; inherited WLFW readback is empty, service-locator resolves msm/modem/wlan_pd instance 180, and service-notifier stays uninit/no-indication, so stop QRTR socket mechanics and target the WLAN-PD UNINIT transition prerequisite before Wi-Fi HAL/scan/connect",
    )


def render_qrtr_case(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` service/instance/status: `{data.get('service')}` / `{data.get('instance')}` / `{data.get('status')}`",
        f"- `{name}` qmi/send/new/del: `{data.get('qmi_attempted')}` / `{data.get('send_attempted')}` / `{data.get('new_lookup_send.rc')}` / `{data.get('del_lookup_send.rc')}`",
        f"- `{name}` events/service/empty/end/timeout: `{data.get('readback.events')}` / `{data.get('readback.service_events')}` / `{data.get('readback.empty_events')}` / `{data.get('readback.end_of_list')}` / `{data.get('readback.timeout')}`",
    ]


def render_listener(title: str, data: dict[str, str]) -> list[str]:
    return [
        f"- {title} allowed/qmi: `{data.get('allowed')}` / `{data.get('qmi_payload')}`",
        f"- {title} endpoint: `{data.get('endpoint.status')}` node `{data.get('endpoint.node')}` port `{data.get('endpoint.port')}`",
        f"- {title} response: success `{data.get('response_success')}`, state `{data.get('response_curr_state_name')}` (`{data.get('response_curr_state')}`)",
        f"- {title} indication/ack/result: `{data.get('indication_seen')}` / `{data.get('ack_sent')}` / `{data.get('result')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    servloc = d["servloc_domain"]
    late_probe = d["service_notifier_late_probe"]
    result_text = "PASS" if result["pass"] else "FAIL"
    return "\n".join(
        [
            "# Native Init V1835 QIPCRTR Route Pivot Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1835`",
            "- Type: host-only classifier over V1834 rollback-verified QIPCRTR bound poll/recv evidence",
            f"- Decision: `{result['decision']}`",
            f"- Result: {result_text}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            f"- Source evidence: `{d['source_dir']}`",
            "",
            "## Source Gates",
            "",
            f"- V1834 decision: `{d['source_decision']}`",
            f"- V1834 reason: {d['source_reason']}",
            f"- rollback ok: `{d['rollback_ok']}`",
            f"- safety ok: `{d['safety_ok']}`",
            f"- PM projection/list commit/init-fail: `{d['pm_service_devnode_projection_label']}` / `{d['pm_service_list_commit_hits']}` / `{d['pm_service_init_fail_hits']}`",
            f"- PM names/devnodes: `{d['pm_service_entry_names']}` / `{d['pm_service_entry_devnodes']}`",
            f"- PM client register/connect/return rc: `{d['pm_client_register_rc']}` / `{d['pm_client_connect_rc']}` / `{d['pm_init_return_path_rc']}`",
            "",
            "## Bound QIPCRTR Observer",
            "",
            f"- label/mode: `{d['qipcrtr_bound_recv_label']}` / `{d['qipcrtr_bound_recv_mode']}`",
            f"- family/type: `{d['qipcrtr_bound_recv_family']}` / `{d['qipcrtr_bound_recv_type']}`",
            f"- open/bind/close rc: `{d['qipcrtr_bound_recv_open_rc']}` / `{d['qipcrtr_bound_recv_bind_rc']}` / `{d['qipcrtr_bound_recv_close_rc']}`",
            f"- before-bind node/port: `{d['qipcrtr_bound_recv_before_node']}` / `{d['qipcrtr_bound_recv_before_port']}`",
            f"- bind request family/node/port: `{d['qipcrtr_bound_recv_request_family']}` / `{d['qipcrtr_bound_recv_request_node']}` / `{d['qipcrtr_bound_recv_request_port']}`",
            f"- after-bind family/node/port: `{d['qipcrtr_bound_recv_after_family']}` / `{d['qipcrtr_bound_recv_after_node']}` / `{d['qipcrtr_bound_recv_after_port']}`",
            f"- poll timeout-ms/set-nonblock/rc/timeout/revents: `{d['qipcrtr_bound_recv_poll_timeout_ms']}` / `{d['qipcrtr_bound_recv_set_nonblock_rc']}` / `{d['qipcrtr_bound_recv_poll_rc']}` / `{d['qipcrtr_bound_recv_poll_timeout']}` / `{d['qipcrtr_bound_recv_poll_revents']}`",
            f"- recv rc/skipped/reason: `{d['qipcrtr_bound_recv_recv_rc']}` / `{d['qipcrtr_bound_recv_recv_skipped']}` / `{d['qipcrtr_bound_recv_recv_skip_reason']}`",
            f"- socket counts before/before-poll/after-poll/after-close: `{d['qipcrtr_bound_recv_before_sockets']}` / `{d['qipcrtr_bound_recv_while_before_poll_sockets']}` / `{d['qipcrtr_bound_recv_while_after_poll_sockets']}` / `{d['qipcrtr_bound_recv_after_close_sockets']}`",
            f"- observer no connect/send/lookup/control/service-start: `{d['qipcrtr_bound_recv_no_connect']}` / `{d['qipcrtr_bound_recv_no_send']}` / `{d['qipcrtr_bound_recv_no_lookup_send']}` / `{d['qipcrtr_bound_recv_no_control_payload']}` / `{d['qipcrtr_bound_recv_no_service_start']}`",
            "",
            "## Inherited QRTR/QMI Probes",
            "",
            f"- WLFW readback label/matrix/qmi/result: `{d['qrtr_readback_label']}` / `{d['qrtr_readback_matrix']}` / `{d['qrtr_readback_qmi_payload']}` / `{d['qrtr_readback_result']}`",
            *render_qrtr_case("case_0", d["qrtr_case_0"]),
            *render_qrtr_case("case_1", d["qrtr_case_1"]),
            f"- service-locator label: `{d['servloc_domain_label']}`",
            f"- service-locator allowed/qmi/send/response/result: `{servloc.get('allowed')}` / `{servloc.get('qmi_payload')}` / `{servloc.get('send_attempted')}` / `{servloc.get('response_success')}` / `{servloc.get('result')}`",
            f"- service-locator endpoint: `{servloc.get('endpoint.status')}` node `{servloc.get('endpoint.node')}` port `{servloc.get('endpoint.port')}`",
            f"- service-locator domains: count `{servloc.get('domain_count')}`, wlan-like `{servloc.get('wlan_like_domains')}`, first `{servloc.get('domain.0.name')}` instance `{servloc.get('domain.0.instance_id')}`",
            f"- service-notifier label: `{d['servnotif_label']}`",
            *render_listener("early listener", d["service_notifier_early"]),
            f"- late probe allowed/qmi/endpoint/result: `{late_probe.get('allowed')}` / `{late_probe.get('qmi_payload')}` / `{late_probe.get('endpoint.status')}` node `{late_probe.get('endpoint.node')}` port `{late_probe.get('endpoint.port')}` / `{late_probe.get('result')}`",
            *render_listener("late listener", d["service_notifier_late"]),
            "",
            "## Lower Publication State",
            "",
            f"- lower state/service74 label: `{d['post_pm_lower_state_label']}` / `{d['service74_raw_klog_label']}`",
            f"- raw service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{d['raw_service_locator_counts']}` / `{d['raw_servloc_domain_counts']}` / `{d['raw_wlan_fw_counts']}` / `{d['raw_wlan_pd_domain_counts']}` / `{d['raw_qmi_server_connected_counts']}`",
            f"- raw service180/service74/wlan_pd/WLFW counts: `{d['raw_service180_text_counts']}` / `{d['raw_service74_text_counts']}` / `{d['raw_wlan_pd_text_counts']}` / `{d['raw_wlfw_counts']}`",
            f"- service-notifier early/late state: `{d['service_notifier_early_state']}` / `{d['service_notifier_late_state']}`",
            f"- mdm3/MHI/WLFW69/wlan0: `{d['lower_mdm3_states']}` / `{d['lower_mhi_present']}` / `{d['lower_service69_progress']}` / `{d['lower_wlan0_present']}`",
            f"- requested wlanmdsp / service69 seen / wlan0 present: `{d['requested_wlanmdsp']}` / `{d['wlfw_service69_seen']}` / `{d['wlan0_present']}`",
            "",
            "## Interpretation",
            "",
            "- The new V1834 bound observer socket allocates a local QRTR port and then times out on passive poll without inbound ambient data.",
            "- QRTR socket mechanics are no longer the highest-value next target: local bind, nonzero local port, nonblocking poll, and clean close are all proven.",
            "- The inherited route shows QRTR lookup/control and QMI service-locator/notifier surfaces are reachable, but WLFW service 69 remains absent and wlan_pd service-notifier stays `uninit` early and late.",
            "- The next unit should stay below Wi-Fi HAL/scan/connect and classify the safe prerequisite that can move service-notifier out of `uninit` or cause WLFW service 69 publication.",
            "",
            "## Safety Scope",
            "",
            "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
            "",
            "The new V1834 bound observer socket had no connect/send/QRTR lookup/control/service-start. The inherited V1834 route did run bounded QRTR NEW_LOOKUP/DEL_LOOKUP readback without QMI payload, service-locator domain-list QMI, and service-notifier register/listener QMI; no WLFW request payload was sent.",
            "",
        ]
    )


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source = load_json(source_manifest_path)
    fields = prev1796.runner.fwbase.parse_helper_fields(SOURCE_DIR)
    details = collect_details(source, fields)
    label, reason = classify(details)
    passed = label == "qipcrtr-mechanics-cleared-wlan-pd-uninit-blocker"
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1835-{label}-host-{status}",
        "pass": passed,
        "reason": reason,
        "source_manifest": rel(source_manifest_path),
        "out_dir": rel(OUT_DIR),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(result)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": passed, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
