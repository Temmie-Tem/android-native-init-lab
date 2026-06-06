#!/usr/bin/env python3
"""V1773 host-only classifier for the V1772 service-object route gap.

V1772 reopened exactly one bounded PM discriminator, but the live run never made
`vendor.qcom.PeripheralManager` visible through `vndservice list`.  This unit
does not contact the device.  It reconciles V1772 against the provider-positive
V1092 control and the V1761/V1767 PM contract evidence so the next cycle stays
on the route/helper registration gap instead of treating V1772 as a modem
result.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1773-wlan-pd-service-object-route-gap-classifier"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1773_WLAN_PD_SERVICE_OBJECT_ROUTE_GAP_CLASSIFIER_2026-06-03.md"
)

INPUTS = {
    "v1772": REPO_ROOT / "tmp" / "wifi" / "v1772-wlan-pd-service-object-visible-handoff" / "manifest.json",
    "v1772_evidence": REPO_ROOT / "tmp" / "wifi" / "v1772-wlan-pd-service-object-visible-handoff",
    "v1092": REPO_ROOT / "tmp" / "wifi" / "v1092-pm-observer-provider-ready-live" / "manifest.json",
    "v1761": REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier" / "manifest.json",
    "v1767": REPO_ROOT / "tmp" / "wifi" / "v1767-wlan-pd-pm-contract-extraction" / "manifest.json",
    "v1101": REPO_ROOT / "tmp" / "wifi" / "v1101-pm-server-register-path-tracefs-live" / "manifest.json",
    "v1107": REPO_ROOT / "tmp" / "wifi" / "v1107-pm-server-mutex-owner-classifier" / "manifest.json",
}

SERVICE_NAME = "vendor.qcom.PeripheralManager"


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


def parse_key_value_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def vndservice_sections(text: str) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    marker_prefix = "A90_EXECNS_VNDSERVICE_QUERY_"
    marker_suffix = "_STDOUT_BEGIN"
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if marker_prefix not in line or marker_suffix not in line:
            index += 1
            continue
        marker_start = line.find(marker_prefix) + len(marker_prefix)
        marker_end = line.find(marker_suffix, marker_start)
        name = line[marker_start:marker_end]
        body: list[str] = []
        index += 1
        end_marker = f"A90_EXECNS_VNDSERVICE_QUERY_{name}_STDOUT_END"
        while index < len(lines) and end_marker not in lines[index]:
            body.append(lines[index])
            index += 1
        section_text = "\n".join(body)
        sections[name] = {
            "found_zero_services": "Found 0 services:" in section_text,
            "provider_seen": SERVICE_NAME in section_text,
            "line_count": len(body),
        }
        index += 1
    return sections


def collect() -> dict[str, Any]:
    data = {name: load_json(path) for name, path in INPUTS.items() if name != "v1772_evidence"}
    helper_text = read_text(INPUTS["v1772_evidence"] / "test-v1393-helper-result.stdout.txt")
    helper_fields = parse_key_value_lines(helper_text)
    sections = vndservice_sections(helper_text)

    v1092_helper = nested(data["v1092"], "analysis", "helper") or {}
    v1092_contract = v1092_helper.get("contract") or {}
    v1092_query = v1092_helper.get("vndservice_query") or {}
    v1761_facts = data["v1761"].get("facts") or {}
    v1767_facts = data["v1767"].get("facts") or {}

    facts = {
        "v1772_passed_rollbackable_live": data["v1772"].get("decision")
        == "v1772-service-object-still-null-rollback-pass"
        and boolish(data["v1772"].get("pass")),
        "v1772_trigger_label_provider_not_visible": helper_fields.get(
            "wlan_pd_service_object_visible_trigger.label"
        )
        == "provider-not-visible",
        "v1772_vndservicemanager_ready": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.vndservicemanager_ready")
        ),
        "v1772_pm_proxy_helper_ready": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.pm_proxy_helper_ready")
        ),
        "v1772_per_mgr_ready": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.per_mgr_ready")
        ),
        "v1772_provider_seen": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.provider_seen")
        ),
        "v1772_after_per_mgr_provider_seen": boolish(
            helper_fields.get(
                "wifi_vndservice_query.wlan_pd_service_object_visible_after_per_mgr.vendor_qcom_peripheral_manager_seen"
            )
        ),
        "v1772_after_per_mgr_query_exit_zero": helper_fields.get(
            "wifi_vndservice_query.wlan_pd_service_object_visible_after_per_mgr.result"
        )
        == "query-exit-zero",
        "v1772_ready_query_found_zero_services": bool(
            sections.get("wlan_pd_service_object_visible_vndservicemanager_ready", {}).get(
                "found_zero_services"
            )
        ),
        "v1772_after_per_mgr_query_found_zero_services": bool(
            sections.get("wlan_pd_service_object_visible_after_per_mgr", {}).get("found_zero_services")
        ),
        "v1772_pm_proxy_helper_clean_exit": boolish(
            helper_fields.get("wifi_companion_start.child.pm_proxy_helper.exited")
        )
        and intish(helper_fields.get("wifi_companion_start.child.pm_proxy_helper.exit_code")) == 0
        and intish(helper_fields.get("wifi_companion_start.child.pm_proxy_helper.signal")) == 0,
        "v1772_per_mgr_clean_exit": boolish(helper_fields.get("wifi_companion_start.child.per_mgr.exited"))
        and intish(helper_fields.get("wifi_companion_start.child.per_mgr.exit_code")) == 0
        and intish(helper_fields.get("wifi_companion_start.child.per_mgr.signal")) == 0,
        "v1772_wlfw_worker_reached": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.wlfw_start_seen")
        )
        and boolish(helper_fields.get("wlan_pd_service_object_visible_trigger.wlfw_service_request_seen")),
        "v1772_requested_wlanmdsp": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.requested_wlanmdsp")
        ),
        "v1772_wlfw_service69_seen": boolish(
            helper_fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen")
        ),
        "v1092_provider_positive_control": data["v1092"].get("decision")
        == "v1092-pm-provider-registration-observed"
        and boolish(data["v1092"].get("pass")),
        "v1092_after_per_mgr_provider_seen": boolish(
            v1092_query.get("wifi_vndservice_query.pm_observer_after_per_mgr_probe.vendor_qcom_peripheral_manager_seen")
        ),
        "v1092_after_per_mgr_query_exit_zero": v1092_query.get(
            "wifi_vndservice_query.pm_observer_after_per_mgr_probe.result"
        )
        == "query-exit-zero",
        "v1092_provider_before_per_proxy": boolish(v1092_helper.get("vndservice_provider_seen"))
        and str(v1092_contract.get("order", "")).find("per_mgr,vndservice_query,per_proxy") >= 0,
        "v1761_pm_service_object_gap": data["v1761"].get("label")
        == "pm-service-object-gap-before-wlanmdsp-request"
        and boolish(data["v1761"].get("pass"))
        and boolish(v1761_facts.get("native_pm_null_peripheral_branch"))
        and not boolish(v1761_facts.get("native_periph_as_interface_call"))
        and not boolish(v1761_facts.get("native_periph_manager_register_tx_call")),
        "v1767_pm_contract_extracted": data["v1767"].get("label")
        == "pm-contract-extracted-live-suspended"
        and boolish(data["v1767"].get("pass"))
        and boolish(v1767_facts.get("provider_registration_observed")),
        "v1101_pm_server_register_entry_observed": data["v1101"].get("decision")
        == "v1101-cnss-server-register-no-return-at-pm_server_register_entry"
        and boolish(data["v1101"].get("pass")),
        "v1107_mutex_owner_blocked_in_subsystem_get": data["v1107"].get("decision")
        == "v1107-modem-mutex-owner-blocked-in-subsystem-get"
        and boolish(data["v1107"].get("pass")),
    }

    observations = {
        "v1772_order": helper_fields.get("wifi_companion_start.order", ""),
        "v1092_order": v1092_contract.get("order", ""),
        "v1772_pm_proxy_helper_argv": helper_fields.get("wifi_companion_start.per_proxy_helper_argv", ""),
        "v1772_per_mgr_argv": helper_fields.get("wifi_companion_start.per_mgr_argv", ""),
        "v1772_sections": sections,
        "v1772_child_lifecycle": {
            "pm_proxy_helper_running": helper_fields.get(
                "wlan_pd_service_object_visible_trigger.pm_proxy_helper_running", ""
            ),
            "per_mgr_running": helper_fields.get("wlan_pd_service_object_visible_trigger.per_mgr_running", ""),
            "cnss_daemon_running": helper_fields.get(
                "wlan_pd_service_object_visible_trigger.cnss_daemon_running", ""
            ),
        },
    }
    return {"inputs": data, "facts": facts, "observations": observations}


def classify(facts: dict[str, Any]) -> tuple[str, bool, str, str]:
    required = (
        "v1772_passed_rollbackable_live",
        "v1772_trigger_label_provider_not_visible",
        "v1772_vndservicemanager_ready",
        "v1772_pm_proxy_helper_ready",
        "v1772_per_mgr_ready",
        "v1772_after_per_mgr_query_exit_zero",
        "v1772_ready_query_found_zero_services",
        "v1772_after_per_mgr_query_found_zero_services",
        "v1772_pm_proxy_helper_clean_exit",
        "v1772_per_mgr_clean_exit",
        "v1772_wlfw_worker_reached",
        "v1092_provider_positive_control",
        "v1092_after_per_mgr_provider_seen",
        "v1092_provider_before_per_proxy",
        "v1761_pm_service_object_gap",
        "v1767_pm_contract_extracted",
    )
    missing = [key for key in required if not facts.get(key)]
    if missing:
        return (
            "v1773-route-gap-input-incomplete",
            False,
            "missing required retained evidence: " + ",".join(missing),
            "route-gap-input-incomplete",
        )
    if facts["v1772_provider_seen"] or facts["v1772_after_per_mgr_provider_seen"]:
        return (
            "v1773-v1772-provider-visibility-contradiction",
            False,
            "V1772 helper fields claim provider visibility; do not classify as a registration gap",
            "provider-visibility-contradiction",
        )
    return (
        "v1773-provider-not-registered-after-per-mgr-clean-exit-host-pass",
        True,
        "V1772 made the service-object route ready enough to query vndservicemanager, but provider remained absent after per_mgr and both PM helper processes exited cleanly; V1092 proves provider registration can appear after per_mgr before per_proxy",
        "provider-not-registered-after-per-mgr-clean-exit",
    )


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    observations = result["observations"]
    sections = observations["v1772_sections"]
    return "\n".join(
        [
            "# Native Init V1773 WLAN-PD Service-object Route Gap Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1773`",
            "- Type: host-only retained-evidence classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Classification",
            "",
            "- V1772 is not a modem/WLAN-PD progress result.",
            "- It is a route/helper provider-registration gap: the PM actors reported ready, but `vendor.qcom.PeripheralManager` never appeared in `vndservicemanager`.",
            "- The next unit should compare V1772 route construction against the provider-positive V1092 route before any further live modem gate.",
            "",
            "## V1772 Observed State",
            "",
            f"- Rollbackable live PASS: `{facts['v1772_passed_rollbackable_live']}`",
            f"- Trigger label: `provider-not-visible` = `{facts['v1772_trigger_label_provider_not_visible']}`",
            f"- `vndservicemanager` / `pm_proxy_helper` / `per_mgr` ready: `{facts['v1772_vndservicemanager_ready']}` / `{facts['v1772_pm_proxy_helper_ready']}` / `{facts['v1772_per_mgr_ready']}`",
            f"- Provider seen after `per_mgr`: `{facts['v1772_after_per_mgr_provider_seen']}`",
            f"- Ready query empty / after-`per_mgr` query empty: `{facts['v1772_ready_query_found_zero_services']}` / `{facts['v1772_after_per_mgr_query_found_zero_services']}`",
            f"- `pm_proxy_helper` clean exit: `{facts['v1772_pm_proxy_helper_clean_exit']}`",
            f"- `per_mgr` clean exit: `{facts['v1772_per_mgr_clean_exit']}`",
            f"- WLFW worker reached: `{facts['v1772_wlfw_worker_reached']}`",
            f"- Requested `wlanmdsp` / WLFW service 69: `{facts['v1772_requested_wlanmdsp']}` / `{facts['v1772_wlfw_service69_seen']}`",
            f"- Child running at summary, `pm_proxy_helper` / `per_mgr` / `cnss-daemon`: `{observations['v1772_child_lifecycle']['pm_proxy_helper_running']}` / `{observations['v1772_child_lifecycle']['per_mgr_running']}` / `{observations['v1772_child_lifecycle']['cnss_daemon_running']}`",
            "",
            "## Positive Control",
            "",
            f"- V1092 provider registration observed: `{facts['v1092_provider_positive_control']}`",
            f"- V1092 provider seen after `per_mgr`: `{facts['v1092_after_per_mgr_provider_seen']}`",
            f"- V1092 provider appeared before `per_proxy`: `{facts['v1092_provider_before_per_proxy']}`",
            f"- V1092 order: `{observations['v1092_order']}`",
            f"- V1772 order: `{observations['v1772_order']}`",
            "",
            "## Contract Context",
            "",
            f"- V1761 service-object gap before `wlanmdsp`: `{facts['v1761_pm_service_object_gap']}`",
            f"- V1767 PM contract extracted: `{facts['v1767_pm_contract_extracted']}`",
            f"- V1101 PM server register entry observed: `{facts['v1101_pm_server_register_entry_observed']}`",
            f"- V1107 mutex owner blocked in `__subsystem_get`: `{facts['v1107_mutex_owner_blocked_in_subsystem_get']}`",
            "",
            "## V1772 `vndservice` Sections",
            "",
            f"- Ready section: `{sections.get('wlan_pd_service_object_visible_vndservicemanager_ready', {})}`",
            f"- After-`per_mgr` section: `{sections.get('wlan_pd_service_object_visible_after_per_mgr', {})}`",
            "",
            "## Next",
            "",
            "- Host/source-only: diff V1772 vs V1092 PM route setup, especially property shim, shutdown-critical allowlist, `pm-service` lifetime, child argv, service namespace, and post-start wait semantics.",
            "- Do not treat V1772 as proof that a non-null service object failed to cause a PM vote; the object never became visible.",
            "- Do not chain into functional `pm-service`, WLAN-PD-UP cascade, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping without a separate explicit gate.",
            "",
            "## Safety",
            "",
            "- This unit is host-only and retained-evidence-only.",
            "- No device command, flash, reboot, actor start, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, firmware write, partition write, PMIC/GPIO/GDSC write, eSoC action, PCI action, platform bind/unbind, or tracefs write was performed.",
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
        "cycle": "V1773",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": collected["facts"],
        "observations": collected["observations"],
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "actor_start_executed": False,
        "wifi_hal_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "firmware_write_executed": False,
        "partition_write_executed": False,
        "pmic_gpio_gdsc_write_executed": False,
        "esoc_executed": False,
        "pci_executed": False,
        "platform_bind_unbind_executed": False,
        "tracefs_write_executed": False,
    }
    write_private_text(args.out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(manifest))
    print(
        json.dumps(
            {
                "decision": decision,
                "pass": passed,
                "label": label,
                "out_dir": display_path(args.out_dir),
            },
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
