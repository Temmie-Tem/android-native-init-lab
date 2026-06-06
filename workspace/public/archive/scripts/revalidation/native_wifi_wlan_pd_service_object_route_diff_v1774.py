#!/usr/bin/env python3
"""V1774 host-only diff for the WLAN-PD service-object PM route.

V1773 fixed the V1772 result as a provider-registration/lifetime gap.  This
classifier compares the failed V1772 service-object route with the retained
provider-positive V1092 PM observer route and checks the helper source for the
concrete route delta.

No device command is executed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1774-wlan-pd-service-object-route-diff"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1774_WLAN_PD_SERVICE_OBJECT_ROUTE_DIFF_2026-06-03.md"
)

INPUTS = {
    "v1772": REPO_ROOT / "tmp" / "wifi" / "v1772-wlan-pd-service-object-visible-handoff" / "manifest.json",
    "v1772_evidence": REPO_ROOT / "tmp" / "wifi" / "v1772-wlan-pd-service-object-visible-handoff",
    "v1773": REPO_ROOT / "tmp" / "wifi" / "v1773-wlan-pd-service-object-route-gap-classifier" / "manifest.json",
    "v1092": REPO_ROOT / "tmp" / "wifi" / "v1092-pm-observer-provider-ready-live" / "manifest.json",
    "helper_source": REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c",
}

SHUTDOWN_PROP = "vendor.peripheral.shutdown_critical_list"


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


def parse_key_value_lines(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    return fields


def nested(payload: dict[str, Any], *keys: str) -> Any:
    cur: Any = payload
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def request_values(fields: dict[str, str], prefix: str, prop_name: str) -> list[str]:
    values: list[str] = []
    for key, value in fields.items():
        if not key.startswith(prefix) or not key.endswith(".name") or value != prop_name:
            continue
        base = key[: -len(".name")]
        values.append(fields.get(base + ".value", ""))
    return values


def source_flags(source: str) -> dict[str, Any]:
    property_contract_expr = (
        "const bool peripheral_manager_property_contract =\n"
        "        is_wifi_companion_peripheral_manager_property_contract_start_only_mode(cfg->mode) ||\n"
        "        peripheral_manager_init_contract;"
    )
    allow_expr = (
        "bool allow_peripheral_shutdown_list =\n"
        "            is_wifi_companion_peripheral_manager_property_contract_start_only_mode(cfg->mode) ||\n"
        "            is_wifi_companion_pm_observer_any_mode(cfg->mode) ||\n"
        "            is_wifi_companion_mdm_helper_runtime_any_mode(cfg->mode) ||"
    )
    return {
        "service_object_mode_exists": "wlan_pd_service_object_visible_trigger" in source,
        "property_contract_expr_present": property_contract_expr in source,
        "allow_expr_present": allow_expr in source,
        "service_object_in_property_contract_expr": (
            "wlan_pd_service_object_visible_trigger" in source[
                source.find("const bool peripheral_manager_property_contract =") :
                source.find("const bool peripheral_manager_node_parity =")
            ]
        ),
        "service_object_in_allow_shutdown_expr": (
            "wlan_pd_service_object_visible_trigger" in source[
                source.find("bool allow_peripheral_shutdown_list =") :
                source.find("close(pipe_fds[0]);", source.find("bool allow_peripheral_shutdown_list ="))
            ]
        ),
    }


def collect() -> dict[str, Any]:
    data = {name: load_json(path) for name, path in INPUTS.items() if name not in {"v1772_evidence", "helper_source"}}
    v1772_fields = parse_key_value_lines(
        read_text(INPUTS["v1772_evidence"] / "test-v1393-helper-result.stdout.txt")
    )
    v1092_helper = nested(data["v1092"], "analysis", "helper") or {}
    v1092_property = v1092_helper.get("property_service_shim") or {}
    v1092_contract = v1092_helper.get("contract") or {}
    source = read_text(INPUTS["helper_source"])

    v1772_prefix = "wifi_hal_composite_start.property_service_shim."
    v1092_prefix = "wifi_hal_composite_start.property_service_shim."
    facts = {
        "v1773_route_gap_passed": data["v1773"].get("decision")
        == "v1773-provider-not-registered-after-per-mgr-clean-exit-host-pass"
        and boolish(data["v1773"].get("pass")),
        "v1772_service_object_live_passed": data["v1772"].get("decision")
        == "v1772-service-object-still-null-rollback-pass"
        and boolish(data["v1772"].get("pass")),
        "v1772_property_contract": boolish(
            v1772_fields.get("wifi_companion_start.peripheral_manager.property_contract")
        ),
        "v1772_init_contract": boolish(v1772_fields.get("wifi_companion_start.peripheral_manager.init_contract")),
        "v1772_allow_shutdown_list": boolish(v1772_fields.get(v1772_prefix + "allow_peripheral_shutdown_list")),
        "v1772_allowlist_has_shutdown_list": SHUTDOWN_PROP in v1772_fields.get(v1772_prefix + "allowlist", ""),
        "v1772_shutdown_values": request_values(v1772_fields, v1772_prefix, SHUTDOWN_PROP),
        "v1772_provider_seen": boolish(v1772_fields.get("wlan_pd_service_object_visible_trigger.provider_seen")),
        "v1772_after_per_mgr_query_exit_zero": v1772_fields.get(
            "wifi_vndservice_query.wlan_pd_service_object_visible_after_per_mgr.result"
        )
        == "query-exit-zero",
        "v1772_pm_proxy_helper_clean_exit": boolish(
            v1772_fields.get("wifi_companion_start.child.pm_proxy_helper.exited")
        )
        and v1772_fields.get("wifi_companion_start.child.pm_proxy_helper.exit_code") == "0",
        "v1772_per_mgr_clean_exit": boolish(v1772_fields.get("wifi_companion_start.child.per_mgr.exited"))
        and v1772_fields.get("wifi_companion_start.child.per_mgr.exit_code") == "0",
        "v1092_provider_positive": data["v1092"].get("decision") == "v1092-pm-provider-registration-observed"
        and boolish(data["v1092"].get("pass")),
        "v1092_property_shim_started": boolish(v1092_property.get(v1092_prefix + "started")),
        "v1092_allow_shutdown_list": boolish(v1092_property.get(v1092_prefix + "allow_peripheral_shutdown_list")),
        "v1092_allowlist_has_shutdown_list": SHUTDOWN_PROP in str(v1092_property.get(v1092_prefix + "allowlist", "")),
        "v1092_shutdown_values": request_values(v1092_property, v1092_prefix, SHUTDOWN_PROP),
        "v1092_after_per_mgr_provider_seen": boolish(
            (v1092_helper.get("vndservice_query") or {}).get(
                "wifi_vndservice_query.pm_observer_after_per_mgr_probe.vendor_qcom_peripheral_manager_seen"
            )
        ),
        "v1092_order_has_after_per_mgr_probe_before_per_proxy": "per_mgr,vndservice_query,per_proxy"
        in str(v1092_contract.get("order", "")),
    }
    observations = {
        "v1772_allowlist": v1772_fields.get(v1772_prefix + "allowlist", ""),
        "v1092_allowlist": v1092_property.get(v1092_prefix + "allowlist", ""),
        "v1772_order": v1772_fields.get("wifi_companion_start.order", ""),
        "v1092_order": v1092_contract.get("order", ""),
        "source_flags": source_flags(source),
    }
    return {"inputs": data, "facts": facts, "observations": observations}


def classify(facts: dict[str, Any], observations: dict[str, Any]) -> tuple[str, bool, str, str]:
    required = (
        "v1773_route_gap_passed",
        "v1772_service_object_live_passed",
        "v1772_after_per_mgr_query_exit_zero",
        "v1772_pm_proxy_helper_clean_exit",
        "v1772_per_mgr_clean_exit",
        "v1092_provider_positive",
        "v1092_property_shim_started",
        "v1092_allow_shutdown_list",
        "v1092_allowlist_has_shutdown_list",
        "v1092_after_per_mgr_provider_seen",
        "v1092_order_has_after_per_mgr_probe_before_per_proxy",
    )
    missing = [key for key in required if not facts.get(key)]
    if missing:
        return (
            "v1774-route-diff-input-incomplete",
            False,
            "missing required retained evidence: " + ",".join(missing),
            "route-diff-input-incomplete",
        )
    source = observations["source_flags"]
    if not (source["property_contract_expr_present"] and source["allow_expr_present"]):
        return (
            "v1774-helper-source-contract-expression-missing",
            False,
            "helper source no longer matches the retained property-contract expressions",
            "helper-source-contract-expression-missing",
        )
    if (
        not facts["v1772_property_contract"]
        and not facts["v1772_allow_shutdown_list"]
        and not facts["v1772_allowlist_has_shutdown_list"]
        and not facts["v1772_shutdown_values"]
        and not source["service_object_in_property_contract_expr"]
        and not source["service_object_in_allow_shutdown_expr"]
    ):
        return (
            "v1774-service-object-route-lacks-pm-property-contract-host-pass",
            True,
            "V1772 service-object route omitted the PM property/shutdown-critical-list contract that the V1092 provider-positive route used before provider registration",
            "service-object-route-lacks-pm-property-contract",
        )
    return (
        "v1774-property-contract-gap-not-proven",
        False,
        "retained evidence does not prove the service-object route lacks the PM property contract",
        "property-contract-gap-not-proven",
    )


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    obs = result["observations"]
    source = obs["source_flags"]
    return "\n".join(
        [
            "# Native Init V1774 WLAN-PD Service-object Route Diff",
            "",
            "## Summary",
            "",
            "- Cycle: `V1774`",
            "- Type: host-only route/source diff classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Diff Result",
            "",
            "- The failed V1772 service-object route did not enable the PM property contract.",
            "- The provider-positive V1092 route did enable `vendor.peripheral.shutdown_critical_list` handling.",
            "- Source inspection shows `wlan_pd_service_object_visible_trigger` is not included in either the `peripheral_manager_property_contract` expression or the property-shim `allow_peripheral_shutdown_list` expression.",
            "- Therefore the next source/build repair target is narrow: include the V1772 service-object route in the same PM property/shutdown-critical-list contract surface, without adding `per_proxy`, eSoC, RC1, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
            "",
            "## V1772 Failed Route",
            "",
            f"- Property contract flag: `{facts['v1772_property_contract']}`",
            f"- Init contract flag: `{facts['v1772_init_contract']}`",
            f"- Property shim allows shutdown list: `{facts['v1772_allow_shutdown_list']}`",
            f"- Allowlist contains `{SHUTDOWN_PROP}`: `{facts['v1772_allowlist_has_shutdown_list']}`",
            f"- Shutdown-list values observed: `{facts['v1772_shutdown_values']}`",
            f"- Provider seen: `{facts['v1772_provider_seen']}`",
            f"- `pm_proxy_helper` / `pm-service` clean exits: `{facts['v1772_pm_proxy_helper_clean_exit']}` / `{facts['v1772_per_mgr_clean_exit']}`",
            f"- Order: `{obs['v1772_order']}`",
            f"- Allowlist: `{obs['v1772_allowlist']}`",
            "",
            "## V1092 Positive Control",
            "",
            f"- Provider-positive control: `{facts['v1092_provider_positive']}`",
            f"- Property shim started: `{facts['v1092_property_shim_started']}`",
            f"- Property shim allows shutdown list: `{facts['v1092_allow_shutdown_list']}`",
            f"- Allowlist contains `{SHUTDOWN_PROP}`: `{facts['v1092_allowlist_has_shutdown_list']}`",
            f"- Shutdown-list values observed: `{facts['v1092_shutdown_values']}`",
            f"- Provider seen after `per_mgr`: `{facts['v1092_after_per_mgr_provider_seen']}`",
            f"- After-`per_mgr` query before `per_proxy`: `{facts['v1092_order_has_after_per_mgr_probe_before_per_proxy']}`",
            f"- Order: `{obs['v1092_order']}`",
            f"- Allowlist: `{obs['v1092_allowlist']}`",
            "",
            "## Source Check",
            "",
            f"- Service-object mode exists: `{source['service_object_mode_exists']}`",
            f"- Property-contract expression present: `{source['property_contract_expr_present']}`",
            f"- Shutdown-list allow expression present: `{source['allow_expr_present']}`",
            f"- Service-object mode included in property-contract expression: `{source['service_object_in_property_contract_expr']}`",
            f"- Service-object mode included in shutdown-list allow expression: `{source['service_object_in_allow_shutdown_expr']}`",
            "",
            "## Next",
            "",
            "- Source/build-only: patch `a90_android_execns_probe.c` so `wlan_pd_service_object_visible_trigger` enables the PM property/shutdown-critical-list contract used by V1092.",
            "- Keep the live route bounded: no full `per_proxy`, no `/dev/subsys_esoc0`, no forced RC1, no fake-ONLINE, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping.",
            "- After source/build validation, a separate rollbackable live gate can test only whether the provider becomes visible and whether CNSS reaches `asInterface` / register-TX / `wlanmdsp` request.",
            "",
            "## Safety",
            "",
            "- This unit is host-only and retained-evidence/source-only.",
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
    decision, passed, reason, label = classify(collected["facts"], collected["observations"])
    manifest = {
        "cycle": "V1774",
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
