#!/usr/bin/env python3
"""V1809 host-only classifier for PM-client-success lower handoff state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1809"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1808-pm-client-return-fetchargs-handoff"
V739_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v739-mdm3-wlanpd-delta" / "manifest.json"
V852_ANDROID_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v852-android-ext-mdm-provider-surface-handoff"
    / "v852-android-ext-mdm-provider-surface-run"
    / "manifest.json"
)
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1809-pm-client-success-lower-handoff-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1809_PM_CLIENT_SUCCESS_LOWER_HANDOFF_CLASSIFIER_2026-06-03.md"
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    return prev1796.intish(value)


def field(fields: dict[str, str], key: str) -> str:
    return fields.get(key, "")


def collect_listener(fields: dict[str, str], prefix: str) -> dict[str, str]:
    base = f"{prefix}."
    return {
        "endpoint_status": field(fields, base + "endpoint.status"),
        "endpoint_node": field(fields, base + "endpoint.node"),
        "endpoint_port": field(fields, base + "endpoint.port"),
        "response_success": field(fields, base + "response_success"),
        "response_curr_state": field(fields, base + "response_curr_state"),
        "response_curr_state_name": field(fields, base + "response_curr_state_name"),
        "indication_seen": field(fields, base + "indication_seen"),
        "ack_sent": field(fields, base + "ack_sent"),
        "result": field(fields, base + "result"),
        "hold_ms": field(fields, base + "timing.hold_ms"),
        "poll_timeout": field(fields, base + "timing.poll_timeout"),
        "phase": field(fields, base + "phase"),
    }


def collect_qrtr_case(fields: dict[str, str], index: int) -> dict[str, str]:
    base = f"wifi_companion_qrtr_readback.case_{index}."
    return {
        "service": field(fields, base + "service"),
        "instance": field(fields, base + "instance"),
        "service_events": field(fields, base + "readback.service_events"),
        "empty_events": field(fields, base + "readback.empty_events"),
        "end_of_list": field(fields, base + "readback.end_of_list"),
        "timeout": field(fields, base + "readback.timeout"),
        "status": field(fields, base + "status"),
    }


def collect_details(
    fields: dict[str, str],
    source: dict[str, Any],
    v739: dict[str, Any],
    v852: dict[str, Any],
) -> dict[str, Any]:
    gate = source.get("gate", {})
    v611 = v739.get("android_v611_summary", {})
    v622 = v739.get("android_v622_summary", {})
    v620 = v739.get("v620_summary", {})
    v852_summary = v852.get("android_summary", {})
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "pm_client_return_label": gate.get("pm_client_return_label", ""),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "pm_service_projection_label": gate.get("pm_service_devnode_projection_label", ""),
        "pm_server_label": gate.get("pm_server_label", ""),
        "pm_service_list_commit_hits": gate.get("pm_service_add_peripheral_list_commit_hits", ""),
        "pm_server_success_hits": gate.get("pm_server_success_return_hits", ""),
        "pm_client_register_rc": gate.get("pm_client_register_rc", ""),
        "pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
        "pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
        "mss_states": ",".join(
            value
            for value in (
                field(fields, "wlan_pd_post_pm_lower_state_observer.after_holder_start.sample_00.mss_state"),
                field(fields, "wlan_pd_post_pm_lower_state_observer.post_listener_window.sample_11.mss_state"),
            )
            if value
        ),
        "mdm3_states": gate.get("lower_mdm3_states", ""),
        "mdm_status_irq_totals": gate.get("lower_mdm_status_irq_totals", ""),
        "mhi_device_counts": gate.get("lower_mhi_device_counts", ""),
        "mhi_present": bool(gate.get("lower_mhi_present")),
        "wlan0_present": bool(gate.get("lower_wlan0_present")),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "wlfw_service69_seen": gate.get("wlfw_service69_seen", ""),
        "early_listener": collect_listener(fields, "wifi_companion_service_notifier_listener"),
        "late_listener": collect_listener(fields, "wifi_companion_service_notifier_late_listener"),
        "qrtr_case_0": collect_qrtr_case(fields, 0),
        "qrtr_case_1": collect_qrtr_case(fields, 1),
        "service_notifier_debugfs_count": field(fields, "A90_EXECNS_DIR_wifi_window_service_notifier_END count"),
        "android_v739_decision": v739.get("decision", ""),
        "android_v739_pass": bool(v739.get("pass")),
        "android_v611_counts": {
            "service_notifier_180": v611.get("counts", {}).get("service_notifier_180", ""),
            "service_notifier_74": v611.get("counts", {}).get("service_notifier_74", ""),
            "wlan_pd": v611.get("counts", {}).get("wlan_pd", ""),
            "wlan_pd_ack_180": v611.get("counts", {}).get("wlan_pd_ack_180", ""),
            "qmi_server_connected": v611.get("counts", {}).get("qmi_server_connected", ""),
        },
        "android_v622_counts": {
            "service_notifier_180": v622.get("counts", {}).get("service_notifier_180", ""),
            "service_notifier_74": v622.get("counts", {}).get("service_notifier_74", ""),
            "wlan_pd": v622.get("counts", {}).get("wlan_pd", ""),
            "wlan_pd_ack_180": v622.get("counts", {}).get("wlan_pd_ack_180", ""),
            "wlfw_start": v622.get("counts", {}).get("wlfw_start", ""),
            "qmi_server_connected": v622.get("counts", {}).get("qmi_server_connected", ""),
        },
        "android_v622_deltas_ms": {
            "sysmon_modem_to_service_notifier_180": v622.get("deltas_ms", {}).get("sysmon_modem_to_service_notifier_180", ""),
            "service_notifier_180_to_wlan_pd": v622.get("deltas_ms", {}).get("service_notifier_180_to_wlan_pd", ""),
            "service_notifier_180_to_wlfw_start": v622.get("deltas_ms", {}).get("service_notifier_180_to_wlfw_start", ""),
            "wlan_pd_to_qmi_server_connected": v622.get("deltas_ms", {}).get("wlan_pd_to_qmi_server_connected", ""),
        },
        "android_v620_causality": {
            "service_notifier_before_sysmon_esoc0": v620.get("causality_checks", {}).get("android_service_notifier_before_sysmon_esoc0", ""),
            "wlan_pd_before_sysmon_esoc0": v620.get("causality_checks", {}).get("android_wlan_pd_before_sysmon_esoc0", ""),
            "native_missing_service_notifier": v620.get("causality_checks", {}).get("native_missing_service_notifier", ""),
            "raw_esoc_open_should_not_be_retried": v620.get("inferences", {}).get("raw_esoc_open_should_not_be_retried", ""),
        },
        "android_v852_decision": v852.get("decision", ""),
        "android_v852_pass": bool(v852.get("pass")),
        "android_v852_mss_state": v852_summary.get("mss_state", ""),
        "android_v852_mdm3_state": v852_summary.get("mdm3_state", ""),
        "android_v852_counts": {
            "mdm3": v852_summary.get("counts", {}).get("mdm3", ""),
            "wlfw": v852_summary.get("counts", {}).get("wlfw", ""),
            "bdf": v852_summary.get("counts", {}).get("bdf", ""),
            "mhi": v852_summary.get("counts", {}).get("mhi", ""),
        },
        "android_v852_hints": {
            "has_wlan_pd": bool(v852_summary.get("dmesg_hints", {}).get("has_wlan_pd")),
            "has_wlfw": bool(v852_summary.get("dmesg_hints", {}).get("has_wlfw")),
            "has_bdf": bool(v852_summary.get("dmesg_hints", {}).get("has_bdf")),
            "has_wlan0": bool(v852_summary.get("dmesg_hints", {}).get("has_wlan0")),
        },
    }


def listener_uninit(listener: dict[str, str]) -> bool:
    return (
        listener.get("endpoint_status") == "found"
        and listener.get("response_success") == "1"
        and listener.get("response_curr_state_name") == "uninit"
        and intish(listener.get("indication_seen")) == 0
    )


def qrtr_service_absent(case: dict[str, str]) -> bool:
    return (
        intish(case.get("service_events")) == 0
        and intish(case.get("empty_events")) > 0
        and intish(case.get("end_of_list")) > 0
        and intish(case.get("timeout")) == 0
        and case.get("status") == "complete"
    )


def classify(details: dict[str, Any]) -> tuple[str, str]:
    pm_client_success = (
        bool(details.get("source_pass"))
        and details.get("pm_client_return_label") == "pm-client-return-success-still-offlining"
        and details.get("pm_client_register_rc") == "0"
        and details.get("pm_client_connect_rc") == "0"
        and details.get("pm_init_return_path_rc") == "0"
    )
    native_stall = (
        details.get("post_pm_lower_state_label") == "stable-mdm3-offlining"
        and details.get("mdm3_states") == "OFFLINING"
        and not bool(details.get("mhi_present"))
        and not bool(details.get("wlan0_present"))
        and intish(details.get("requested_wlanmdsp")) == 0
        and intish(details.get("wlfw_service69_seen")) == 0
        and listener_uninit(details["early_listener"])
        and listener_uninit(details["late_listener"])
        and qrtr_service_absent(details["qrtr_case_0"])
        and qrtr_service_absent(details["qrtr_case_1"])
    )
    android_positive = (
        bool(details.get("android_v739_pass"))
        and bool(details.get("android_v852_pass"))
        and intish(details["android_v622_counts"].get("service_notifier_180")) > 0
        and intish(details["android_v622_counts"].get("service_notifier_74")) > 0
        and intish(details["android_v622_counts"].get("wlan_pd")) > 0
        and intish(details["android_v622_counts"].get("qmi_server_connected")) > 0
        and details.get("android_v852_mdm3_state") == "ONLINE"
        and bool(details["android_v852_hints"].get("has_wlan_pd"))
        and bool(details["android_v852_hints"].get("has_wlfw"))
        and bool(details["android_v852_hints"].get("has_wlan0"))
    )
    if not pm_client_success:
        return "pm-client-success-not-established", "V1808 did not prove zero PM-client return values"
    if not native_stall:
        return "native-lower-stall-shape-incomplete", "V1808 lower-stall shape was incomplete"
    if not android_positive:
        return "android-positive-lower-handoff-incomplete", "Android-positive lower handoff baseline was incomplete"
    return (
        "pm-client-success-servnotif-uninit-lower-handoff-missing",
        "PM-client register/connect/return values are zero, but native wlan_pd service-notifier remains uninit with no indication and WLFW service 69 absent while Android-good reaches service-notifier 180/74, wlan_pd, WLFW, and wlan0",
    )


def render_listener(name: str, listener: dict[str, str]) -> list[str]:
    return [
        f"- {name} endpoint/status: `{listener.get('endpoint_status')}` node `{listener.get('endpoint_node')}` port `{listener.get('endpoint_port')}`",
        f"- {name} response: success `{listener.get('response_success')}`, state `{listener.get('response_curr_state_name')}` (`{listener.get('response_curr_state')}`)",
        f"- {name} indication/ack/result: `{listener.get('indication_seen')}` / `{listener.get('ack_sent')}` / `{listener.get('result')}`",
        f"- {name} hold/poll/phase: `{listener.get('hold_ms')}` / `{listener.get('poll_timeout')}` / `{listener.get('phase')}`",
    ]


def render_qrtr_case(name: str, case: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` service/instance/status: `{case.get('service')}` / `{case.get('instance')}` / `{case.get('status')}`",
        f"- `{name}` service/empty/end/timeout: `{case.get('service_events')}` / `{case.get('empty_events')}` / `{case.get('end_of_list')}` / `{case.get('timeout')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    lines = [
        "# Native Init V1809 PM-client-success Lower-handoff Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1809`",
        "- Type: host-only classifier over V1808 PM-client return evidence and Android-positive lower-handoff baselines",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Current Native Gate",
        "",
        f"- V1808 decision: `{d['source_decision']}`",
        f"- PM-client label: `{d['pm_client_return_label']}`",
        f"- lower-state label: `{d['post_pm_lower_state_label']}`",
        f"- projection / PM server labels: `{d['pm_service_projection_label']}` / `{d['pm_server_label']}`",
        f"- list commit / PM server success hits: `{d['pm_service_list_commit_hits']}` / `{d['pm_server_success_hits']}`",
        f"- PM-client register/connect/return rc: `{d['pm_client_register_rc']}` / `{d['pm_client_connect_rc']}` / `{d['pm_init_return_path_rc']}`",
        "",
        "## Current Lower State",
        "",
        f"- MSS states: `{d['mss_states']}`",
        f"- mdm3 states: `{d['mdm3_states']}`",
        f"- mdm status IRQ totals: `{d['mdm_status_irq_totals']}`",
        f"- MHI counts/present: `{d['mhi_device_counts']}` / `{d['mhi_present']}`",
        f"- requested `wlanmdsp` / WLFW service69 / wlan0: `{d['requested_wlanmdsp']}` / `{d['wlfw_service69_seen']}` / `{d['wlan0_present']}`",
        *render_listener("early listener", d["early_listener"]),
        *render_listener("late listener", d["late_listener"]),
        *render_qrtr_case("case_0", d["qrtr_case_0"]),
        *render_qrtr_case("case_1", d["qrtr_case_1"]),
        f"- service_notifier debugfs count: `{d['service_notifier_debugfs_count']}`",
        "",
        "## Android-positive Baselines",
        "",
        f"- V739 decision: `{d['android_v739_decision']}`",
        f"- V852 decision: `{d['android_v852_decision']}`",
        f"- Android V622 counts service-notifier 180/74, wlan_pd, ack, WLFW start, qmi-server: `{d['android_v622_counts']['service_notifier_180']}` / `{d['android_v622_counts']['service_notifier_74']}` / `{d['android_v622_counts']['wlan_pd']}` / `{d['android_v622_counts']['wlan_pd_ack_180']}` / `{d['android_v622_counts']['wlfw_start']}` / `{d['android_v622_counts']['qmi_server_connected']}`",
        f"- Android V622 deltas sysmon_modem→SN180, SN180→wlan_pd, SN180→WLFW, wlan_pd→qmi-server: `{d['android_v622_deltas_ms']['sysmon_modem_to_service_notifier_180']}` / `{d['android_v622_deltas_ms']['service_notifier_180_to_wlan_pd']}` / `{d['android_v622_deltas_ms']['service_notifier_180_to_wlfw_start']}` / `{d['android_v622_deltas_ms']['wlan_pd_to_qmi_server_connected']}`",
        f"- Android V620 causality SN before esoc0 / wlan_pd before esoc0 / raw esoc no-retry: `{d['android_v620_causality']['service_notifier_before_sysmon_esoc0']}` / `{d['android_v620_causality']['wlan_pd_before_sysmon_esoc0']}` / `{d['android_v620_causality']['raw_esoc_open_should_not_be_retried']}`",
        f"- Android V852 mss/mdm3: `{d['android_v852_mss_state']}` / `{d['android_v852_mdm3_state']}`",
        f"- Android V852 counts mdm3/WLFW/BDF/MHI: `{d['android_v852_counts']['mdm3']}` / `{d['android_v852_counts']['wlfw']}` / `{d['android_v852_counts']['bdf']}` / `{d['android_v852_counts']['mhi']}`",
        f"- Android V852 hints wlan_pd/WLFW/BDF/wlan0: `{d['android_v852_hints']['has_wlan_pd']}` / `{d['android_v852_hints']['has_wlfw']}` / `{d['android_v852_hints']['has_bdf']}` / `{d['android_v852_hints']['has_wlan0']}`",
        "",
        "## Interpretation",
        "",
        "- PM-service list/register and `cnss-daemon` PM-client register/connect are now proven to return success in native init.",
        "- The remaining blocker is below that successful PM-client boundary: wlan_pd service-notifier state remains `uninit` early and late, no indication is produced, and WLFW service 69 is absent.",
        "- Android-good evidence shows service-notifier 180/74, wlan_pd UP/ACK, qmi-server, WLFW/BDF, and `wlan0` occur without requiring native to open `/dev/subsys_esoc0` directly.",
        "- Next work should observe the service-notifier/sysmon/subsys lower handoff after PM-client success; Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain premature.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source = load_json(source_manifest_path)
    v739 = load_json(V739_MANIFEST)
    v852 = load_json(V852_ANDROID_MANIFEST)
    fields = prev1796.runner.fwbase.parse_helper_fields(SOURCE_DIR)
    label, reason = classify(collect_details(fields, source, v739, v852))
    details = collect_details(fields, source, v739, v852)
    details["source_manifest"] = rel(source_manifest_path)
    details["v739_manifest"] = rel(V739_MANIFEST)
    details["v852_manifest"] = rel(V852_ANDROID_MANIFEST)
    result = {
        "cycle": CYCLE,
        "decision": f"v1809-{label}-host-pass",
        "pass": True,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "source_manifest": rel(source_manifest_path),
        "v739_manifest": rel(V739_MANIFEST),
        "v852_manifest": rel(V852_ANDROID_MANIFEST),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = render_report(result)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": True, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
