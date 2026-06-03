#!/usr/bin/env python3
"""V1832 host-only classifier for passive bound QIPCRTR poll/recv target."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1832"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1831-qipcrtr-local-node-bind-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1832-qipcrtr-bound-recv-poll-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1832_QIPCRTR_BOUND_RECV_POLL_CLASSIFIER_2026-06-03.md"
)


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


def collect_details(source: dict[str, Any]) -> dict[str, Any]:
    gate = source.get("gate", {})
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_DIR / "manifest.json"),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "native_local_bind_label": gate.get("qipcrtr_local_bind_label", ""),
        "native_local_bind_mode": gate.get("qipcrtr_local_bind_mode", ""),
        "native_local_bind_family": gate.get("qipcrtr_local_bind_family", ""),
        "native_local_bind_type": gate.get("qipcrtr_local_bind_type", ""),
        "native_local_bind_open_rc": gate.get("qipcrtr_local_bind_open_rc", ""),
        "native_local_bind_before_rc": gate.get("qipcrtr_local_bind_before_rc", ""),
        "native_local_bind_before_node": gate.get("qipcrtr_local_bind_before_node", ""),
        "native_local_bind_before_port": gate.get("qipcrtr_local_bind_before_port", ""),
        "native_local_bind_request_family": gate.get("qipcrtr_local_bind_request_family", ""),
        "native_local_bind_request_node": gate.get("qipcrtr_local_bind_request_node", ""),
        "native_local_bind_request_port": gate.get("qipcrtr_local_bind_request_port", ""),
        "native_local_bind_rc": gate.get("qipcrtr_local_bind_rc", ""),
        "native_local_bind_after_rc": gate.get("qipcrtr_local_bind_after_rc", ""),
        "native_local_bind_after_family": gate.get("qipcrtr_local_bind_after_family", ""),
        "native_local_bind_after_node": gate.get("qipcrtr_local_bind_after_node", ""),
        "native_local_bind_after_port": gate.get("qipcrtr_local_bind_after_port", ""),
        "native_local_bind_close_rc": gate.get("qipcrtr_local_bind_close_rc", ""),
        "native_local_bind_before_sockets": intish(gate.get("qipcrtr_local_bind_before_sockets")),
        "native_local_bind_while_bound_sockets": intish(gate.get("qipcrtr_local_bind_while_bound_sockets")),
        "native_local_bind_after_close_sockets": intish(gate.get("qipcrtr_local_bind_after_close_sockets")),
        "native_local_bind_no_connect": gate.get("qipcrtr_local_bind_no_connect", ""),
        "native_local_bind_no_send": gate.get("qipcrtr_local_bind_no_send", ""),
        "native_local_bind_no_lookup_send": gate.get("qipcrtr_local_bind_no_lookup_send", ""),
        "native_local_bind_no_control_payload": gate.get("qipcrtr_local_bind_no_control_payload", ""),
        "native_local_bind_no_service_start": gate.get("qipcrtr_local_bind_no_service_start", ""),
        "native_local_bind_contract_ok": gate.get("qipcrtr_local_bind_contract_ok"),
        "native_local_bind_safety_ok": gate.get("qipcrtr_local_bind_safety_ok"),
        "native_local_bind_port_nonzero": gate.get("qipcrtr_local_bind_port_nonzero"),
        "native_qrtr_registry_readable": gate.get("qrtr_registry_readable"),
        "native_qrtr_registry_proc_open_counts": gate.get("qrtr_registry_proc_net_qrtr_open_counts", ""),
        "native_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "native_servloc_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "native_wlan_fw_counts": gate.get("raw_wlan_fw_counts", ""),
        "native_wlan_pd_domain_counts": gate.get("raw_wlan_pd_domain_counts", ""),
        "native_qmi_server_connected_counts": gate.get("raw_qmi_server_connected_counts", ""),
        "native_service180_counts": gate.get("raw_service180_text_counts", ""),
        "native_service74_counts": gate.get("raw_service74_text_counts", ""),
        "native_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "native_precondition_pd_mapper_counts": gate.get("raw_pd_mapper_counts", ""),
        "native_precondition_subsys_counts": gate.get("raw_subsys_counts", ""),
        "native_precondition_pil_counts": gate.get("raw_pil_counts", ""),
        "native_precondition_qmi_counts": gate.get("raw_qmi_counts", ""),
        "native_precondition_wlfw_counts": gate.get("raw_wlfw_counts", ""),
        "native_service_notifier_early_state": gate.get("service_notifier_early_state", ""),
        "native_service_notifier_late_state": gate.get("service_notifier_late_state", ""),
        "native_lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "native_lower_mhi_present": gate.get("lower_mhi_present"),
        "native_lower_service69_progress": gate.get("lower_service69_progress"),
        "native_lower_wlan0_present": gate.get("lower_wlan0_present"),
        "native_pm_client_register_rc": gate.get("pm_client_register_rc", ""),
        "native_pm_client_connect_rc": gate.get("pm_client_connect_rc", ""),
        "native_pm_init_return_path_rc": gate.get("pm_init_return_path_rc", ""),
        "native_safety_ok": gate.get("safety_ok"),
    }


def native_local_bind_port_only(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_local_bind_label") == "qipcrtr-local-node-bind-gets-local-port-passive"
        and details.get("native_local_bind_mode") == "observed-local-node-bind-getsockname-close"
        and details.get("native_local_bind_family") == "AF_QIPCRTR"
        and details.get("native_local_bind_type") == "SOCK_DGRAM"
        and details.get("native_local_bind_open_rc") == "0"
        and details.get("native_local_bind_before_rc") == "0"
        and details.get("native_local_bind_before_node") == "1"
        and details.get("native_local_bind_before_port") == "0"
        and details.get("native_local_bind_request_family") == "42"
        and details.get("native_local_bind_request_node") == "1"
        and details.get("native_local_bind_request_port") == "0"
        and details.get("native_local_bind_rc") == "0"
        and details.get("native_local_bind_after_rc") == "0"
        and details.get("native_local_bind_after_family") == "42"
        and details.get("native_local_bind_after_node") == "1"
        and intish(details.get("native_local_bind_after_port")) > 0
        and details.get("native_local_bind_close_rc") == "0"
        and details.get("native_local_bind_before_sockets") == 0
        and details.get("native_local_bind_while_bound_sockets") == 0
        and details.get("native_local_bind_after_close_sockets") == 0
        and details.get("native_local_bind_no_connect") == "1"
        and details.get("native_local_bind_no_send") == "1"
        and details.get("native_local_bind_no_lookup_send") == "1"
        and details.get("native_local_bind_no_control_payload") == "1"
        and details.get("native_local_bind_no_service_start") == "1"
        and boolish(details.get("native_local_bind_contract_ok"))
        and boolish(details.get("native_local_bind_safety_ok"))
        and boolish(details.get("native_local_bind_port_nonzero"))
        and not boolish(details.get("native_qrtr_registry_readable"))
        and details.get("native_qrtr_registry_proc_open_counts") == "0,0,0"
        and details.get("native_service_locator_counts") == "2,2,2"
        and details.get("native_servloc_domain_counts") == "0,0,0"
        and details.get("native_wlan_fw_counts") == "0,0,0"
        and details.get("native_wlan_pd_domain_counts") == "0,0,0"
        and details.get("native_qmi_server_connected_counts") == "0,0,0"
        and details.get("native_service180_counts") == "1,1,1"
        and details.get("native_service74_counts") == "0,0,0"
        and details.get("native_wlan_pd_counts") == "0,0,0"
        and details.get("native_service_notifier_early_state") == "uninit"
        and details.get("native_service_notifier_late_state") == "uninit"
        and details.get("native_lower_mdm3_states") == "OFFLINING"
        and not boolish(details.get("native_lower_mhi_present"))
        and not boolish(details.get("native_lower_service69_progress"))
        and not boolish(details.get("native_lower_wlan0_present"))
        and details.get("native_pm_client_register_rc") == "0"
        and details.get("native_pm_client_connect_rc") == "0"
        and details.get("native_pm_init_return_path_rc") == "0"
        and boolish(details.get("native_safety_ok"))
    )


def classify(details: dict[str, Any]) -> tuple[str, str]:
    if not native_local_bind_port_only(details):
        return (
            "native-qipcrtr-local-bind-shape-incomplete",
            "V1831 evidence did not match the fixed observed-local-node bind/local-port-only shape",
        )
    return (
        "passive-bound-qipcrtr-poll-recv-target",
        "Native can allocate a local QIPCRTR port without lookup/control traffic, but no lower publication follows; the next source target can hold that bound socket briefly and run timeout-bounded poll/recvfrom with no connect, send, lookup, service start, or QRTR control payload",
    )


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    result_text = "PASS" if result["pass"] else "FAIL"
    return "\n".join([
        "# Native Init V1832 QIPCRTR Bound Poll/Recv Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1832`",
        "- Type: host-only classifier over V1831 QIPCRTR observed-local-node bind handoff",
        f"- Decision: `{result['decision']}`",
        f"- Result: {result_text}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Native V1831 Shape",
        "",
        f"- V1831 decision: `{d['source_decision']}`",
        f"- local-bind label/mode: `{d['native_local_bind_label']}` / `{d['native_local_bind_mode']}`",
        f"- open/bind/close rc: `{d['native_local_bind_open_rc']}` / `{d['native_local_bind_rc']}` / `{d['native_local_bind_close_rc']}`",
        f"- before-bind node/port: `{d['native_local_bind_before_node']}` / `{d['native_local_bind_before_port']}`",
        f"- bind request family/node/port: `{d['native_local_bind_request_family']}` / `{d['native_local_bind_request_node']}` / `{d['native_local_bind_request_port']}`",
        f"- after-bind family/node/port: `{d['native_local_bind_after_family']}` / `{d['native_local_bind_after_node']}` / `{d['native_local_bind_after_port']}`",
        f"- socket counts before/while-bound/after-close: `{d['native_local_bind_before_sockets']}` / `{d['native_local_bind_while_bound_sockets']}` / `{d['native_local_bind_after_close_sockets']}`",
        f"- no connect/send/lookup/control/service-start: `{d['native_local_bind_no_connect']}` / `{d['native_local_bind_no_send']}` / `{d['native_local_bind_no_lookup_send']}` / `{d['native_local_bind_no_control_payload']}` / `{d['native_local_bind_no_service_start']}`",
        f"- registry readable/proc open counts: `{d['native_qrtr_registry_readable']}` / `{d['native_qrtr_registry_proc_open_counts']}`",
        f"- service-locator/domain/wlan-fw/wlan-pd-domain/qmi-server: `{d['native_service_locator_counts']}` / `{d['native_servloc_domain_counts']}` / `{d['native_wlan_fw_counts']}` / `{d['native_wlan_pd_domain_counts']}` / `{d['native_qmi_server_connected_counts']}`",
        f"- service180/service74/wlan_pd counts: `{d['native_service180_counts']}` / `{d['native_service74_counts']}` / `{d['native_wlan_pd_counts']}`",
        f"- precondition pd-mapper/subsys/pil/qmi/wlfw: `{d['native_precondition_pd_mapper_counts']}` / `{d['native_precondition_subsys_counts']}` / `{d['native_precondition_pil_counts']}` / `{d['native_precondition_qmi_counts']}` / `{d['native_precondition_wlfw_counts']}`",
        f"- notifier early/late state: `{d['native_service_notifier_early_state']}` / `{d['native_service_notifier_late_state']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{d['native_lower_mdm3_states']}` / `{d['native_lower_mhi_present']}` / `{d['native_lower_service69_progress']}` / `{d['native_lower_wlan0_present']}`",
        "",
        "## Interpretation",
        "",
        "- Local-node bind is the first native QIPCRTR endpoint allocation that returns a nonzero local port.",
        "- Endpoint allocation alone does not publish service 74, wlan_pd, WLFW service 69, MHI, or `wlan0`.",
        "- The next source/build target should only add a short timeout-bounded bound-socket `poll` plus `recvfrom` observer; it must not connect, send, issue QRTR lookup/control packets, or start services.",
        "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain invalid because WLFW service 69 and `wlan0` are absent.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, bind/connect/send QRTR sockets, send QRTR lookup/control packets, start services, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ])


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source = load_json(source_manifest_path)
    details = collect_details(source)
    label, reason = classify(details)
    passed = label == "passive-bound-qipcrtr-poll-recv-target"
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1832-{label}-host-{status}",
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "source_manifest": rel(source_manifest_path),
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
