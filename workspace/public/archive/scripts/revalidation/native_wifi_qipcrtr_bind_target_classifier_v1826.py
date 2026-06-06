#!/usr/bin/env python3
"""V1826 host-only classifier for the next QIPCRTR bind-state target."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1826"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1825-qipcrtr-socket-state-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1826-qipcrtr-bind-target-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1826_QIPCRTR_BIND_TARGET_CLASSIFIER_2026-06-03.md"
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
        "native_qipcrtr_socket_label": gate.get("qipcrtr_socket_label", ""),
        "native_qipcrtr_socket_mode": gate.get("qipcrtr_socket_mode", ""),
        "native_qipcrtr_socket_family": gate.get("qipcrtr_socket_family", ""),
        "native_qipcrtr_socket_type": gate.get("qipcrtr_socket_type", ""),
        "native_qipcrtr_open_rc": gate.get("qipcrtr_socket_open_rc", ""),
        "native_qipcrtr_getsockname_rc": gate.get("qipcrtr_socket_getsockname_rc", ""),
        "native_qipcrtr_getsockname_family": gate.get("qipcrtr_socket_getsockname_family", ""),
        "native_qipcrtr_getsockname_node": gate.get("qipcrtr_socket_getsockname_node", ""),
        "native_qipcrtr_getsockname_port": gate.get("qipcrtr_socket_getsockname_port", ""),
        "native_qipcrtr_close_rc": gate.get("qipcrtr_socket_close_rc", ""),
        "native_qipcrtr_before_sockets": intish(gate.get("qipcrtr_socket_before_sockets")),
        "native_qipcrtr_after_open_sockets": intish(gate.get("qipcrtr_socket_after_open_sockets")),
        "native_qipcrtr_after_close_sockets": intish(gate.get("qipcrtr_socket_after_close_sockets")),
        "native_qipcrtr_count_rises_while_open": gate.get("qipcrtr_socket_count_rises_while_open"),
        "native_qipcrtr_no_bind": gate.get("qipcrtr_socket_no_bind", ""),
        "native_qipcrtr_no_connect": gate.get("qipcrtr_socket_no_connect", ""),
        "native_qipcrtr_no_send": gate.get("qipcrtr_socket_no_send", ""),
        "native_qipcrtr_no_lookup_send": gate.get("qipcrtr_socket_no_lookup_send", ""),
        "native_qipcrtr_no_control_payload": gate.get("qipcrtr_socket_no_control_payload", ""),
        "native_qipcrtr_no_service_start": gate.get("qipcrtr_socket_no_service_start", ""),
        "native_qipcrtr_contract_ok": gate.get("qipcrtr_socket_contract_ok"),
        "native_qipcrtr_safety_ok": gate.get("qipcrtr_socket_safety_ok"),
        "native_qrtr_registry_readable": gate.get("qrtr_registry_readable"),
        "native_qrtr_registry_proc_open_counts": gate.get("qrtr_registry_proc_net_qrtr_open_counts", ""),
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


def native_unbound_qipcrtr_socket_only(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_qipcrtr_socket_label") == "qipcrtr-socket-open-getname-close-passive"
        and details.get("native_qipcrtr_socket_mode") == "passive-open-getsockname-close"
        and details.get("native_qipcrtr_socket_family") == "AF_QIPCRTR"
        and details.get("native_qipcrtr_socket_type") == "SOCK_DGRAM"
        and details.get("native_qipcrtr_open_rc") == "0"
        and details.get("native_qipcrtr_getsockname_rc") == "0"
        and details.get("native_qipcrtr_getsockname_family") == "42"
        and details.get("native_qipcrtr_getsockname_node") == "1"
        and details.get("native_qipcrtr_getsockname_port") == "0"
        and details.get("native_qipcrtr_close_rc") == "0"
        and details.get("native_qipcrtr_before_sockets") == 0
        and details.get("native_qipcrtr_after_open_sockets") == 0
        and details.get("native_qipcrtr_after_close_sockets") == 0
        and not boolish(details.get("native_qipcrtr_count_rises_while_open"))
        and details.get("native_qipcrtr_no_bind") == "1"
        and details.get("native_qipcrtr_no_connect") == "1"
        and details.get("native_qipcrtr_no_send") == "1"
        and details.get("native_qipcrtr_no_lookup_send") == "1"
        and details.get("native_qipcrtr_no_control_payload") == "1"
        and details.get("native_qipcrtr_no_service_start") == "1"
        and boolish(details.get("native_qipcrtr_contract_ok"))
        and boolish(details.get("native_qipcrtr_safety_ok"))
        and not boolish(details.get("native_qrtr_registry_readable"))
        and details.get("native_qrtr_registry_proc_open_counts") == "0,0,0"
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
    if not native_unbound_qipcrtr_socket_only(details):
        return (
            "native-qipcrtr-unbound-socket-shape-incomplete",
            "V1825 evidence did not match the fixed unbound AF_QIPCRTR open/getname/close shape",
        )
    return (
        "passive-qipcrtr-autobind-state-target",
        "Native can open an unbound AF_QIPCRTR datagram socket, but it remains port 0 with zero protocol-table socket count; the next source target can test local auto-bind state without connect, send, lookup, service start, or QRTR control payload",
    )


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    result_text = "PASS" if result["pass"] else "FAIL"
    return "\n".join([
        "# Native Init V1826 QIPCRTR Bind Target Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1826`",
        "- Type: host-only classifier over V1825 passive QIPCRTR socket handoff",
        f"- Decision: `{result['decision']}`",
        f"- Result: {result_text}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        "",
        "## Native V1825 Shape",
        "",
        f"- V1825 decision: `{d['source_decision']}`",
        f"- socket label/mode: `{d['native_qipcrtr_socket_label']}` / `{d['native_qipcrtr_socket_mode']}`",
        f"- open/getsockname/close rc: `{d['native_qipcrtr_open_rc']}` / `{d['native_qipcrtr_getsockname_rc']}` / `{d['native_qipcrtr_close_rc']}`",
        f"- getsockname family/node/port: `{d['native_qipcrtr_getsockname_family']}` / `{d['native_qipcrtr_getsockname_node']}` / `{d['native_qipcrtr_getsockname_port']}`",
        f"- sockets before/after-open/after-close: `{d['native_qipcrtr_before_sockets']}` / `{d['native_qipcrtr_after_open_sockets']}` / `{d['native_qipcrtr_after_close_sockets']}`",
        f"- no bind/connect/send/lookup/control/service-start: `{d['native_qipcrtr_no_bind']}` / `{d['native_qipcrtr_no_connect']}` / `{d['native_qipcrtr_no_send']}` / `{d['native_qipcrtr_no_lookup_send']}` / `{d['native_qipcrtr_no_control_payload']}` / `{d['native_qipcrtr_no_service_start']}`",
        f"- registry readable/proc open counts: `{d['native_qrtr_registry_readable']}` / `{d['native_qrtr_registry_proc_open_counts']}`",
        f"- service-locator/domain counts: `{d['native_service_locator_counts']}` / `{d['native_servloc_domain_counts']}`",
        f"- service180/service74/wlan_pd counts: `{d['native_service180_counts']}` / `{d['native_service74_counts']}` / `{d['native_wlan_pd_counts']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{d['native_lower_mdm3_states']}` / `{d['native_lower_mhi_present']}` / `{d['native_lower_service69_progress']}` / `{d['native_lower_wlan0_present']}`",
        "",
        "## Interpretation",
        "",
        "- The unbound QIPCRTR socket path is safe but not discriminating enough: it returns local node 1, port 0, and leaves the protocol socket count at zero.",
        "- The next source/build target should stay bounded to local auto-bind state and still avoid connect, send, service lookup, service start, and QRTR control payloads.",
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
    passed = label == "passive-qipcrtr-autobind-state-target"
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1826-{label}-host-{status}",
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
