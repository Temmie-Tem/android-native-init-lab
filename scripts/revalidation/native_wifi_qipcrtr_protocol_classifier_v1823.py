#!/usr/bin/env python3
"""V1823 host-only classifier for QIPCRTR protocol state after V1822."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1823"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1822-qrtr-registry-handoff"
HELPER_STDOUT = SOURCE_DIR / "test-v1393-helper-result.stdout.txt"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1823-qipcrtr-protocol-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1823_QIPCRTR_PROTOCOL_CLASSIFIER_2026-06-03.md"
)
QIPCRTR_PHASES = ("net_before", "net_after_spawn", "net_window", "net_after_cleanup")


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


def parse_helper_fields(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"missing helper stdout: {path}")
    text = path.read_bytes().decode("utf-8", "replace").replace("\x00", "")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def collect_details(source: dict[str, Any], helper_fields: dict[str, str]) -> dict[str, Any]:
    gate = source.get("gate", {})
    qipcrtr = {}
    for phase in QIPCRTR_PHASES:
        prefix = f"wifi_companion_start.{phase}."
        qipcrtr[phase] = {
            "protocols_open": helper_fields.get(prefix + "protocols_open", ""),
            "present": helper_fields.get(prefix + "qipcrtr_present", ""),
            "size": helper_fields.get(prefix + "qipcrtr_size", ""),
            "sockets": helper_fields.get(prefix + "qipcrtr_sockets", ""),
            "line": helper_fields.get(prefix + "qipcrtr_line", ""),
        }
    return {
        "source_dir": rel(SOURCE_DIR),
        "source_manifest": rel(SOURCE_DIR / "manifest.json"),
        "helper_stdout": rel(HELPER_STDOUT),
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_reason": source.get("reason", ""),
        "rollback_ok": source.get("rollback", {}).get("ok"),
        "native_qrtr_registry_label": gate.get("qrtr_registry_label", ""),
        "native_qrtr_registry_readable": gate.get("qrtr_registry_readable"),
        "native_qrtr_registry_proc_open_counts": gate.get("qrtr_registry_proc_net_qrtr_open_counts", ""),
        "native_qrtr_registry_nodes_open_counts": gate.get("qrtr_registry_qrtr_nodes_open_counts", ""),
        "native_qrtr_registry_services_open_counts": gate.get("qrtr_registry_qrtr_services_open_counts", ""),
        "native_qrtr_no_lookup_send": gate.get("qrtr_registry_no_lookup_send"),
        "native_qrtr_no_service_start": gate.get("qrtr_registry_no_service_start"),
        "native_publication_service_locator_counts": gate.get("raw_service_locator_counts", ""),
        "native_publication_domain_counts": gate.get("raw_servloc_domain_counts", ""),
        "native_service180_counts": gate.get("raw_service180_text_counts", ""),
        "native_service74_counts": gate.get("raw_service74_text_counts", ""),
        "native_wlan_pd_counts": gate.get("raw_wlan_pd_text_counts", ""),
        "native_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "native_lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "native_lower_mhi_present": gate.get("lower_mhi_present"),
        "native_lower_service69_progress": gate.get("lower_service69_progress"),
        "native_lower_wlan0_present": gate.get("lower_wlan0_present"),
        "native_safety_ok": gate.get("safety_ok"),
        "qipcrtr": qipcrtr,
        "qipcrtr_present_all": all(item["present"] == "1" for item in qipcrtr.values()),
        "qipcrtr_protocols_open_all": all(item["protocols_open"] == "1" for item in qipcrtr.values()),
        "qipcrtr_sockets_all_zero": all(item["sockets"] == "0" for item in qipcrtr.values()),
        "qipcrtr_line_seen": any(item["line"].startswith("QIPCRTR") for item in qipcrtr.values()),
        "net_window_qrtr_captured": helper_fields.get("wifi_companion_start.net_window.qrtr_captured", ""),
        "net_window_protocols_captured": helper_fields.get("wifi_companion_start.net_window.protocols_captured", ""),
    }


def native_qipcrtr_protocol_only_gap(details: dict[str, Any]) -> bool:
    return (
        bool(details.get("source_pass"))
        and bool(details.get("rollback_ok"))
        and details.get("native_qrtr_registry_label") == "qrtr-registry-unreadable-with-qmi-context"
        and not boolish(details.get("native_qrtr_registry_readable"))
        and boolish(details.get("native_qrtr_no_lookup_send"))
        and boolish(details.get("native_qrtr_no_service_start"))
        and bool(details.get("qipcrtr_present_all"))
        and bool(details.get("qipcrtr_protocols_open_all"))
        and bool(details.get("qipcrtr_sockets_all_zero"))
        and bool(details.get("qipcrtr_line_seen"))
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
    if not native_qipcrtr_protocol_only_gap(details):
        return (
            "native-qipcrtr-protocol-shape-incomplete",
            "V1822 evidence did not match the fixed protocol-present/proc-registry-absent native shape",
        )
    return (
        "passive-qipcrtr-socket-state-target",
        "QIPCRTR protocol support is present with zero native QRTR sockets while proc/debugfs registry paths are absent; the next source target can be a passive no-send socket state observer",
    )


def render_report(result: dict[str, Any]) -> str:
    d = result["details"]
    result_text = "PASS" if result["pass"] else "FAIL"
    lines = [
        "# Native Init V1823 QIPCRTR Protocol Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1823`",
        "- Type: host-only classifier over V1822 QRTR registry handoff helper stdout",
        f"- Decision: `{result['decision']}`",
        f"- Result: {result_text}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{d['source_dir']}`",
        f"- Helper stdout: `{d['helper_stdout']}`",
        "",
        "## Native V1822 Shape",
        "",
        f"- V1822 decision: `{d['source_decision']}`",
        f"- QRTR registry label/readable: `{d['native_qrtr_registry_label']}` / `{d['native_qrtr_registry_readable']}`",
        f"- registry proc/nodes/services open counts: `{d['native_qrtr_registry_proc_open_counts']}` / `{d['native_qrtr_registry_nodes_open_counts']}` / `{d['native_qrtr_registry_services_open_counts']}`",
        f"- no lookup send/service start: `{d['native_qrtr_no_lookup_send']}` / `{d['native_qrtr_no_service_start']}`",
        f"- service-locator/domain counts: `{d['native_publication_service_locator_counts']}` / `{d['native_publication_domain_counts']}`",
        f"- service180/service74/wlan_pd counts: `{d['native_service180_counts']}` / `{d['native_service74_counts']}` / `{d['native_wlan_pd_counts']}`",
        f"- mdm3/MHI/WLFW69/wlan0: `{d['native_lower_mdm3_states']}` / `{d['native_lower_mhi_present']}` / `{d['native_lower_service69_progress']}` / `{d['native_lower_wlan0_present']}`",
        "",
        "## QIPCRTR Protocol Summary",
        "",
        f"- present/protocols-open/sockets-zero/line-seen: `{d['qipcrtr_present_all']}` / `{d['qipcrtr_protocols_open_all']}` / `{d['qipcrtr_sockets_all_zero']}` / `{d['qipcrtr_line_seen']}`",
        f"- net window protocols/qrtr captured: `{d['net_window_protocols_captured']}` / `{d['net_window_qrtr_captured']}`",
    ]
    for phase in QIPCRTR_PHASES:
        item = d["qipcrtr"][phase]
        lines.append(
            f"- `{phase}` present/size/sockets: `{item['present']}` / `{item['size']}` / `{item['sockets']}`"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Native exposes QIPCRTR protocol support, but there are zero QRTR sockets across the sampled companion window.",
        "- `/proc/net/qrtr` and debugfs QRTR registry paths are absent, so registry-file observation is not a viable next surface.",
        "- The next source/build should remain passive: open/getsockname/close a QIPCRTR socket without bind, connect, send, lookup, service start, or QRTR control payload.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, send QRTR lookup packets, start services, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    source = load_json(source_manifest_path)
    helper_fields = parse_helper_fields(HELPER_STDOUT)
    details = collect_details(source, helper_fields)
    label, reason = classify(details)
    passed = label == "passive-qipcrtr-socket-state-target"
    status = "pass" if passed else "fail"
    result = {
        "cycle": CYCLE,
        "decision": f"v1823-{label}-host-{status}",
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "source_manifest": rel(source_manifest_path),
        "helper_stdout": rel(HELPER_STDOUT),
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
