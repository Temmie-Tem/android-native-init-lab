#!/usr/bin/env python3
"""V1782 host-only classifier for V1781 PM forwarding delta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1782-wlan-pd-pm-forwarding-delta-classifier"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1782_WLAN_PD_PM_FORWARDING_DELTA_CLASSIFIER_2026-06-03.md"
)

INPUTS = {
    "v1781_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1781-service-object-vndservice-parity-handoff"
    / "manifest.json",
    "v1781_helper": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1781-service-object-vndservice-parity-handoff"
    / "test-v1393-helper-result.stdout.txt",
    "v1760_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1760-wlan-pd-request-trigger-surface-classifier"
    / "manifest.json",
    "v1761_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1761-wlan-pd-autoload-trigger-contract-classifier"
    / "manifest.json",
    "v1768_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1768-wlan-pd-pm-server-branch-classifier"
    / "manifest.json",
    "v1769_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1769-wlan-pd-pm-server-prematch-static"
    / "manifest.json",
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


def read_text_binary_safe(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or " " in key or key.startswith("A90_"):
            continue
        fields[key] = value.strip()
    return fields


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def hit(fields: dict[str, str], key: str) -> bool:
    return intish(fields.get(key)) > 0


def collect() -> dict[str, Any]:
    v1781 = load_json(INPUTS["v1781_manifest"])
    v1781_gate = v1781.get("gate") or {}
    v1781_text = read_text_binary_safe(INPUTS["v1781_helper"])
    v1781_fields = parse_fields(v1781_text)
    v1760 = load_json(INPUTS["v1760_manifest"])
    v1761 = load_json(INPUTS["v1761_manifest"])
    v1768 = load_json(INPUTS["v1768_manifest"])
    v1769 = load_json(INPUTS["v1769_manifest"])

    android_events = v1760.get("android", {}).get("events") or v1761.get("android_events") or {}
    facts = {
        "v1781_present": boolish(v1781.get("present")),
        "v1781_pass": boolish(v1781.get("pass")),
        "v1781_decision": v1781.get("decision"),
        "v1781_policy_load_result": v1781_gate.get("policy_load_result"),
        "v1781_per_mgr_state": v1781_gate.get("per_mgr_state"),
        "v1781_per_mgr_zombie": v1781_gate.get("per_mgr_zombie"),
        "v1781_per_mgr_ready": v1781_gate.get("per_mgr_ready"),
        "v1781_provider_seen": v1781_gate.get("provider_seen"),
        "v1781_as_interface_hits": v1781_gate.get("as_interface_hits"),
        "v1781_register_tx_hits": v1781_gate.get("register_tx_hits"),
        "v1781_success_path_hits": v1781_gate.get("success_path_hits"),
        "v1781_requested_wlanmdsp": v1781_gate.get("requested_wlanmdsp"),
        "v1781_wlfw_service69_seen": v1781_gate.get("wlfw_service69_seen"),
        "v1781_late_listener_state": v1781_gate.get("late_listener_state"),
        "v1781_no_per_proxy": v1781_gate.get("no_per_proxy"),
        "v1781_no_esoc0": v1781_gate.get("no_esoc0"),
        "v1781_no_scan_connect": v1781_gate.get("no_scan_connect"),
        "v1781_no_credentials": v1781_gate.get("no_credentials"),
        "v1781_no_dhcp_routes": v1781_gate.get("no_dhcp_routes"),
        "v1781_no_external_ping": v1781_gate.get("no_external_ping"),
        "v1781_pm_client_register_entry": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_pm_client_register_entry.hit_count",
        ),
        "v1781_register_connect_entry": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_pm_register_connect_entry.hit_count",
        ),
        "v1781_service_manager_get_call": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_service_manager_get_call.hit_count",
        ),
        "v1781_binder_present_check": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_binder_object_present_check.hit_count",
        ),
        "v1781_as_interface_call": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_as_interface_call.hit_count",
        ),
        "v1781_register_tx_call": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_call.hit_count",
        ),
        "v1781_register_tx_retcheck": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_manager_register_tx_retcheck.hit_count",
        ),
        "v1781_register_connect_return": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_pm_register_connect_return.hit_count",
        ),
        "v1781_client_register_common_return": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_pm_client_register_common_return.hit_count",
        ),
        "v1781_success_path": hit(
            v1781_fields,
            "wlan_pd_cnss_nonlog_control_flow.peripheral_uprobe.periph_success_path.hit_count",
        ),
        "android_per_mgr_register_seen": "per_mgr_register" in android_events,
        "android_per_mgr_vote_seen": "per_mgr_vote" in android_events,
        "android_wlanmdsp_request_seen": "wlanmdsp_request" in android_events
        or boolish(v1760.get("android", {}).get("requested_wlanmdsp")),
        "android_wlan_pd_up_seen": boolish(
            (v1761.get("facts") or {}).get("android_wlan_pd_up_seen")
        )
        or "wlan_pd_up" in (v1760.get("android", {}).get("dmesg_events") or {}),
        "v1761_prior_null_object_gap": v1761.get("label") == "pm-service-object-gap-before-wlanmdsp-request"
        and boolish(v1761.get("pass")),
        "v1768_server_entry_only_before_match": v1768.get("label")
        == "pm-server-register-entry-only-before-match"
        and boolish(v1768.get("pass")),
        "v1769_prematch_list_mutex_boundary": v1769.get("label")
        == "pm-server-prematch-list-mutex-boundary"
        and boolish(v1769.get("pass")),
    }

    facts["v1781_client_register_return_no_success"] = (
        facts["v1781_pm_client_register_entry"]
        and facts["v1781_register_connect_entry"]
        and facts["v1781_service_manager_get_call"]
        and facts["v1781_binder_present_check"]
        and facts["v1781_as_interface_call"]
        and facts["v1781_register_tx_call"]
        and facts["v1781_register_tx_retcheck"]
        and facts["v1781_register_connect_return"]
        and facts["v1781_client_register_common_return"]
        and not facts["v1781_success_path"]
    )
    facts["v1781_request_still_absent"] = (
        str(facts["v1781_requested_wlanmdsp"]) == "0"
        and str(facts["v1781_wlfw_service69_seen"]) == "0"
        and str(facts["v1781_late_listener_state"]) == "uninit"
    )
    facts["v1781_safety_retained"] = all(
        str(facts[key]) == "1"
        for key in (
            "v1781_no_per_proxy",
            "v1781_no_esoc0",
            "v1781_no_scan_connect",
            "v1781_no_credentials",
            "v1781_no_dhcp_routes",
            "v1781_no_external_ping",
        )
    )

    if (
        facts["v1781_pass"]
        and facts["v1781_client_register_return_no_success"]
        and facts["v1781_request_still_absent"]
        and facts["android_per_mgr_register_seen"]
        and facts["android_per_mgr_vote_seen"]
        and facts["android_wlanmdsp_request_seen"]
        and facts["v1768_server_entry_only_before_match"]
        and facts["v1769_prematch_list_mutex_boundary"]
        and facts["v1781_safety_retained"]
    ):
        decision = "v1782-cnss-pm-register-return-no-success-host-pass"
        label = "client-register-return-no-forwarding"
        reason = (
            "V1781 proves service-object non-null and client register TX/return, "
            "but skips the libperipheral success path and still never requests wlanmdsp; "
            "retained V1768/V1769 evidence keeps the next blocker in PM server forwarding before WLAN-PD"
        )
        passed = True
    else:
        decision = "v1782-pm-forwarding-delta-incomplete-host-blocked"
        label = "pm-forwarding-delta-incomplete"
        reason = "required V1781 client-return, Android-good PM/request, or retained server-branch evidence is incomplete"
        passed = False

    return {
        "cycle": "V1782",
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": display_path(OUT_DIR),
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": facts,
        "next": {
            "recommended_gate": "source-build-only PM server forwarding observer for the V1781 route",
            "must_include": [
                "server-side pm-service register entry/match/add-client/return probes",
                "client-side libperipheral register return/success probes",
                "requested_wlanmdsp, WLFW service 69, late WLAN-PD listener state",
                "same hard stops as V1781 until a separate live gate is approved",
            ],
            "must_not_autochain": [
                "full PM trio",
                "per_proxy positive-control side effects",
                "WLAN-PD cascade",
                "Wi-Fi HAL",
                "scan/connect",
                "credentials",
                "DHCP/routes",
                "external ping",
            ],
        },
    }


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    return "\n".join(
        [
            "# Native Init V1782 WLAN-PD PM Forwarding Delta Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1782`",
            "- Type: host-only classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'BLOCKED'}`",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## V1781 Client-side PM Path",
            "",
            f"- provider seen: `{facts['v1781_provider_seen']}`",
            f"- `asInterface` call: `{facts['v1781_as_interface_call']}`",
            f"- manager register TX call: `{facts['v1781_register_tx_call']}`",
            f"- manager register TX return checkpoint: `{facts['v1781_register_tx_retcheck']}`",
            f"- register-connect return: `{facts['v1781_register_connect_return']}`",
            f"- client register common return: `{facts['v1781_client_register_common_return']}`",
            f"- success path: `{facts['v1781_success_path']}`",
            f"- requested `wlanmdsp`: `{facts['v1781_requested_wlanmdsp']}`",
            f"- WLFW service 69: `{facts['v1781_wlfw_service69_seen']}`",
            f"- late WLAN-PD listener state: `{facts['v1781_late_listener_state']}`",
            "",
            "## Retained Android-good / Server-side Model",
            "",
            f"- Android PM register seen: `{facts['android_per_mgr_register_seen']}`",
            f"- Android PM vote seen: `{facts['android_per_mgr_vote_seen']}`",
            f"- Android `wlanmdsp` request seen: `{facts['android_wlanmdsp_request_seen']}`",
            f"- Android WLAN-PD UP seen: `{facts['android_wlan_pd_up_seen']}`",
            f"- V1768 server entry-only-before-match: `{facts['v1768_server_entry_only_before_match']}`",
            f"- V1769 pre-match list/mutex boundary: `{facts['v1769_prematch_list_mutex_boundary']}`",
            "",
            "## Interpretation",
            "",
            "- V1781 closes the previous service-object-null gap: cnss-daemon gets a non-null `vendor.qcom.PeripheralManager` object and reaches the manager-register transaction.",
            "- V1781 does not prove functional PM forwarding: the client returns without the retained `periph_success_path`, `wlanmdsp` is still not requested, WLFW service 69 is absent, and WLAN-PD remains `uninit`.",
            "- The next aligned unit is not Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping. It is a source/build-only PM server forwarding observer for the V1781 route, then a separately approved one-run live gate.",
            "- The next live gate should avoid `per_proxy` positive-control side effects unless explicitly scoped, because V1769 classified the pre-match record/list boundary as sensitive to PM server ordering.",
            "",
            "## Safety",
            "",
            "- Host-only analysis. No live device command, flash, reboot, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, external ping, PM actor start, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write was performed.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = collect()
    manifest["out_dir"] = display_path(args.out_dir)
    store = EvidenceStore(args.out_dir)
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    write_private_text(args.report, report)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": manifest["out_dir"]}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
