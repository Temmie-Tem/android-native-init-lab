#!/usr/bin/env python3
"""V1767 host-only WLAN-PD PeripheralManager contract extraction.

This classifier extracts the narrow PM/service-object contract from retained
evidence without contacting the device.  It is the safe follow-up to V1766:
live PM/helper gates remain suspended, but the next live gate can be made more
precise if the contract is written down first.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1767-wlan-pd-pm-contract-extraction"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1767_WLAN_PD_PM_CONTRACT_EXTRACTION_2026-06-03.md"
)

INPUTS = {
    "v1087": REPO_ROOT / "tmp" / "wifi" / "v1087-pm-addservice-host-classifier" / "manifest.json",
    "v1092": REPO_ROOT / "tmp" / "wifi" / "v1092-pm-observer-provider-ready-live" / "manifest.json",
    "v1095": REPO_ROOT / "tmp" / "wifi" / "v1095-pm-cnss-voter-surface-live" / "manifest.json",
    "v1101": REPO_ROOT / "tmp" / "wifi" / "v1101-pm-server-register-path-tracefs-live" / "manifest.json",
    "v1757_report": REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1757_WLAN_PD_PERIPHERAL_INTERFACE_BRANCH_CLASSIFIER_2026-06-03.md",
    "v1758": REPO_ROOT / "tmp" / "wifi" / "v1758-wlan-pd-provider-visibility-contract-classifier" / "manifest.json",
    "v1761": REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier" / "manifest.json",
    "v1764": REPO_ROOT / "tmp" / "wifi" / "v1764-wlan-pd-service-object-visible-helper-build" / "manifest.json",
    "v1765_report": REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1765_WLAN_PD_FIRMWARE_REQUEST_DIRECTIVE_AUDIT_2026-06-03.md",
    "v1766": REPO_ROOT / "tmp" / "wifi" / "v1766-wlan-pd-request-trigger-directive-classifier" / "manifest.json",
}


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


def collect() -> dict[str, Any]:
    data = {name: load_json(path) for name, path in INPUTS.items() if name.endswith(("v1087", "v1092", "v1095", "v1101", "v1758", "v1761", "v1764", "v1766"))}
    v1757_text = read_text(INPUTS["v1757_report"])
    v1765_text = read_text(INPUTS["v1765_report"])

    v1761_facts = data["v1761"].get("facts") or {}
    v1766_facts = data["v1766"].get("facts") or {}
    v1101_server = nested(data["v1101"], "result", "cnss_server_register_hits_by_comm") or {}
    v1101_reason = str(data["v1101"].get("reason") or "")

    facts = {
        "policy_readiness_delta_classified": data["v1087"].get("decision")
        == "v1087-addservice-readiness-policy-delta-classified"
        and boolish(data["v1087"].get("pass")),
        "provider_registration_observed": data["v1092"].get("decision") == "v1092-pm-provider-registration-observed"
        and boolish(data["v1092"].get("pass")),
        "vndservicemanager_ready_observed": boolish(data["v1092"].get("vndservicemanager_ready")),
        "provider_positive_cnss_window_observed": data["v1095"].get("decision")
        == "v1095-cnss-voter-no-pm-fd-mdm3-still-offline"
        and boolish(data["v1095"].get("pass")),
        "cnss_server_register_entry_observed": data["v1101"].get("decision")
        == "v1101-cnss-server-register-no-return-at-pm_server_register_entry"
        and boolish(data["v1101"].get("pass")),
        "cnss_server_register_entry_only": "pm_server_register_entry" in v1101_reason
        or any("pm_server_register_entry" in str(comm_hits) for comm_hits in v1101_server.values()),
        "v1757_static_null_branch": "cbz x8" in v1757_text
        and "vendor.qcom.PeripheralManager" in v1757_text
        and "peripheral-manager-service-object-null" in v1757_text,
        "native_pm_null_branch": boolish(v1761_facts.get("native_pm_null_peripheral_branch")),
        "native_as_interface_reached": boolish(v1761_facts.get("native_periph_as_interface_call")),
        "native_register_tx_reached": boolish(v1761_facts.get("native_periph_manager_register_tx_call")),
        "native_requested_wlanmdsp": boolish(v1766_facts.get("native_requested_wlanmdsp")),
        "android_pm_vote_before_request": boolish(v1766_facts.get("android_pm_vote_seen")),
        "android_wlanmdsp_request_seen": boolish(v1766_facts.get("android_wlanmdsp_request_seen")),
        "v1764_dormant_artifact_available": boolish(v1766_facts.get("v1764_dormant_artifact_available")),
        "active_stop_suspends_live_pm": "Do not deploy or live-run the V1764 service-object-visible helper" in v1765_text,
    }
    return {"inputs": data, "facts": facts}


def classify(facts: dict[str, Any]) -> tuple[str, bool, str, str]:
    required = (
        "policy_readiness_delta_classified",
        "provider_registration_observed",
        "vndservicemanager_ready_observed",
        "v1757_static_null_branch",
        "native_pm_null_branch",
        "android_pm_vote_before_request",
        "android_wlanmdsp_request_seen",
        "v1764_dormant_artifact_available",
    )
    missing = [key for key in required if not facts.get(key)]
    if missing:
        return (
            "v1767-pm-contract-input-incomplete",
            False,
            "missing required retained evidence: " + ",".join(missing),
            "pm-contract-input-incomplete",
        )
    if facts["active_stop_suspends_live_pm"]:
        return (
            "v1767-pm-contract-extracted-live-suspended-host-pass",
            True,
            "narrow PM contract extracted; live service-object/register discriminator remains suspended by current stop directive",
            "pm-contract-extracted-live-suspended",
        )
    return (
        "v1767-pm-contract-extracted-live-eligible-host-pass",
        True,
        "narrow PM contract extracted; live discriminator would still need explicit gate scope",
        "pm-contract-extracted-live-eligible",
    )


def render_report(result: dict[str, Any]) -> str:
    facts = result["facts"]
    return "\n".join(
        [
            "# Native Init V1767 WLAN-PD PM Contract Extraction",
            "",
            "## Summary",
            "",
            "- Cycle: `V1767`",
            "- Type: host-only PeripheralManager contract extraction",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Extracted Contract",
            "",
            "The next narrow live discriminator, if explicitly reopened, must prove this ordered contract before any Wi-Fi connection work:",
            "",
            "1. Current-boot SELinux/policy-load and service-manager namespace are valid for `vendor_per_mgr`.",
            "2. `vndservicemanager` is started and explicitly ready.",
            "3. `/vendor/bin/pm-service` registers `vendor.qcom.PeripheralManager`.",
            "4. `/vendor/bin/vndservice list` sees `vendor.qcom.PeripheralManager` in the same namespace used by `cnss-daemon`.",
            "5. `cnss-daemon` `libperipheral_client.so` lookup returns a non-null service object.",
            "6. `IPeripheralManager::asInterface` and manager-register transaction are reached.",
            "7. PM register/vote returns or reaches the server-side post-entry checkpoints.",
            "8. Only then measure `requested_wlanmdsp`, WLFW service 69, and `wlan0`.",
            "",
            "## Facts",
            "",
            f"- V1087 policy/readiness delta classified: `{facts['policy_readiness_delta_classified']}`",
            f"- V1092 provider registration observed: `{facts['provider_registration_observed']}`",
            f"- V1092 `vndservicemanager` readiness observed: `{facts['vndservicemanager_ready_observed']}`",
            f"- V1095 provider-positive CNSS window observed: `{facts['provider_positive_cnss_window_observed']}`",
            f"- V1101 CNSS server register entry observed: `{facts['cnss_server_register_entry_observed']}`",
            f"- V1101 server register entry only: `{facts['cnss_server_register_entry_only']}`",
            f"- V1757 static null-service branch proven: `{facts['v1757_static_null_branch']}`",
            f"- Native PM null branch / `asInterface` / register TX: `{facts['native_pm_null_branch']}` / `{facts['native_as_interface_reached']}` / `{facts['native_register_tx_reached']}`",
            f"- Android PM vote before request / request seen: `{facts['android_pm_vote_before_request']}` / `{facts['android_wlanmdsp_request_seen']}`",
            f"- Native requested `wlanmdsp`: `{facts['native_requested_wlanmdsp']}`",
            f"- V1764 dormant artifact available: `{facts['v1764_dormant_artifact_available']}`",
            f"- Active stop suspends live PM helper gate: `{facts['active_stop_suspends_live_pm']}`",
            "",
            "## Classification",
            "",
            "- `provider_seen` alone is insufficient; V1095/V1101 show provider-positive windows can still leave `wlanmdsp.mbn` unrequested.",
            "- The decisive pre-request milestones are non-null service object, `asInterface`, manager-register TX/return, and PM vote/register success.",
            "- A future live gate should include labels that distinguish `provider-not-visible`, `service-object-null`, `register-tx-no-return`, `register-return-still-no-request`, and `request-progress`.",
            "- The current directive still suspends that live gate, so this unit stops at host/source-only contract extraction.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It performs no device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD load, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, or tracefs write.",
            "",
            "## Next",
            "",
            "- If the stop directive remains active: continue only host/source-only analysis of the PM register server-side branch after entry.",
            "- If the narrow live gate is explicitly reopened: deploy the dormant V1764-style helper only after adding the refined output labels above.",
            "- Do not proceed to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until `wlan0` exists and the user explicitly opens the active connection gate.",
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
        "cycle": "V1767",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": collected["facts"],
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
        "tracefs_write_executed": False,
    }
    write_private_text(args.out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(manifest))
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
