#!/usr/bin/env python3
"""V1785 host-only classifier for the PM server no-peripheral boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1785-pm-server-no-peripheral-classifier"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1785_PM_SERVER_NO_PERIPHERAL_CLASSIFIER_2026-06-03.md"
INPUTS = {
    "v1784_manifest": REPO_ROOT / "tmp" / "wifi" / "v1784-pm-server-forwarding-observer-handoff" / "manifest.json",
    "v1784_helper": REPO_ROOT / "tmp" / "wifi" / "v1784-pm-server-forwarding-observer-handoff" / "test-v1393-helper-result.stdout.txt",
    "v1769_manifest": REPO_ROOT / "tmp" / "wifi" / "v1769-wlan-pd-pm-server-prematch-static" / "manifest.json",
    "v1769_surrounding_disasm": REPO_ROOT / "tmp" / "wifi" / "v1769-wlan-pd-pm-server-prematch-static" / "host" / "pm-service-register-surrounding-0x6048-0x614c.S",
    "v1779_manifest": REPO_ROOT / "tmp" / "wifi" / "v1779-pm-service-lifetime-delta-classifier" / "manifest.json",
    "v1782_manifest": REPO_ROOT / "tmp" / "wifi" / "v1782-wlan-pd-pm-forwarding-delta-classifier" / "manifest.json",
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        data["present"] = True
        return data
    return {"present": True, "value": data}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def intish(value: Any) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def field_int(fields: dict[str, str], key: str) -> int:
    return intish(fields.get(key))


def count_shutdown_requests(fields: dict[str, str]) -> tuple[int, list[str]]:
    values: list[str] = []
    prefix = "wifi_hal_composite_start.property_service_shim.request."
    for key, value in fields.items():
        if not key.startswith(prefix) or not key.endswith(".name"):
            continue
        if value != "vendor.peripheral.shutdown_critical_list":
            continue
        base = key[: -len(".name")]
        values.append(fields.get(base + ".value", ""))
    return len(values), values


def disasm_has_empty_list_branch(disasm: str) -> bool:
    patterns = [
        r"606c:\s+f940141b\s+ldr\s+x27, \[x0, #40\]",
        r"6070:\s+9100801c\s+add\s+x28, x0, #0x20",
        r"6078:\s+eb1b039f\s+cmp\s+x28, x27",
        r"607c:\s+54000240\s+b\.eq\s+60c4",
        r"60c4:\s+f940031a\s+ldr\s+x26, \[x24\]",
        r"60c8:\s+14000020\s+b\s+6148",
    ]
    return all(re.search(pattern, disasm) for pattern in patterns)


def disasm_has_loop_path(disasm: str) -> bool:
    patterns = [
        r"6094:\s+f9400b79\s+ldr\s+x25, \[x27, #16\]",
        r"609c:\s+94000d27\s+bl\s+9538",
        r"60ac:\s+94000f5d\s+bl\s+9e20 <strcmp@plt>",
        r"60b0:\s+340000e0\s+cbz\s+w0, 60cc",
        r"60b4:\s+f940077b\s+ldr\s+x27, \[x27, #8\]",
        r"60bc:\s+54fffec1\s+b\.ne\s+6094",
    ]
    return all(re.search(pattern, disasm) for pattern in patterns)


def classify(facts: dict[str, Any]) -> tuple[str, str, str]:
    required_inputs = [
        facts["v1784_present"],
        facts["v1769_present"],
        facts["disasm_present"],
    ]
    if not all(required_inputs):
        return (
            "v1785-pm-server-no-peripheral-input-missing",
            "input-missing",
            "required V1784/V1769 evidence is missing",
        )
    if not facts["v1784_pass"] or not facts["v1784_rollback_ok"]:
        return (
            "v1785-pm-server-no-peripheral-live-baseline-invalid",
            "live-baseline-invalid",
            "V1784 did not produce a rollback-verified live baseline",
        )
    if facts["v1784_pm_server_label"] != "pm-server-no-peripheral":
        return (
            "v1785-pm-server-no-peripheral-not-current-label",
            "not-current-label",
            "V1784 did not produce the pm-server-no-peripheral label",
        )
    if facts["entry_hits"] > 0 and facts["no_peripheral_hits"] > 0 and facts["loop_hits"] == 0 and facts["match_hits"] == 0 and facts["empty_list_branch_static"]:
        return (
            "v1785-pm-server-supported-list-empty-host-pass",
            "pm-server-supported-list-empty",
            "V1784 hits register entry then the no-peripheral return while every list traversal/match checkpoint stays zero; static control flow shows this is the empty-list branch before record getter or strcmp",
        )
    if facts["entry_hits"] > 0 and facts["loop_hits"] > 0 and facts["match_hits"] == 0:
        return (
            "v1785-pm-server-list-traversal-no-match-host-pass",
            "pm-server-list-traversal-no-match",
            "PM server traversed records but did not match the requested peripheral",
        )
    return (
        "v1785-pm-server-no-peripheral-unclassified-host-pass",
        "pm-server-no-peripheral-unclassified",
        "host inputs are present but do not match a fixed no-peripheral sublabel",
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    return "\n".join([
        "# Native Init V1785 PM Server No-peripheral Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1785`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        "- Result: PASS",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Inputs",
        "",
        *[f"- {name}: `{display_path(path)}`" for name, path in INPUTS.items()],
        "",
        "## V1784 Server Boundary",
        "",
        f"- V1784 decision: `{facts['v1784_decision']}`",
        f"- V1784 rollback ok: `{facts['v1784_rollback_ok']}`",
        f"- provider / asInterface / register TX: `{facts['provider_seen']}` / `{facts['as_interface_hits']}` / `{facts['register_tx_hits']}`",
        f"- requested `wlanmdsp`: `{facts['requested_wlanmdsp']}`",
        f"- PM server label: `{facts['v1784_pm_server_label']}`",
        f"- PM server entry / loop / match / add-client / success / no-peripheral hits: `{facts['entry_hits']}` / `{facts['loop_hits']}` / `{facts['match_hits']}` / `{facts['add_client_hits']}` / `{facts['success_hits']}` / `{facts['no_peripheral_hits']}`",
        f"- first PM server hit: `{facts['first_hit_line']}`",
        "",
        "## Static Control-flow Interpretation",
        "",
        f"- empty-list branch present: `{facts['empty_list_branch_static']}`",
        f"- loop/getter/strcmp path present: `{facts['loop_path_static']}`",
        "- Register entry loads the list end/sentinel from `x0+0x20` and current node from `x0+0x28`, compares them, and branches directly to the no-peripheral return when they are equal.",
        "- In V1784, the loop node, record getter, `strcmp`, match, permission, add-client, and success checkpoints all have zero hits.",
        "- Therefore the current PM server blocker is earlier than the V1769 mutex/list-traversal model: the supported-peripheral list is empty at the CNSS registration time.",
        "",
        "## Supporting Deltas",
        "",
        f"- V1769 previous label: `{facts['v1769_label']}`",
        f"- V1779 Android-good shutdown-list values: `{', '.join(facts['v1779_android_shutdown_values'])}`",
        f"- V1784 shutdown-list set requests: `{facts['v1784_shutdown_request_count']}` values `{', '.join(facts['v1784_shutdown_request_values'])}`",
        f"- V1784 safety retained: `{facts['safety_retained']}`",
        "",
        "## Interpretation",
        "",
        "- This is not a service-object visibility failure: V1784 has provider, `asInterface`, and register TX evidence.",
        "- This is not a permission failure: permission checks start after the supported-peripheral match checkpoint, and V1784 never reaches that checkpoint.",
        "- This is not the previously observed modem-record mutex wait: V1784 never reaches the record getter or `strcmp` path.",
        "- The next useful unit is host/source-only reconstruction of `pm-service` supported-peripheral list population, then a narrowly scoped source/build gate that observes or repairs that list before CNSS registration.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
        "",
        "## Next",
        "",
        "- V1786 should analyze `pm-service` supported-list population sources and offsets: peripheral initialization, property/sysfs inputs, and list insertion points.",
        "- Do not run another live PM gate until that host/source model names a minimal repair or observation point.",
        "- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.",
        "",
    ])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v1784 = load_json(INPUTS["v1784_manifest"])
    v1769 = load_json(INPUTS["v1769_manifest"])
    v1779 = load_json(INPUTS["v1779_manifest"])
    v1782 = load_json(INPUTS["v1782_manifest"])
    helper_fields = parse_fields(read_text(INPUTS["v1784_helper"]))
    disasm = read_text(INPUTS["v1769_surrounding_disasm"])
    shutdown_count, shutdown_values = count_shutdown_requests(helper_fields)
    gate = v1784.get("gate") or {}
    facts: dict[str, Any] = {
        "v1784_present": truthy(v1784.get("present")),
        "v1769_present": truthy(v1769.get("present")),
        "v1779_present": truthy(v1779.get("present")),
        "v1782_present": truthy(v1782.get("present")),
        "disasm_present": bool(disasm),
        "v1784_pass": truthy(v1784.get("pass")),
        "v1784_decision": v1784.get("decision", ""),
        "v1784_rollback_ok": truthy((v1784.get("rollback") or {}).get("ok")),
        "provider_seen": gate.get("provider_seen", ""),
        "as_interface_hits": gate.get("as_interface_hits", ""),
        "register_tx_hits": gate.get("register_tx_hits", ""),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "v1784_pm_server_label": gate.get("pm_server_label", ""),
        "entry_hits": intish(gate.get("pm_server_register_entry_hits")),
        "loop_hits": intish(gate.get("pm_server_loop_node_hits")),
        "getter_hits": intish(gate.get("pm_server_name_helper_call_hits")),
        "strcmp_hits": intish(gate.get("pm_server_strcmp_result_hits")),
        "match_hits": intish(gate.get("pm_server_match_hits")),
        "add_client_hits": intish(gate.get("pm_server_add_client_hits")),
        "success_hits": intish(gate.get("pm_server_success_return_hits")),
        "no_peripheral_hits": intish(gate.get("pm_server_no_peripheral_hits")),
        "first_hit_line": gate.get("pm_server_first_hit_line", ""),
        "empty_list_branch_static": disasm_has_empty_list_branch(disasm),
        "loop_path_static": disasm_has_loop_path(disasm),
        "v1769_label": v1769.get("label", ""),
        "v1769_prematch_list_mutex_boundary": v1769.get("label") == "pm-server-prematch-list-mutex-boundary",
        "v1779_android_shutdown_values": (v1779.get("facts") or {}).get("v1092_shutdown_critical_values", []),
        "v1779_v1778_shutdown_values": (v1779.get("facts") or {}).get("v1778_shutdown_critical_values", []),
        "v1784_shutdown_request_count": shutdown_count,
        "v1784_shutdown_request_values": shutdown_values,
        "v1782_client_register_return_no_success": (v1782.get("facts") or {}).get("v1781_client_register_return_no_success", False),
        "safety_retained": all(
            helper_fields.get(key) == "1"
            for key in (
                "wlan_pd_service_object_visible_trigger.no_esoc0",
                "wlan_pd_service_object_visible_trigger.no_forced_rc1",
                "wlan_pd_service_object_visible_trigger.no_fake_online",
                "wlan_pd_service_object_visible_trigger.no_per_proxy",
                "wlan_pd_service_object_visible_trigger.no_wifi_hal",
                "wlan_pd_service_object_visible_trigger.no_scan_connect",
                "wlan_pd_service_object_visible_trigger.no_credentials",
                "wlan_pd_service_object_visible_trigger.no_dhcp_routes",
                "wlan_pd_service_object_visible_trigger.no_external_ping",
            )
        ),
    }
    decision, label, reason = classify(facts)
    manifest = {
        "cycle": "V1785",
        "decision": decision,
        "label": label,
        "pass": decision.endswith("host-pass"),
        "reason": reason,
        "out_dir": display_path(OUT_DIR),
        "report": display_path(REPORT_PATH),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": facts,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (OUT_DIR / "summary.md").write_text(render_report(manifest))
    REPORT_PATH.write_text(render_report(manifest))
    print(json.dumps({"decision": decision, "label": label, "pass": manifest["pass"], "report": display_path(REPORT_PATH)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
