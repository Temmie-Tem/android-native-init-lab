#!/usr/bin/env python3
"""V1829 host-only classifier for QIPCRTR local-node auto-bind target."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1829"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1828-qipcrtr-autobind-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1829-qipcrtr-local-node-bind-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1829_QIPCRTR_LOCAL_NODE_BIND_CLASSIFIER_2026-06-03.md"
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return bool(value) and str(value) not in {"0", "False", "false", "None", ""}


def intish(value: object) -> int:
    return prev1796.intish(value)


def collect_details(source: dict[str, Any]) -> dict[str, Any]:
    gate = source.get("gate", {})
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_DIR / "manifest.json"),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "native_autobind_label": gate.get("qipcrtr_autobind_label", ""),
        "native_autobind_mode": gate.get("qipcrtr_autobind_mode", ""),
        "native_autobind_open_rc": gate.get("qipcrtr_autobind_open_rc", ""),
        "native_autobind_before_node": gate.get("qipcrtr_autobind_getsockname_before_node", ""),
        "native_autobind_before_port": gate.get("qipcrtr_autobind_getsockname_before_port", ""),
        "native_autobind_bind_request_family": gate.get("qipcrtr_autobind_bind_request_family", ""),
        "native_autobind_bind_request_node": gate.get("qipcrtr_autobind_bind_request_node", ""),
        "native_autobind_bind_request_port": gate.get("qipcrtr_autobind_bind_request_port", ""),
        "native_autobind_bind_rc": gate.get("qipcrtr_autobind_bind_rc", ""),
        "native_autobind_bind_errno": gate.get("qipcrtr_autobind_bind_errno", ""),
        "native_autobind_bind_error": gate.get("qipcrtr_autobind_bind_error", ""),
        "native_autobind_close_rc": gate.get("qipcrtr_autobind_close_rc", ""),
        "native_autobind_before_sockets": intish(gate.get("qipcrtr_autobind_before_sockets")),
        "native_autobind_while_bound_sockets": intish(gate.get("qipcrtr_autobind_while_bound_sockets")),
        "native_autobind_after_close_sockets": intish(gate.get("qipcrtr_autobind_after_close_sockets")),
        "native_autobind_no_connect": gate.get("qipcrtr_autobind_no_connect", ""),
        "native_autobind_no_send": gate.get("qipcrtr_autobind_no_send", ""),
        "native_autobind_no_lookup_send": gate.get("qipcrtr_autobind_no_lookup_send", ""),
        "native_autobind_no_control_payload": gate.get("qipcrtr_autobind_no_control_payload", ""),
        "native_autobind_no_service_start": gate.get("qipcrtr_autobind_no_service_start", ""),
        "native_autobind_contract_ok": gate.get("qipcrtr_autobind_contract_ok"),
        "native_autobind_safety_ok": gate.get("qipcrtr_autobind_safety_ok"),
        "native_registry_readable": gate.get("qrtr_registry_readable"),
        "native_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "native_servloc_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "native_service180_counts": gate.get("raw_service180_text_counts", ""),
        "native_service74_counts": gate.get("raw_service74_text_counts", ""),
        "native_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "native_lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "native_lower_mhi_present": gate.get("lower_mhi_present"),
        "native_lower_service69_progress": gate.get("lower_service69_progress"),
        "native_lower_wlan0_present": gate.get("lower_wlan0_present"),
        "native_safety_ok": gate.get("safety_ok"),
    }


def node_zero_bind_invalid_shape(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_autobind_label") == "qipcrtr-autobind-fails"
        and details.get("native_autobind_mode") == "local-autobind-getsockname-close"
        and details.get("native_autobind_open_rc") == "0"
        and details.get("native_autobind_before_node") == "1"
        and details.get("native_autobind_before_port") == "0"
        and details.get("native_autobind_bind_request_family") == "42"
        and details.get("native_autobind_bind_request_node") == "0"
        and details.get("native_autobind_bind_request_port") == "0"
        and details.get("native_autobind_bind_rc") == "-1"
        and details.get("native_autobind_bind_errno") == "22"
        and details.get("native_autobind_close_rc") == "0"
        and details.get("native_autobind_before_sockets") == 0
        and details.get("native_autobind_while_bound_sockets") == 0
        and details.get("native_autobind_after_close_sockets") == 0
        and details.get("native_autobind_no_connect") == "1"
        and details.get("native_autobind_no_send") == "1"
        and details.get("native_autobind_no_lookup_send") == "1"
        and details.get("native_autobind_no_control_payload") == "1"
        and details.get("native_autobind_no_service_start") == "1"
        and boolish(details.get("native_autobind_contract_ok"))
        and boolish(details.get("native_autobind_safety_ok"))
        and not boolish(details.get("native_registry_readable"))
        and details.get("native_service_locator_counts") == "2,2,2"
        and details.get("native_servloc_domain_counts") == "0,0,0"
        and details.get("native_service180_counts") == "1,1,1"
        and details.get("native_service74_counts") == "0,0,0"
        and details.get("native_wlan_pd_counts") == "0,0,0"
        and details.get("native_lower_mdm3_states") == "OFFLINING"
        and not boolish(details.get("native_lower_mhi_present"))
        and not boolish(details.get("native_lower_service69_progress"))
        and not boolish(details.get("native_lower_wlan0_present"))
        and boolish(details.get("native_safety_ok"))
    )


def classify(details: dict[str, Any]) -> tuple[str, str]:
    if not node_zero_bind_invalid_shape(details):
        return (
            "native-qipcrtr-node-zero-bind-shape-incomplete",
            "V1828 evidence did not match the fixed node-zero bind EINVAL shape",
        )
    return (
        "qipcrtr-local-node-autobind-target",
        "Binding AF_QIPCRTR with node 0 and port 0 fails with EINVAL while the unbound socket reports local node 1; the next source target can try observed-local-node/port-0 bind without connect, send, lookup, service start, or QRTR control payload",
    )


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    result_text = "PASS" if result["pass"] else "FAIL"
    return "\n".join([
        "# Native Init V1829 QIPCRTR Local-Node Bind Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1829`",
        "- Type: host-only classifier over V1828 QIPCRTR auto-bind handoff",
        f"- Decision: `{result['decision']}`",
        f"- Result: {result_text}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Native V1828 Shape",
        "",
        f"- V1828 decision: `{d['source_decision']}`",
        f"- auto-bind label/mode: `{d['native_autobind_label']}` / `{d['native_autobind_mode']}`",
        f"- open/bind/close rc: `{d['native_autobind_open_rc']}` / `{d['native_autobind_bind_rc']}` / `{d['native_autobind_close_rc']}`",
        f"- before-bind node/port: `{d['native_autobind_before_node']}` / `{d['native_autobind_before_port']}`",
        f"- bind request family/node/port: `{d['native_autobind_bind_request_family']}` / `{d['native_autobind_bind_request_node']}` / `{d['native_autobind_bind_request_port']}`",
        f"- bind errno/error: `{d['native_autobind_bind_errno']}` / `{d['native_autobind_bind_error']}`",
        f"- sockets before/while-bound/after-close: `{d['native_autobind_before_sockets']}` / `{d['native_autobind_while_bound_sockets']}` / `{d['native_autobind_after_close_sockets']}`",
        f"- no connect/send/lookup/control/service-start: `{d['native_autobind_no_connect']}` / `{d['native_autobind_no_send']}` / `{d['native_autobind_no_lookup_send']}` / `{d['native_autobind_no_control_payload']}` / `{d['native_autobind_no_service_start']}`",
        f"- service180/service74/wlan_pd counts: `{d['native_service180_counts']}` / `{d['native_service74_counts']}` / `{d['native_wlan_pd_counts']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{d['native_lower_mdm3_states']}` / `{d['native_lower_mhi_present']}` / `{d['native_lower_service69_progress']}` / `{d['native_lower_wlan0_present']}`",
        "",
        "## Interpretation",
        "",
        "- Node-zero bind is not the correct native QRTR endpoint-allocation form on this kernel.",
        "- The next source/build target should try the observed local node `1` with port `0`, still without connect, send, service lookup, service start, or QRTR control payload.",
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
    passed = label == "qipcrtr-local-node-autobind-target"
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1829-{label}-host-{status}",
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
