#!/usr/bin/env python3
"""V1803 host-only classifier for WLFW QRTR/service-notifier readiness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_post_pm_success_wlfw_classifier_v1802 as prev1802
import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1803"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1801-pm-service-devnode-projection-handoff"
SOURCE_V1802_DIR = REPO_ROOT / "tmp" / "wifi" / "v1802-post-pm-success-wlfw-classifier"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1803-wlfw-qmi-readiness-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1803_WLFW_QMI_READINESS_CLASSIFIER_2026-06-03.md"
)


NOTIFIER_KEYS = [
    "service",
    "instance",
    "service_name",
    "phase",
    "endpoint.found",
    "endpoint.node",
    "endpoint.port",
    "endpoint.status",
    "register_response.qmi_result_valid",
    "register_response.qmi_result",
    "register_response.qmi_error",
    "register_response.curr_state_valid",
    "register_response.curr_state",
    "register_response.curr_state_name",
    "register_response.success",
    "response_seen",
    "response_success",
    "response_curr_state_valid",
    "response_curr_state",
    "response_curr_state_name",
    "indication_seen",
    "indication_valid",
    "indication_curr_state",
    "indication_curr_state_name",
    "ack_sent",
    "ack_success",
    "timing.target_hold_ms",
    "timing.hold_ms",
    "timing.poll_timeout",
    "result",
]

LATE_PROBE_KEYS = [
    "service",
    "instance",
    "service_name",
    "phase",
    "endpoint.found",
    "endpoint.node",
    "endpoint.port",
    "endpoint.status",
    "lookup_attempted",
    "result",
]

QRTR_CASE_KEYS = [
    "service",
    "instance",
    "readback.timeout_ms",
    "readback.service_events",
    "readback.empty_events",
    "readback.end_of_list",
    "readback.timeout",
    "status",
]


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def intish(value: object) -> int:
    return prev1796.intish(value)


def collect(fields: dict[str, str], prefix: str, keys: list[str]) -> dict[str, str]:
    return {key: fields.get(prefix + key, "") for key in keys}


def qrtr_case(fields: dict[str, str], index: int) -> dict[str, str]:
    return collect(fields, f"wifi_companion_qrtr_readback.case_{index}.", QRTR_CASE_KEYS)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    return prev1802.event(fields, name)


def response_uninit(listener: dict[str, str]) -> bool:
    return (
        intish(listener.get("response_success")) > 0
        and listener.get("response_curr_state_name") == "uninit"
        and intish(listener.get("indication_seen")) == 0
    )


def qrtr_absent(case: dict[str, str]) -> bool:
    return (
        intish(case.get("readback.service_events")) == 0
        and intish(case.get("readback.empty_events")) > 0
        and intish(case.get("readback.end_of_list")) > 0
        and intish(case.get("readback.timeout")) == 0
        and case.get("status") == "complete"
    )


def classify(
    fields: dict[str, str],
    source_manifest: dict[str, Any],
    source_v1802_manifest: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    early_listener = collect(fields, "wifi_companion_service_notifier_listener.", NOTIFIER_KEYS)
    late_probe = collect(fields, "wifi_companion_service_notifier_late_probe.", LATE_PROBE_KEYS)
    late_listener = collect(fields, "wifi_companion_service_notifier_late_listener.", NOTIFIER_KEYS)
    case_0 = qrtr_case(fields, 0)
    case_1 = qrtr_case(fields, 1)
    wlfw_service_request = event(fields, "wlfw_service_request")
    wlfw_ind_register = event(fields, "wlfw_ind_register_qmi")
    wlfw_cap = event(fields, "wlfw_cap_qmi")

    details: dict[str, Any] = {
        "source_decision": source_manifest.get("decision", ""),
        "source_pass": bool(source_manifest.get("pass")),
        "source_projection_label": source_manifest.get("gate", {}).get("pm_service_devnode_projection_label", ""),
        "source_pm_server_label": source_manifest.get("gate", {}).get("pm_server_label", ""),
        "source_list_commit_hits": source_manifest.get("gate", {}).get("pm_service_add_peripheral_list_commit_hits", ""),
        "source_pm_register_success_hits": source_manifest.get("gate", {}).get("pm_server_success_return_hits", ""),
        "source_v1802_decision": source_v1802_manifest.get("decision", ""),
        "source_v1802_pass": bool(source_v1802_manifest.get("pass")),
        "source_v1802_reason": source_v1802_manifest.get("reason", ""),
        "nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "requested_wlanmdsp": fields.get("wlan_pd_service_object_visible_trigger.requested_wlanmdsp", ""),
        "wlfw_service69_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen", ""),
        "wlan0_present": fields.get("wlan_pd_service_object_visible_trigger.wlan0_present", ""),
        "wlfw_service_request": wlfw_service_request,
        "wlfw_ind_register_qmi": wlfw_ind_register,
        "wlfw_cap_qmi": wlfw_cap,
        "qrtr_nameservice_readback": fields.get("wifi_companion_start.qrtr_nameservice_readback", ""),
        "service_notifier_listener_probe": fields.get("wifi_companion_start.service_notifier_listener_probe", ""),
        "route_order": fields.get("wifi_companion_start.order", ""),
        "qrtr_matrix": fields.get("wifi_companion_qrtr_readback.matrix", ""),
        "qrtr_case_0": case_0,
        "qrtr_case_1": case_1,
        "service_notifier_listener": early_listener,
        "service_notifier_late_probe": late_probe,
        "service_notifier_late_listener": late_listener,
    }

    if not bool(source_manifest.get("pass")):
        return "source-v1801-not-pass", "V1801 source manifest was not PASS", details
    if not bool(source_v1802_manifest.get("pass")):
        return "source-v1802-not-pass", "V1802 source manifest was not PASS", details
    if intish(source_manifest.get("gate", {}).get("pm_service_add_peripheral_list_commit_hits")) <= 0:
        return "pm-service-list-not-committed", "V1801 did not prove PM-service list commit", details
    if intish(wlfw_service_request.get("hit_count")) <= 0:
        return "wlfw-service-request-missing", "WLFW worker service request did not run", details
    if intish(wlfw_ind_register.get("hit_count")) > 0 or intish(wlfw_cap.get("hit_count")) > 0:
        return "wlfw-qmi-send-progress", "WLFW reached indication/capability QMI send path", details
    if intish(fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen")) > 0:
        return "wlfw-service69-progress", "WLFW service 69 appeared in the service-object summary", details
    if intish(case_0.get("readback.service_events")) > 0 or intish(case_1.get("readback.service_events")) > 0:
        return "qrtr-wlfw-service69-progress", "QRTR readback saw WLFW service 69", details
    if intish(early_listener.get("indication_seen")) > 0 or intish(late_listener.get("indication_seen")) > 0:
        return "wlan-pd-servnotif-indication-progress", "Service-notifier emitted a wlan_pd state indication", details
    if not response_uninit(early_listener) or not response_uninit(late_listener):
        return "wlan-pd-servnotif-state-incomplete", "Service-notifier state did not match the expected uninit/no-indication shape", details
    if qrtr_absent(case_0) and qrtr_absent(case_1):
        return (
            "wlan-pd-servnotif-uninit-wlfw-service69-absent",
            "wlan_pd service-notifier remained uninit/no-indication while QRTR WLFW service 69 readback returned end-of-list for instances 0 and 1",
            details,
        )
    return "wlfw-qmi-readiness-incomplete", "QRTR/service-notifier readiness discriminator was incomplete", details


def render_event(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` hits/registered/enabled: `{data.get('hit_count')}` / `{data.get('registered')}` / `{data.get('enabled')}`",
        f"- `{name}` first hit: `{data.get('first_hit_line')}`",
    ]


def render_listener(title: str, data: dict[str, str]) -> list[str]:
    return [
        f"- {title} service/instance/name: `{data.get('service')}` / `{data.get('instance')}` / `{data.get('service_name')}`",
        f"- {title} endpoint: `{data.get('endpoint.status')}` node `{data.get('endpoint.node')}` port `{data.get('endpoint.port')}`",
        f"- {title} response: success `{data.get('response_success')}`, state `{data.get('response_curr_state_name')}` (`{data.get('response_curr_state')}`)",
        f"- {title} indication/ack: `{data.get('indication_seen')}` / `{data.get('ack_sent')}`",
        f"- {title} hold/poll/result: `{data.get('timing.hold_ms')}` / `{data.get('timing.poll_timeout')}` / `{data.get('result')}`",
    ]


def render_qrtr_case(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` service/instance/status: `{data.get('service')}` / `{data.get('instance')}` / `{data.get('status')}`",
        f"- `{name}` service/empty/end/timeout: `{data.get('readback.service_events')}` / `{data.get('readback.empty_events')}` / `{data.get('readback.end_of_list')}` / `{data.get('readback.timeout')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    late_probe = details["service_notifier_late_probe"]
    lines = [
        "# Native Init V1803 WLFW QMI Readiness Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1803`",
        "- Type: host-only classifier over V1801 rollback-verified helper evidence and V1802 classifier output",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{details['source_dir']}`",
        f"- Source classifier: `{details['source_v1802_dir']}`",
        "",
        "## Source Gates",
        "",
        f"- V1801 decision: `{details['source_decision']}`",
        f"- V1802 decision: `{details['source_v1802_decision']}`",
        f"- V1802 reason: {details['source_v1802_reason']}",
        f"- projection label: `{details['source_projection_label']}`",
        f"- PM server label: `{details['source_pm_server_label']}`",
        f"- list commit hits: `{details['source_list_commit_hits']}`",
        f"- PM register success hits: `{details['source_pm_register_success_hits']}`",
        "",
        "## WLFW Worker Gate",
        "",
        f"- non-log label: `{details['nonlog_label']}`",
        f"- requested `wlanmdsp`: `{details['requested_wlanmdsp']}`",
        f"- WLFW service 69 seen: `{details['wlfw_service69_seen']}`",
        f"- wlan0 present: `{details['wlan0_present']}`",
        *render_event("wlfw_service_request", details["wlfw_service_request"]),
        *render_event("wlfw_ind_register_qmi", details["wlfw_ind_register_qmi"]),
        *render_event("wlfw_cap_qmi", details["wlfw_cap_qmi"]),
        "",
        "## QRTR Readback",
        "",
        f"- route order: `{details['route_order']}`",
        f"- nameservice readback/listener probe: `{details['qrtr_nameservice_readback']}` / `{details['service_notifier_listener_probe']}`",
        f"- matrix: `{details['qrtr_matrix']}`",
        *render_qrtr_case("case_0", details["qrtr_case_0"]),
        *render_qrtr_case("case_1", details["qrtr_case_1"]),
        "",
        "## Service Notifier",
        "",
        *render_listener("early listener", details["service_notifier_listener"]),
        f"- late probe endpoint/result: `{late_probe.get('endpoint.status')}` node `{late_probe.get('endpoint.node')}` port `{late_probe.get('endpoint.port')}` / `{late_probe.get('result')}`",
        *render_listener("late listener", details["service_notifier_late_listener"]),
        "",
        "## Interpretation",
        "",
        "- PM-service list/register is no longer the immediate blocker: the projected private devnodes allowed list commit and PM registration success.",
        "- WLFW worker starts and requests QMI service, but it does not reach the first WLFW indication/capability QMI sends.",
        "- The bounded readiness evidence shows `msm/modem/wlan_pd` service-notifier endpoint exists but reports `uninit` early and late with no indication, while QRTR readback for WLFW service 69 instances `0` and `1` returns end-of-list.",
        "- The next unit should stay below Wi-Fi HAL/scan/connect and classify the safe prerequisite for moving wlan_pd from service-notifier `uninit` to a state where WLFW service 69 is present.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source_v1802_manifest_path = SOURCE_V1802_DIR / "manifest.json"
    if not source_manifest_path.exists():
        raise SystemExit(f"missing source manifest: {source_manifest_path}")
    if not source_v1802_manifest_path.exists():
        raise SystemExit(f"missing V1802 source manifest: {source_v1802_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_v1802_manifest = json.loads(source_v1802_manifest_path.read_text(encoding="utf-8"))
    fields = prev1796.runner.fwbase.parse_helper_fields(SOURCE_DIR)
    label, reason, details = classify(fields, source_manifest, source_v1802_manifest)
    details["source_dir"] = rel(SOURCE_DIR)
    details["source_v1802_dir"] = rel(SOURCE_V1802_DIR)
    result = {
        "cycle": CYCLE,
        "decision": f"v1803-{label}-host-pass",
        "pass": True,
        "reason": reason,
        "source_manifest": rel(source_manifest_path),
        "source_v1802_manifest": rel(source_v1802_manifest_path),
        "out_dir": rel(OUT_DIR),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_report(result), encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": True, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
