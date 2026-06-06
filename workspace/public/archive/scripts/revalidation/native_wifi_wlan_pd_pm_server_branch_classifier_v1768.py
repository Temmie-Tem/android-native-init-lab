#!/usr/bin/env python3
"""V1768 host-only classifier for the PM server register branch.

V1767 extracted the narrow PeripheralManager contract but left live helper gates
suspended.  This classifier uses retained V1101 tracefs evidence to pin the
server-side branch more tightly without contacting the device.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1768-wlan-pd-pm-server-branch-classifier"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1768_WLAN_PD_PM_SERVER_BRANCH_CLASSIFIER_2026-06-03.md"
)

INPUTS = {
    "v1101": REPO_ROOT / "tmp" / "wifi" / "v1101-pm-server-register-path-tracefs-live" / "manifest.json",
    "v1101_report": REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1101_PM_SERVER_REGISTER_PATH_TRACEFS_2026-05-27.md",
    "v1766": REPO_ROOT / "tmp" / "wifi" / "v1766-wlan-pd-request-trigger-directive-classifier" / "manifest.json",
    "v1767": REPO_ROOT / "tmp" / "wifi" / "v1767-wlan-pd-pm-contract-extraction" / "manifest.json",
}

SERVER_SEQUENCE = (
    "pm_server_register_entry",
    "pm_server_register_match",
    "pm_server_register_permission_ok",
    "pm_server_register_constructed",
    "pm_server_register_state_read",
    "pm_server_register_add_client_call",
    "pm_server_register_after_add_client",
    "pm_server_register_success_return",
    "pm_server_register_ret",
)

CNSS_BLOCKING_ABSENT = SERVER_SEQUENCE[1:]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = display_path(path)
    return payload


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def nested(payload: dict[str, Any], *keys: str) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def sum_label(hits_by_comm: dict[str, Any], label: str) -> int:
    total = 0
    for labels in hits_by_comm.values():
        if isinstance(labels, dict):
            total += intish(labels.get(label))
    return total


def collect() -> dict[str, Any]:
    v1101 = load_json(INPUTS["v1101"])
    v1766 = load_json(INPUTS["v1766"])
    v1767 = load_json(INPUTS["v1767"])
    v1101_report = read_text(INPUTS["v1101_report"])

    trace = nested(v1101, "analysis", "tracefs_uprobe") or {}
    by_comm = trace.get("by_comm") or {}
    cnss_hits = trace.get("cnss_server_register_hits_by_comm") or {}
    returns = trace.get("return_values_by_comm") or {}
    cnss_comms = trace.get("cnss_server_register_comms") or []
    client_args = trace.get("client_register_args_by_comm") or {}

    positive_comm = ""
    positive_hits: dict[str, Any] = {}
    for comm, labels in by_comm.items():
        if isinstance(labels, dict) and intish(labels.get("pm_server_register_ret")) > 0:
            positive_comm = str(comm)
            positive_hits = labels
            break

    cnss_labels_total = {label: sum_label(cnss_hits, label) for label in SERVER_SEQUENCE}
    positive_labels = {label: intish(positive_hits.get(label)) for label in SERVER_SEQUENCE}
    absent_after_entry = all(cnss_labels_total.get(label, 0) == 0 for label in CNSS_BLOCKING_ABSENT)

    facts = {
        "v1766_request_trigger_gap_suspended": v1766.get("decision")
        == "v1766-request-trigger-gap-identified-live-gate-suspended-host-pass"
        and boolish(v1766.get("pass")),
        "v1767_pm_contract_extracted": v1767.get("decision")
        == "v1767-pm-contract-extracted-live-suspended-host-pass"
        and boolish(v1767.get("pass")),
        "v1101_pass": v1101.get("decision") == "v1101-cnss-server-register-no-return-at-pm_server_register_entry"
        and boolish(v1101.get("pass")),
        "tracefs_uprobe_pass": trace.get("result") == "tracefs-uprobe-pass",
        "cnss_client_register_args_corrected": "peripheral=\"modem\"" in v1101_report
        and "client=\"cnss-daemon\"" in v1101_report,
        "cnss_server_register_comms": cnss_comms,
        "cnss_server_register_entry_count": cnss_labels_total["pm_server_register_entry"],
        "cnss_server_register_match_count": cnss_labels_total["pm_server_register_match"],
        "cnss_server_register_ret_count": cnss_labels_total["pm_server_register_ret"],
        "cnss_absent_after_entry": absent_after_entry,
        "positive_control_comm": positive_comm,
        "positive_control_sequence_complete": all(positive_labels.get(label, 0) > 0 for label in SERVER_SEQUENCE),
        "positive_control_register_ret_values": (returns.get(positive_comm) or {}).get("pm_server_register_ret", []),
        "positive_control_connect_ret_values": (returns.get(positive_comm) or {}).get("pm_server_connect_ret", []),
        "pm_proxy_client_register_return": (returns.get("pm-proxy") or {}).get("pm_client_register_ret", []),
        "cnss_client_register_return": (returns.get("cnss-daemon") or {}).get("pm_client_register_ret", []),
        "cnss_client_register_args": client_args.get("cnss-daemon") or [],
        "pm_proxy_client_register_args": client_args.get("pm-proxy") or [],
        "server_offsets": {
            "entry": "0x6048",
            "match": "0x60cc",
            "permission_ok": "0x60e8",
            "constructed": "0x6104",
            "state_read": "0x6110",
            "add_client_call": "0x611c",
            "after_add_client": "0x6124",
            "success_return": "0x6140",
            "no_peripheral": "0x6148",
        },
    }
    return {
        "inputs": {"v1101": v1101, "v1766": v1766, "v1767": v1767},
        "facts": facts,
        "cnss_labels_total": cnss_labels_total,
        "positive_labels": positive_labels,
    }


def classify(facts: dict[str, Any]) -> tuple[str, bool, str, str]:
    required = (
        "v1766_request_trigger_gap_suspended",
        "v1767_pm_contract_extracted",
        "v1101_pass",
        "tracefs_uprobe_pass",
        "cnss_client_register_args_corrected",
    )
    missing = [key for key in required if not facts.get(key)]
    if missing:
        return (
            "v1768-pm-server-branch-input-incomplete",
            False,
            "missing retained evidence: " + ",".join(missing),
            "pm-server-branch-input-incomplete",
        )
    if facts["cnss_server_register_entry_count"] <= 0:
        return (
            "v1768-cnss-server-register-entry-missing",
            False,
            "cnss-daemon client register did not reach pm-service server register entry in retained evidence",
            "cnss-server-register-entry-missing",
        )
    if not facts["positive_control_sequence_complete"]:
        return (
            "v1768-positive-control-register-path-incomplete",
            False,
            "pm-proxy positive-control path did not complete the server register sequence",
            "positive-control-incomplete",
        )
    if facts["cnss_absent_after_entry"]:
        return (
            "v1768-pm-server-register-entry-only-before-match-host-pass",
            True,
            "cnss-daemon reaches pm-service register entry but no supported-peripheral match, permission, state, add-client, or return checkpoint",
            "pm-server-register-entry-only-before-match",
        )
    if facts["cnss_server_register_match_count"] > 0 and facts["cnss_server_register_ret_count"] <= 0:
        return (
            "v1768-pm-server-register-post-match-no-return-host-pass",
            True,
            "cnss-daemon reaches pm-service supported-peripheral match but no server register return",
            "pm-server-register-post-match-no-return",
        )
    return (
        "v1768-pm-server-register-branch-advanced-host-pass",
        True,
        "cnss-daemon server register branch has advanced past the retained V1101 entry-only boundary",
        "pm-server-register-branch-advanced",
    )


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    return "\n".join(
        [
            "# Native Init V1768 WLAN-PD PM Server Branch Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1768`",
            "- Type: host-only PM server branch classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Inputs",
            "",
            f"- V1101 tracefs live manifest: `{result['inputs']['v1101']}`",
            f"- V1101 tracefs report: `{result['inputs']['v1101_report']}`",
            f"- V1766 request-trigger classifier: `{result['inputs']['v1766']}`",
            f"- V1767 PM contract extraction: `{result['inputs']['v1767']}`",
            "",
            "## Facts",
            "",
            f"- V1766 request-trigger gap live-suspended: `{facts['v1766_request_trigger_gap_suspended']}`",
            f"- V1767 PM contract extracted: `{facts['v1767_pm_contract_extracted']}`",
            f"- V1101 tracefs result: `{facts['tracefs_uprobe_pass']}`",
            f"- Corrected CNSS client args documented: `{facts['cnss_client_register_args_corrected']}`",
            f"- CNSS server register comms: `{facts['cnss_server_register_comms']}`",
            f"- CNSS entry / match / return counts: `{facts['cnss_server_register_entry_count']}` / `{facts['cnss_server_register_match_count']}` / `{facts['cnss_server_register_ret_count']}`",
            f"- CNSS absent after entry: `{facts['cnss_absent_after_entry']}`",
            f"- Positive-control comm: `{facts['positive_control_comm']}`",
            f"- Positive-control sequence complete: `{facts['positive_control_sequence_complete']}`",
            f"- Positive-control register/connect return: `{facts['positive_control_register_ret_values']}` / `{facts['positive_control_connect_ret_values']}`",
            f"- CNSS client register return: `{facts['cnss_client_register_return']}`",
            "",
            "## Server Branch Boundary",
            "",
            "| checkpoint | offset | positive control | cnss-daemon |",
            "| --- | --- | ---: | ---: |",
            f"| entry | `{facts['server_offsets']['entry']}` | `{result['positive_labels']['pm_server_register_entry']}` | `{result['cnss_labels_total']['pm_server_register_entry']}` |",
            f"| supported-peripheral match | `{facts['server_offsets']['match']}` | `{result['positive_labels']['pm_server_register_match']}` | `{result['cnss_labels_total']['pm_server_register_match']}` |",
            f"| permission ok | `{facts['server_offsets']['permission_ok']}` | `{result['positive_labels']['pm_server_register_permission_ok']}` | `{result['cnss_labels_total']['pm_server_register_permission_ok']}` |",
            f"| state read | `{facts['server_offsets']['state_read']}` | `{result['positive_labels']['pm_server_register_state_read']}` | `{result['cnss_labels_total']['pm_server_register_state_read']}` |",
            f"| add-client call | `{facts['server_offsets']['add_client_call']}` | `{result['positive_labels']['pm_server_register_add_client_call']}` | `{result['cnss_labels_total']['pm_server_register_add_client_call']}` |",
            f"| success return | `{facts['server_offsets']['success_return']}` | `{result['positive_labels']['pm_server_register_success_return']}` | `{result['cnss_labels_total']['pm_server_register_success_return']}` |",
            f"| function return | `entry retprobe` | `{result['positive_labels']['pm_server_register_ret']}` | `{result['cnss_labels_total']['pm_server_register_ret']}` |",
            "",
            "## Interpretation",
            "",
            "- The positive-control `pm-proxy` path proves the provider, Binder service, and traced register implementation can complete in this boot/runtime shape.",
            "- The CNSS path reaches the same `pm-service` register implementation entry but stops before `0x60cc`, the first retained supported-peripheral match checkpoint.",
            "- This keeps the active request gap before PM register/vote success and before any `wlanmdsp.mbn` firmware request.",
            "- The next aligned work, while live PM gates remain suspended, is host/source-only disassembly of `pm-service+0x6048..0x60cc`.",
            "",
            "## Host-only Next Targets",
            "",
            "- String argument access/conversion between entry and `0x60cc`.",
            "- Supported peripheral list iteration and comparison setup.",
            "- Early Binder caller/process/context checks before the permission checkpoint.",
            "- Any blocking call or mutex taken only by the CNSS Binder server thread before `0x60cc`.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
            "## Next",
            "",
            "- Continue with host/source-only `pm-service` branch disassembly before `0x60cc`.",
            "- Do not deploy/live-run a service-object or PM actor helper unless a new directive explicitly reopens that narrow gate.",
            "- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    EvidenceStore(args.out_dir)
    collected = collect()
    decision, passed, reason, label = classify(collected["facts"])
    manifest = {
        "cycle": "V1768",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": collected["facts"],
        "cnss_labels_total": collected["cnss_labels_total"],
        "positive_labels": collected["positive_labels"],
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "pm_actor_start_executed": False,
        "qcacld_load_executed": False,
        "esoc_rc1_executed": False,
        "restart_pd_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
        "bpf_attach_executed": False,
        "tracefs_write_executed": False,
    }
    write_private_text(args.out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(manifest))
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
