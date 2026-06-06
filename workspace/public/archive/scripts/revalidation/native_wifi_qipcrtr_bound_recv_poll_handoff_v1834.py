#!/usr/bin/env python3
"""V1834 one-run QIPCRTR bound poll/recv handoff."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import native_wifi_qipcrtr_local_node_bind_handoff_v1831 as prev1831


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1834"
V1833_OUT = REPO_ROOT / "tmp" / "wifi" / "v1833-qipcrtr-bound-recv-poll-test-boot"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1833/dev/__properties__"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1834-qipcrtr-bound-recv-poll-handoff"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1834_QIPCRTR_BOUND_RECV_POLL_HANDOFF_2026-06-03.md"
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.161 (v1833-qipcrtr-bound-recv-poll)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1833.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1833.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1833-helper.result"
DMESG_PATTERN = (
    "A90v1833|wlan_pd_qipcrtr_bound_recv_poll_state|"
    "wlan_pd_qipcrtr_local_node_bind_state|wlan_pd_qipcrtr_autobind_state|"
    "wlan_pd_qipcrtr_socket_state|QIPCRTR|AF_QIPCRTR|"
    "wlan_pd_qrtr_registry|wlan_pd_post_pm_lower_handoff_klog|"
    "raw_count_|last_|service_locator|service-locator|servloc|domain|"
    "wlan/fw|wlan_fw|qmi-server|qmi_server_connected|pd-mapper|"
    "pd_mapper|subsys|subsystem|pil|q6v5|qmi|QMI|wlfw|WLFW|"
    "service_notifier|service-notifier|service 180|service 74|"
    "wlan_pd|qrtr|service 69|FW ready|BDF|wlan0|cnss-daemon|"
    "4080000.qcom,mss|soc:qcom,mdm3"
)

BOUND_PREFIX = "wlan_pd_qipcrtr_bound_recv_poll_state.net_window"
BOUND_PROTOCOL_PHASES = (
    "before_open",
    "while_bound_before_poll",
    "while_bound_after_poll",
    "after_close",
)
BOUND_PROTOCOL_FIELDS = (
    "protocols_open",
    "protocols_error",
    "qipcrtr_present",
    "qipcrtr_line",
    "qipcrtr_size",
    "qipcrtr_sockets",
)


def configure_runner() -> None:
    prev1828 = prev1831.prev1828
    prev1825 = prev1828.prev1825
    prev1822 = prev1825.prev1822
    prev1819 = prev1822.prev1819
    prev1819.CYCLE = CYCLE
    prev1819.V1818_OUT = V1833_OUT
    prev1819.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1819.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    prev1819.DEFAULT_REPORT_PATH = DEFAULT_REPORT_PATH
    prev1819.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1819.TEST_LOG_PATH = TEST_LOG_PATH
    prev1819.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1819.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1819.DMESG_PATTERN = DMESG_PATTERN
    prev1819.configure_runner()
    runner = prev1819.prev1816.prev1796.runner
    runner.DEFAULT_SOURCE_MANIFEST = V1833_OUT / "manifest.json"
    runner.DEFAULT_TEST_IMAGE = V1833_OUT / "boot_linux_v1833_qipcrtr_bound_recv_poll.img"
    runner.LOCAL_PROPERTY_ROOT = V1833_OUT / "property-runtime" / "layout" / "dev" / "__properties__"


def intish(value: object) -> int:
    return prev1831.intish(value)


def bound_protocol_sample(fields: dict[str, str], phase: str) -> dict[str, str]:
    prefix = f"{BOUND_PREFIX}.{phase}."
    return {
        "phase": phase,
        **{key: fields.get(prefix + key, "") for key in BOUND_PROTOCOL_FIELDS},
    }


def collect_gate_fields(fields: dict[str, str]) -> dict[str, Any]:
    details = prev1831.collect_gate_fields(fields)
    protocol_samples = [
        bound_protocol_sample(fields, phase)
        for phase in BOUND_PROTOCOL_PHASES
    ]
    details.update(
        {
            "qipcrtr_bound_recv_protocol_samples": protocol_samples,
            "qipcrtr_bound_recv_begin": fields.get(f"{BOUND_PREFIX}.begin", ""),
            "qipcrtr_bound_recv_end": fields.get(f"{BOUND_PREFIX}.end", ""),
            "qipcrtr_bound_recv_mode": fields.get(f"{BOUND_PREFIX}.mode", ""),
            "qipcrtr_bound_recv_family": fields.get(f"{BOUND_PREFIX}.family", ""),
            "qipcrtr_bound_recv_type": fields.get(f"{BOUND_PREFIX}.type", ""),
            "qipcrtr_bound_recv_bind_attempted": fields.get(f"{BOUND_PREFIX}.bind_attempted", ""),
            "qipcrtr_bound_recv_observed_local_node": fields.get(f"{BOUND_PREFIX}.bind_observed_local_node", ""),
            "qipcrtr_bound_recv_open_rc": fields.get(f"{BOUND_PREFIX}.open.rc", ""),
            "qipcrtr_bound_recv_open_errno": fields.get(f"{BOUND_PREFIX}.open.errno", ""),
            "qipcrtr_bound_recv_open_error": fields.get(f"{BOUND_PREFIX}.open.error", ""),
            "qipcrtr_bound_recv_before_rc": fields.get(f"{BOUND_PREFIX}.getsockname_before_bind.rc", ""),
            "qipcrtr_bound_recv_before_node": fields.get(f"{BOUND_PREFIX}.getsockname_before_bind.node", ""),
            "qipcrtr_bound_recv_before_port": fields.get(f"{BOUND_PREFIX}.getsockname_before_bind.port", ""),
            "qipcrtr_bound_recv_request_family": fields.get(f"{BOUND_PREFIX}.bind.request.family", ""),
            "qipcrtr_bound_recv_request_node": fields.get(f"{BOUND_PREFIX}.bind.request.node", ""),
            "qipcrtr_bound_recv_request_port": fields.get(f"{BOUND_PREFIX}.bind.request.port", ""),
            "qipcrtr_bound_recv_bind_rc": fields.get(f"{BOUND_PREFIX}.bind.rc", ""),
            "qipcrtr_bound_recv_bind_errno": fields.get(f"{BOUND_PREFIX}.bind.errno", ""),
            "qipcrtr_bound_recv_bind_error": fields.get(f"{BOUND_PREFIX}.bind.error", ""),
            "qipcrtr_bound_recv_bind_skipped": fields.get(f"{BOUND_PREFIX}.bind.skipped", ""),
            "qipcrtr_bound_recv_bind_skip_reason": fields.get(f"{BOUND_PREFIX}.bind.skip_reason", ""),
            "qipcrtr_bound_recv_after_rc": fields.get(f"{BOUND_PREFIX}.getsockname_after_bind.rc", ""),
            "qipcrtr_bound_recv_after_family": fields.get(f"{BOUND_PREFIX}.getsockname_after_bind.family", ""),
            "qipcrtr_bound_recv_after_node": fields.get(f"{BOUND_PREFIX}.getsockname_after_bind.node", ""),
            "qipcrtr_bound_recv_after_port": fields.get(f"{BOUND_PREFIX}.getsockname_after_bind.port", ""),
            "qipcrtr_bound_recv_poll_attempted": fields.get(f"{BOUND_PREFIX}.poll_recv.attempted", ""),
            "qipcrtr_bound_recv_poll_skipped": fields.get(f"{BOUND_PREFIX}.poll_recv.skipped", ""),
            "qipcrtr_bound_recv_poll_skip_reason": fields.get(f"{BOUND_PREFIX}.poll_recv.skip_reason", ""),
            "qipcrtr_bound_recv_poll_timeout_ms": fields.get(f"{BOUND_PREFIX}.poll_recv.timeout_ms", ""),
            "qipcrtr_bound_recv_poll_max_bytes": fields.get(f"{BOUND_PREFIX}.poll_recv.max_recv_bytes", ""),
            "qipcrtr_bound_recv_set_nonblock_rc": fields.get(f"{BOUND_PREFIX}.poll_recv.set_nonblock.rc", ""),
            "qipcrtr_bound_recv_set_nonblock_errno": fields.get(f"{BOUND_PREFIX}.poll_recv.set_nonblock.errno", ""),
            "qipcrtr_bound_recv_set_nonblock_error": fields.get(f"{BOUND_PREFIX}.poll_recv.set_nonblock.error", ""),
            "qipcrtr_bound_recv_poll_rc": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.rc", ""),
            "qipcrtr_bound_recv_poll_timeout": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.timeout", ""),
            "qipcrtr_bound_recv_poll_revents": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.revents", ""),
            "qipcrtr_bound_recv_poll_errno": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.errno", ""),
            "qipcrtr_bound_recv_poll_error": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.error", ""),
            "qipcrtr_bound_recv_poll_inner_skipped": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.skipped", ""),
            "qipcrtr_bound_recv_poll_inner_skip_reason": fields.get(f"{BOUND_PREFIX}.poll_recv.poll.skip_reason", ""),
            "qipcrtr_bound_recv_recv_rc": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.rc", ""),
            "qipcrtr_bound_recv_recv_skipped": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.skipped", ""),
            "qipcrtr_bound_recv_recv_skip_reason": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.skip_reason", ""),
            "qipcrtr_bound_recv_recv_errno": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.errno", ""),
            "qipcrtr_bound_recv_recv_error": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.error", ""),
            "qipcrtr_bound_recv_recv_bytes": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.bytes", ""),
            "qipcrtr_bound_recv_recv_from_len": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.from_len", ""),
            "qipcrtr_bound_recv_recv_from_family": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.from.family", ""),
            "qipcrtr_bound_recv_recv_from_node": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.from.node", ""),
            "qipcrtr_bound_recv_recv_from_port": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.from.port", ""),
            "qipcrtr_bound_recv_recv_first_u32": fields.get(f"{BOUND_PREFIX}.poll_recv.recv.first_u32_le", ""),
            "qipcrtr_bound_recv_close_rc": fields.get(f"{BOUND_PREFIX}.close.rc", ""),
            "qipcrtr_bound_recv_close_errno": fields.get(f"{BOUND_PREFIX}.close.errno", ""),
            "qipcrtr_bound_recv_close_error": fields.get(f"{BOUND_PREFIX}.close.error", ""),
            "qipcrtr_bound_recv_no_connect": fields.get(f"{BOUND_PREFIX}.no_connect", ""),
            "qipcrtr_bound_recv_no_send": fields.get(f"{BOUND_PREFIX}.no_send", ""),
            "qipcrtr_bound_recv_no_lookup_send": fields.get(f"{BOUND_PREFIX}.no_qrtr_lookup_send", ""),
            "qipcrtr_bound_recv_no_control_payload": fields.get(f"{BOUND_PREFIX}.no_qrtr_control_payload", ""),
            "qipcrtr_bound_recv_no_service_start": fields.get(f"{BOUND_PREFIX}.no_service_start", ""),
            "qipcrtr_bound_recv_before_sockets": intish(protocol_samples[0].get("qipcrtr_sockets")),
            "qipcrtr_bound_recv_while_before_poll_sockets": intish(protocol_samples[1].get("qipcrtr_sockets")),
            "qipcrtr_bound_recv_while_after_poll_sockets": intish(protocol_samples[2].get("qipcrtr_sockets")),
            "qipcrtr_bound_recv_after_close_sockets": intish(protocol_samples[3].get("qipcrtr_sockets")),
            "qrtr_readback_allowed": fields.get("wifi_companion_qrtr_readback.allowed", ""),
            "qrtr_readback_matrix": fields.get("wifi_companion_qrtr_readback.matrix", ""),
            "qrtr_readback_qmi_payload": fields.get("wifi_companion_qrtr_readback.qmi_payload", ""),
            "qrtr_readback_send_attempted": fields.get("wifi_companion_qrtr_readback.send_attempted", ""),
            "qrtr_readback_result": fields.get("wifi_companion_qrtr_readback.result", ""),
            "qrtr_readback_case0_service_events": fields.get("wifi_companion_qrtr_readback.case_0.readback.service_events", ""),
            "qrtr_readback_case0_empty_events": fields.get("wifi_companion_qrtr_readback.case_0.readback.empty_events", ""),
            "qrtr_readback_case0_end_of_list": fields.get("wifi_companion_qrtr_readback.case_0.readback.end_of_list", ""),
            "qrtr_readback_case0_timeout": fields.get("wifi_companion_qrtr_readback.case_0.readback.timeout", ""),
            "qrtr_readback_case1_service_events": fields.get("wifi_companion_qrtr_readback.case_1.readback.service_events", ""),
            "qrtr_readback_case1_empty_events": fields.get("wifi_companion_qrtr_readback.case_1.readback.empty_events", ""),
            "qrtr_readback_case1_end_of_list": fields.get("wifi_companion_qrtr_readback.case_1.readback.end_of_list", ""),
            "qrtr_readback_case1_timeout": fields.get("wifi_companion_qrtr_readback.case_1.readback.timeout", ""),
            "servloc_domain_allowed": fields.get("wifi_companion_servloc_domain_list.allowed", ""),
            "servloc_domain_qmi_payload": fields.get("wifi_companion_servloc_domain_list.qmi_payload", ""),
            "servloc_domain_endpoint_status": fields.get("wifi_companion_servloc_domain_list.endpoint.status", ""),
            "servloc_domain_endpoint_node": fields.get("wifi_companion_servloc_domain_list.endpoint.node", ""),
            "servloc_domain_endpoint_port": fields.get("wifi_companion_servloc_domain_list.endpoint.port", ""),
            "servloc_domain_response_success": fields.get("wifi_companion_servloc_domain_list.response_success", ""),
            "servloc_domain_result": fields.get("wifi_companion_servloc_domain_list.result", ""),
            "servloc_domain_count": fields.get("wifi_companion_servloc_domain_list.domain_count", ""),
            "servloc_domain0_name": fields.get("wifi_companion_servloc_domain_list.domain.0.name", ""),
            "servloc_domain0_instance_id": fields.get("wifi_companion_servloc_domain_list.domain.0.instance_id", ""),
            "servnotif_early_allowed": fields.get("wifi_companion_service_notifier_listener.allowed", ""),
            "servnotif_early_qmi_payload": fields.get("wifi_companion_service_notifier_listener.qmi_payload", ""),
            "servnotif_early_endpoint_status": fields.get("wifi_companion_service_notifier_listener.endpoint.status", ""),
            "servnotif_early_response_success": fields.get("wifi_companion_service_notifier_listener.response_success", ""),
            "servnotif_early_state": fields.get("wifi_companion_service_notifier_listener.response_curr_state_name", ""),
            "servnotif_early_indication_seen": fields.get("wifi_companion_service_notifier_listener.indication_seen", ""),
            "servnotif_early_result": fields.get("wifi_companion_service_notifier_listener.result", ""),
            "servnotif_late_probe_allowed": fields.get("wifi_companion_service_notifier_late_probe.allowed", ""),
            "servnotif_late_probe_qmi_payload": fields.get("wifi_companion_service_notifier_late_probe.qmi_payload", ""),
            "servnotif_late_probe_endpoint_status": fields.get("wifi_companion_service_notifier_late_probe.endpoint.status", ""),
            "servnotif_late_probe_result": fields.get("wifi_companion_service_notifier_late_probe.result", ""),
            "servnotif_late_listener_allowed": fields.get("wifi_companion_service_notifier_late_listener.allowed", ""),
            "servnotif_late_listener_qmi_payload": fields.get("wifi_companion_service_notifier_late_listener.qmi_payload", ""),
            "servnotif_late_listener_endpoint_status": fields.get("wifi_companion_service_notifier_late_listener.endpoint.status", ""),
            "servnotif_late_listener_response_success": fields.get("wifi_companion_service_notifier_late_listener.response_success", ""),
            "servnotif_late_listener_state": fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name", ""),
            "servnotif_late_listener_indication_seen": fields.get("wifi_companion_service_notifier_late_listener.indication_seen", ""),
            "servnotif_late_listener_result": fields.get("wifi_companion_service_notifier_late_listener.result", ""),
        }
    )
    non_actions_ok = all(
        fields.get(f"{BOUND_PREFIX}.{key}", "") == "1"
        for key in (
            "no_connect",
            "no_send",
            "no_qrtr_lookup_send",
            "no_qrtr_control_payload",
            "no_service_start",
        )
    )
    poll_seen = (
        details["qipcrtr_bound_recv_poll_attempted"] == "1"
        or details["qipcrtr_bound_recv_poll_skipped"] == "1"
    )
    details["qipcrtr_bound_recv_contract_ok"] = (
        details["qipcrtr_bound_recv_begin"] == "1"
        and details["qipcrtr_bound_recv_end"] == "1"
        and details["qipcrtr_bound_recv_mode"] == "observed-local-node-bind-poll-recv-close"
        and details["qipcrtr_bound_recv_bind_attempted"] == "1"
        and details["qipcrtr_bound_recv_observed_local_node"] == "1"
        and non_actions_ok
        and poll_seen
        and all(item.get("protocols_open") == "1" for item in protocol_samples)
        and all(item.get("qipcrtr_present") == "1" for item in protocol_samples)
    )
    details["qipcrtr_bound_recv_safety_ok"] = non_actions_ok
    details["qipcrtr_bound_recv_opened"] = details["qipcrtr_bound_recv_open_rc"] == "0"
    details["qipcrtr_bound_recv_bound"] = details["qipcrtr_bound_recv_bind_rc"] == "0"
    details["qipcrtr_bound_recv_after_ok"] = details["qipcrtr_bound_recv_after_rc"] == "0"
    details["qipcrtr_bound_recv_port_nonzero"] = intish(details.get("qipcrtr_bound_recv_after_port")) > 0
    details["qipcrtr_bound_recv_poll_timed_out"] = (
        details["qipcrtr_bound_recv_poll_rc"] == "0"
        and details["qipcrtr_bound_recv_poll_timeout"] == "1"
        and details["qipcrtr_bound_recv_recv_skipped"] == "1"
        and details["qipcrtr_bound_recv_recv_skip_reason"] == "poll-timeout"
    )
    details["qipcrtr_bound_recv_no_pollin"] = (
        details["qipcrtr_bound_recv_poll_rc"] not in {"", "0", "-1"}
        and details["qipcrtr_bound_recv_recv_skipped"] == "1"
        and details["qipcrtr_bound_recv_recv_skip_reason"] == "no-pollin"
    )
    details["qipcrtr_bound_recv_packet_received"] = (
        details["qipcrtr_bound_recv_recv_rc"] == "0"
        and intish(details.get("qipcrtr_bound_recv_recv_bytes")) >= 0
    )
    details["qipcrtr_bound_recv_error"] = (
        details["qipcrtr_bound_recv_set_nonblock_rc"] == "-1"
        or details["qipcrtr_bound_recv_poll_rc"] == "-1"
        or details["qipcrtr_bound_recv_recv_rc"] == "-1"
    )
    details["qipcrtr_bound_recv_closed"] = details["qipcrtr_bound_recv_close_rc"] == "0"
    details["qrtr_readback_label"] = (
        "wlfw-readback-empty"
        if (
            details["qrtr_readback_allowed"] == "1"
            and details["qrtr_readback_send_attempted"] == "1"
            and details["qrtr_readback_result"] == "complete"
            and details["qrtr_readback_qmi_payload"] == "0"
            and details["qrtr_readback_case0_service_events"] == "0"
            and details["qrtr_readback_case0_empty_events"] == "1"
            and details["qrtr_readback_case0_end_of_list"] == "1"
            and details["qrtr_readback_case0_timeout"] == "0"
            and details["qrtr_readback_case1_service_events"] == "0"
            and details["qrtr_readback_case1_empty_events"] == "1"
            and details["qrtr_readback_case1_end_of_list"] == "1"
            and details["qrtr_readback_case1_timeout"] == "0"
        )
        else "wlfw-readback-review"
    )
    details["servloc_domain_label"] = (
        "servloc-domain-wlan-pd-instance180"
        if (
            details["servloc_domain_allowed"] == "1"
            and details["servloc_domain_qmi_payload"] == "1"
            and details["servloc_domain_response_success"] == "1"
            and details["servloc_domain_result"] == "domain-list-response-success"
            and details["servloc_domain0_name"] == "msm/modem/wlan_pd"
            and details["servloc_domain0_instance_id"] == "180"
        )
        else "servloc-domain-review"
    )
    details["servnotif_label"] = (
        "service-notifier-uninit"
        if (
            details["servnotif_early_allowed"] == "1"
            and details["servnotif_early_qmi_payload"] == "1"
            and details["servnotif_early_response_success"] == "1"
            and details["servnotif_early_state"] == "uninit"
            and details["servnotif_late_listener_allowed"] == "1"
            and details["servnotif_late_listener_qmi_payload"] == "1"
            and details["servnotif_late_listener_response_success"] == "1"
            and details["servnotif_late_listener_state"] == "uninit"
        )
        else "service-notifier-review"
    )
    return details


def actual_publication_progress(details: dict[str, Any]) -> bool:
    return prev1831.actual_publication_progress(details)


def classify_gate(args: Any,
                  test_flash: dict[str, Any],
                  rollback_result: dict[str, Any],
                  evidence_dir: Path) -> tuple[str, bool, str, dict[str, Any]]:
    runner = prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.runner
    test_version = runner.fwbase.read_text(evidence_dir, "test-version.stdout.txt")
    helper_fields = runner.fwbase.parse_helper_fields(evidence_dir)
    details = collect_gate_fields(helper_fields)
    version_ok = args.expect_test_version in test_version
    rollback_ok = bool(rollback_result.get("ok"))
    helper_contract_seen = prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.field_bool(
        helper_fields,
        "wlan_pd_service_object_visible_trigger.begin",
    )
    safety_ok = (
        prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.safety_ok(helper_fields)
        and bool(details.get("devnode_safety_ok"))
        and bool(details.get("lower_safety_ok"))
        and bool(details.get("klog_safety_ok"))
        and bool(details.get("qrtr_registry_safety_ok"))
        and bool(details.get("qipcrtr_socket_safety_ok"))
        and bool(details.get("qipcrtr_autobind_safety_ok"))
        and bool(details.get("qipcrtr_local_bind_safety_ok"))
        and bool(details.get("qipcrtr_bound_recv_safety_ok"))
    )
    details.update(
        {
            "version_ok": version_ok,
            "rollback_ok": rollback_ok,
            "helper_contract_seen": helper_contract_seen,
            "safety_ok": safety_ok,
        }
    )

    if not test_flash.get("ok"):
        return f"{args.cycle.lower()}-test-boot-flash-or-verify-failed", False, "test boot flash/verify failed", details
    if not version_ok:
        return f"{args.cycle.lower()}-test-boot-version-missing", False, "expected V1833 test boot version was not collected", details
    if not rollback_ok:
        return f"{args.cycle.lower()}-rollback-failed", False, "rollback to v724 did not verify", details
    if (
        not helper_contract_seen
        or not details.get("lower_contract_ok")
        or not details.get("klog_contract_ok")
        or not details.get("qrtr_registry_contract_ok")
        or not details.get("qipcrtr_socket_contract_ok")
        or not details.get("qipcrtr_autobind_contract_ok")
        or not details.get("qipcrtr_local_bind_contract_ok")
        or not details.get("qipcrtr_bound_recv_contract_ok")
    ):
        return f"{args.cycle.lower()}-observer-contract-missing", False, "helper result missed lower, registry, socket, bind, or bound poll/recv observer fields", details
    if not safety_ok:
        details["qipcrtr_bound_recv_label"] = "safety-regression"
        return f"{args.cycle.lower()}-safety-regression", False, "one or more hard-stop safety fields regressed", details

    if actual_publication_progress(details):
        label = "lower-publication-progress"
        reason = "service 74, wlan_pd, service-notifier state, WLFW service 69, MHI, or wlan0 progressed"
    elif not bool(details.get("qipcrtr_bound_recv_opened")):
        label = "qipcrtr-bound-recv-poll-open-fails"
        reason = "AF_QIPCRTR protocol is listed, but passive socket open failed"
    elif details.get("qipcrtr_bound_recv_bind_skipped") == "1":
        label = "qipcrtr-bound-recv-poll-bind-skipped"
        reason = f"observed local node was not usable for bind: {details.get('qipcrtr_bound_recv_bind_skip_reason')}"
    elif not bool(details.get("qipcrtr_bound_recv_bound")):
        label = "qipcrtr-bound-recv-poll-bind-fails"
        reason = "AF_QIPCRTR opened, but observed-local-node bind failed"
    elif not bool(details.get("qipcrtr_bound_recv_after_ok")) or not bool(details.get("qipcrtr_bound_recv_port_nonzero")):
        label = "qipcrtr-bound-recv-poll-port-missing"
        reason = "observed-local-node bind did not return a nonzero local port before poll"
    elif bool(details.get("qipcrtr_bound_recv_error")):
        label = "qipcrtr-bound-recv-poll-error"
        reason = "bound QIPCRTR socket hit set_nonblock, poll, or recvfrom error"
    elif bool(details.get("qipcrtr_bound_recv_packet_received")):
        label = "qipcrtr-bound-recv-poll-packet-passive"
        reason = "one inbound datagram arrived on the bound local QRTR port without connect/send/lookup/control traffic"
    elif (
        bool(details.get("qipcrtr_bound_recv_poll_timed_out"))
        and bool(details.get("qipcrtr_bound_recv_closed"))
        and not bool(details.get("raw_wlan_pd_text_positive"))
        and not bool(details.get("raw_service74_text_positive"))
    ):
        label = "qipcrtr-bound-recv-poll-timeout-passive"
        reason = "bound local QRTR port saw no inbound datagram during the 250 ms poll window and service74/wlan_pd stayed absent"
    elif bool(details.get("qipcrtr_bound_recv_no_pollin")):
        label = "qipcrtr-bound-recv-poll-no-pollin-passive"
        reason = "poll returned without POLLIN on the bound local QRTR port"
    else:
        label = "qipcrtr-bound-recv-poll-state-incomplete"
        reason = "bound poll/recv fields were present but did not match a fixed timeout, packet, or error discriminator"

    if prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.lower_progress(details):
        details["post_pm_lower_state_label"] = "lower-progress"
    elif prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1814.prev1811.prev1808.stable_offlining(details):
        details["post_pm_lower_state_label"] = "stable-mdm3-offlining"
    else:
        details["post_pm_lower_state_label"] = "lower-state-incomplete"
    if not bool(details.get("pm_client_return_fetchargs_seen")):
        details["pm_client_return_label"] = "pm-client-return-fetchargs-missing"
    elif bool(details.get("pm_client_return_nonzero")):
        details["pm_client_return_label"] = "pm-client-return-error"
    else:
        details["pm_client_return_label"] = "pm-client-return-success"
    if actual_publication_progress(details):
        details["service74_raw_klog_label"] = "service74-progress"
    elif bool(details.get("raw_service74_text_positive")) and not bool(details.get("klog_service74_positive")):
        details["service74_raw_klog_label"] = "service74-parser-miss"
    elif bool(details.get("klog_service180_positive")) and not bool(details.get("raw_service74_text_positive")):
        details["service74_raw_klog_label"] = "service74-raw-absent"
    else:
        details["service74_raw_klog_label"] = "service74-raw-klog-incomplete"
    details["qipcrtr_bound_recv_label"] = label
    return f"{args.cycle.lower()}-{label}-rollback-pass", True, reason, details


def render_bound_protocol_samples(samples: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for item in samples:
        lines.append(
            f"- `{item.get('phase')}` qipcrtr present/size/sockets: `{item.get('qipcrtr_present')}` / `{item.get('qipcrtr_size')}` / `{item.get('qipcrtr_sockets')}`"
        )
    return lines


def render_report(result: dict[str, Any]) -> str:
    gate = result.get("gate", {})
    property_deploy = result.get("property_deploy", {})
    lines = [
        "# Native Init V1834 QIPCRTR Bound Poll/Recv Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1834`",
        "- Type: one-run rollbackable QIPCRTR bound socket poll/recv discriminator",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Rollback attempt: `{result.get('rollback', {}).get('attempt')}`",
        f"- Rollback ok: `{result.get('rollback', {}).get('ok')}`",
        "",
        "## Gate Label",
        "",
        f"- QIPCRTR bound poll/recv label: `{gate.get('qipcrtr_bound_recv_label')}`",
        f"- WLFW QRTR readback label: `{gate.get('qrtr_readback_label')}`",
        f"- service-locator domain label: `{gate.get('servloc_domain_label')}`",
        f"- service-notifier label: `{gate.get('servnotif_label')}`",
        f"- service74 raw label: `{gate.get('service74_raw_klog_label')}`",
        f"- PM-client return label: `{gate.get('pm_client_return_label')}`",
        f"- lower-state label: `{gate.get('post_pm_lower_state_label')}`",
        f"- safety ok: `{gate.get('safety_ok')}`",
        "",
        "## Bound Poll/Recv State",
        "",
        f"- mode/family/type: `{gate.get('qipcrtr_bound_recv_mode')}` / `{gate.get('qipcrtr_bound_recv_family')}` / `{gate.get('qipcrtr_bound_recv_type')}`",
        f"- open/bind/close rc: `{gate.get('qipcrtr_bound_recv_open_rc')}` / `{gate.get('qipcrtr_bound_recv_bind_rc')}` / `{gate.get('qipcrtr_bound_recv_close_rc')}`",
        f"- before-bind getsockname rc/node/port: `{gate.get('qipcrtr_bound_recv_before_rc')}` / `{gate.get('qipcrtr_bound_recv_before_node')}` / `{gate.get('qipcrtr_bound_recv_before_port')}`",
        f"- bind request family/node/port: `{gate.get('qipcrtr_bound_recv_request_family')}` / `{gate.get('qipcrtr_bound_recv_request_node')}` / `{gate.get('qipcrtr_bound_recv_request_port')}`",
        f"- after-bind getsockname rc/family/node/port: `{gate.get('qipcrtr_bound_recv_after_rc')}` / `{gate.get('qipcrtr_bound_recv_after_family')}` / `{gate.get('qipcrtr_bound_recv_after_node')}` / `{gate.get('qipcrtr_bound_recv_after_port')}`",
        f"- bind skipped/reason: `{gate.get('qipcrtr_bound_recv_bind_skipped')}` / `{gate.get('qipcrtr_bound_recv_bind_skip_reason')}`",
        f"- poll attempted/skipped/reason: `{gate.get('qipcrtr_bound_recv_poll_attempted')}` / `{gate.get('qipcrtr_bound_recv_poll_skipped')}` / `{gate.get('qipcrtr_bound_recv_poll_skip_reason')}`",
        f"- poll timeout-ms/set-nonblock/poll rc/timeout/revents: `{gate.get('qipcrtr_bound_recv_poll_timeout_ms')}` / `{gate.get('qipcrtr_bound_recv_set_nonblock_rc')}` / `{gate.get('qipcrtr_bound_recv_poll_rc')}` / `{gate.get('qipcrtr_bound_recv_poll_timeout')}` / `{gate.get('qipcrtr_bound_recv_poll_revents')}`",
        f"- recv rc/skipped/reason/bytes: `{gate.get('qipcrtr_bound_recv_recv_rc')}` / `{gate.get('qipcrtr_bound_recv_recv_skipped')}` / `{gate.get('qipcrtr_bound_recv_recv_skip_reason')}` / `{gate.get('qipcrtr_bound_recv_recv_bytes')}`",
        f"- recv from family/node/port/first-u32: `{gate.get('qipcrtr_bound_recv_recv_from_family')}` / `{gate.get('qipcrtr_bound_recv_recv_from_node')}` / `{gate.get('qipcrtr_bound_recv_recv_from_port')}` / `{gate.get('qipcrtr_bound_recv_recv_first_u32')}`",
        f"- socket counts before/before-poll/after-poll/after-close: `{gate.get('qipcrtr_bound_recv_before_sockets')}` / `{gate.get('qipcrtr_bound_recv_while_before_poll_sockets')}` / `{gate.get('qipcrtr_bound_recv_while_after_poll_sockets')}` / `{gate.get('qipcrtr_bound_recv_after_close_sockets')}`",
        f"- no connect/send/lookup/control/service-start: `{gate.get('qipcrtr_bound_recv_no_connect')}` / `{gate.get('qipcrtr_bound_recv_no_send')}` / `{gate.get('qipcrtr_bound_recv_no_lookup_send')}` / `{gate.get('qipcrtr_bound_recv_no_control_payload')}` / `{gate.get('qipcrtr_bound_recv_no_service_start')}`",
        *render_bound_protocol_samples(gate.get("qipcrtr_bound_recv_protocol_samples", [])),
        "",
        "## Inherited QRTR/QMI Probes",
        "",
        f"- WLFW readback allowed/matrix/qmi-payload/result: `{gate.get('qrtr_readback_allowed')}` / `{gate.get('qrtr_readback_matrix')}` / `{gate.get('qrtr_readback_qmi_payload')}` / `{gate.get('qrtr_readback_result')}`",
        f"- WLFW case0 service/empty/end/timeout events: `{gate.get('qrtr_readback_case0_service_events')}` / `{gate.get('qrtr_readback_case0_empty_events')}` / `{gate.get('qrtr_readback_case0_end_of_list')}` / `{gate.get('qrtr_readback_case0_timeout')}`",
        f"- WLFW case1 service/empty/end/timeout events: `{gate.get('qrtr_readback_case1_service_events')}` / `{gate.get('qrtr_readback_case1_empty_events')}` / `{gate.get('qrtr_readback_case1_end_of_list')}` / `{gate.get('qrtr_readback_case1_timeout')}`",
        f"- service-locator endpoint/status/result: `{gate.get('servloc_domain_endpoint_node')}`:`{gate.get('servloc_domain_endpoint_port')}` / `{gate.get('servloc_domain_endpoint_status')}` / `{gate.get('servloc_domain_result')}`",
        f"- service-locator domain/name/instance: `{gate.get('servloc_domain_count')}` / `{gate.get('servloc_domain0_name')}` / `{gate.get('servloc_domain0_instance_id')}`",
        f"- service-notifier early qmi/state/indication/result: `{gate.get('servnotif_early_qmi_payload')}` / `{gate.get('servnotif_early_state')}` / `{gate.get('servnotif_early_indication_seen')}` / `{gate.get('servnotif_early_result')}`",
        f"- service-notifier late qmi/state/indication/result: `{gate.get('servnotif_late_listener_qmi_payload')}` / `{gate.get('servnotif_late_listener_state')}` / `{gate.get('servnotif_late_listener_indication_seen')}` / `{gate.get('servnotif_late_listener_result')}`",
        "",
        "## Registry And Publication State",
        "",
        f"- registry readable: `{gate.get('qrtr_registry_readable')}`",
        f"- proc_net_qrtr open counts: `{gate.get('qrtr_registry_proc_net_qrtr_open_counts')}`",
        f"- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{gate.get('raw_service_locator_counts')}` / `{gate.get('raw_servloc_domain_counts')}` / `{gate.get('raw_wlan_fw_counts')}` / `{gate.get('raw_wlan_pd_domain_counts')}` / `{gate.get('raw_qmi_server_connected_counts')}`",
        f"- service180/service74/wlan_pd raw: `{gate.get('raw_service180_text_counts')}` / `{gate.get('raw_service74_text_counts')}` / `{gate.get('raw_wlan_pd_text_counts')}`",
        f"- precondition pd-mapper/subsys/pil/qmi/wlfw: `{gate.get('raw_pd_mapper_counts')}` / `{gate.get('raw_subsys_counts')}` / `{gate.get('raw_pil_counts')}` / `{gate.get('raw_qmi_counts')}` / `{gate.get('raw_wlfw_counts')}`",
        "",
        "## Lower State",
        "",
        f"- early/late service-notifier state: `{gate.get('service_notifier_early_state')}` / `{gate.get('service_notifier_late_state')}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{gate.get('lower_mdm3_states')}` / `{gate.get('lower_mhi_present')}` / `{gate.get('lower_service69_progress')}` / `{gate.get('lower_wlan0_present')}`",
        f"- PM-client register/connect/return-path rc: `{gate.get('pm_client_register_rc')}` / `{gate.get('pm_client_connect_rc')}` / `{gate.get('pm_init_return_path_rc')}`",
        "",
        "## Property Runtime",
        "",
        f"- Remote root: `{property_deploy.get('remote_property_root')}`",
        f"- Transport: `{property_deploy.get('transport')}`",
        f"- Uploaded files/bytes: `{property_deploy.get('file_count')}` / `{property_deploy.get('bytes')}`",
        f"- property_info SHA verified: `{property_deploy.get('property_info_sha_ok')}`",
        f"- vendor_default_prop SHA verified: `{property_deploy.get('vendor_default_sha_ok')}`",
        "",
        "## Safety Scope",
        "",
        "- The new V1834 observer opened one AF_QIPCRTR datagram socket, bound it with the observed local node and port `0`, set `O_NONBLOCK`, ran one 250 ms `poll(POLLIN)`, called `recvfrom` only if `POLLIN` was set, and closed it without connect or send on that socket.",
        "- The inherited service-object route also ran bounded QRTR/QMI probes: WLFW `NEW_LOOKUP`/`DEL_LOOKUP` readback with `qmi_payload=0`, service-locator domain-list QMI, and service-notifier register/listener QMI.",
        "- No WLFW request payload, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- The route did not open `/dev/subsys_esoc0`, did not fake ONLINE, and did not write PMIC/GPIO/GDSC controls.",
        "- `boot_wlan`, restart-PD request, forced RC1, eSoC notify, BOOT_DONE spoof, PCI rescan, and platform bind/unbind were not used.",
        "- Mutation scope is private property runtime staging on `/mnt/sdext`, one test boot flash, and rollback to `stage3/boot_linux_v724.img`.",
        "",
        "## Next",
        "",
        "- Classify the combined V1834 state before any next live action: bound-poll timeout, WLFW readback empty, service-locator `msm/modem/wlan_pd` instance `180`, and service-notifier state `uninit`.",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_runner()
    runner = prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.runner
    runner.deploy_property_root = prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.deploy_property_root_serial
    runner.classify_gate = classify_gate
    runner.render_report = render_report
    rc = runner.main(argv)
    prev1831.prev1828.prev1825.prev1822.prev1819.prev1816.prev1796.sanitize_evidence_dir(DEFAULT_OUT_DIR)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
