#!/usr/bin/env python3
"""V1766 host-only classifier for the post-firmware-request stop directive.

The active state is:

* V1753/V1763 fixed the redirect label as firmware-not-requested.
* V1760 fixed the active blocker as request generation before firmware serving.
* V1761/V1756/V1757 identified the only concrete pre-request delta as the
  PeripheralManager service object/register-vote path.
* The latest directive forbids adding PM/QCACLD/eSoC/RC1/HAL actors and says to
  stop after the firmware-request label.

This unit does not contact the device.  It reconciles those facts so the next
work cannot accidentally restart route minimization or live actor expansion.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1766-wlan-pd-request-trigger-directive-classifier"
REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1766_WLAN_PD_REQUEST_TRIGGER_DIRECTIVE_CLASSIFIER_2026-06-03.md"
)

V1760 = REPO_ROOT / "tmp" / "wifi" / "v1760-wlan-pd-request-trigger-surface-classifier" / "manifest.json"
V1761 = REPO_ROOT / "tmp" / "wifi" / "v1761-wlan-pd-autoload-trigger-contract-classifier" / "manifest.json"
V1763 = REPO_ROOT / "tmp" / "wifi" / "v1763-wlan-pd-firmware-request-gate-reconciliation" / "manifest.json"
V1764 = REPO_ROOT / "tmp" / "wifi" / "v1764-wlan-pd-service-object-visible-helper-build" / "manifest.json"
V1765_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1765_WLAN_PD_FIRMWARE_REQUEST_DIRECTIVE_AUDIT_2026-06-03.md"
)
V1756_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1756_WLAN_PD_PM_REGISTER_TRACE_CLASSIFIER_2026-06-03.md"
)
V1757_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1757_WLAN_PD_PERIPHERAL_INTERFACE_BRANCH_CLASSIFIER_2026-06-03.md"
)


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


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def facts(v1760: dict[str, Any], v1761: dict[str, Any], v1763: dict[str, Any], v1764: dict[str, Any]) -> dict[str, Any]:
    v1761_facts = v1761.get("facts") or {}
    v1763_native = v1763.get("native_v1736") or {}
    return {
        "firmware_request_label_fixed": v1763.get("label") == "firmware-not-requested" and boolish(v1763.get("pass")),
        "request_generation_gap": v1760.get("label") == "request-generation-gap-before-firmware-serving"
        and boolish(v1760.get("pass")),
        "android_pm_register_seen": boolish(v1761_facts.get("android_pm_register_seen")),
        "android_pm_vote_seen": boolish(v1761_facts.get("android_pm_vote_seen")),
        "android_wlanmdsp_request_seen": boolish(v1761_facts.get("android_wlanmdsp_request_seen")),
        "native_reaches_wlfw_request": intish(v1763_native.get("wlfw_service_request_hit_count")) > 0,
        "native_tftp_running": intish(v1763_native.get("tftp_running")) > 0,
        "native_requested_wlanmdsp": intish(v1763_native.get("requested_wlanmdsp")) > 0,
        "native_wlfw_service69_seen": intish(v1763_native.get("wlfw_service69_seen")) > 0,
        "native_pm_null_branch": boolish(v1761_facts.get("native_pm_null_peripheral_branch")),
        "native_as_interface_reached": boolish(v1761_facts.get("native_periph_as_interface_call")),
        "native_manager_register_tx_reached": boolish(v1761_facts.get("native_periph_manager_register_tx_call")),
        "native_peripheral_manager_enabled": boolish(v1761_facts.get("native_peripheral_manager_enabled")),
        "v1764_dormant_artifact_available": boolish(v1764.get("pass"))
        and v1764.get("decision") == "v1764-service-object-visible-helper-build-pass",
    }


def classify(all_facts: dict[str, Any], stop_text: str) -> tuple[str, bool, str, str]:
    stop_forbids_live_pm = (
        "Do not deploy or live-run the V1764 service-object-visible helper" in stop_text
        and "PM actor start" in stop_text
    )
    if not all_facts["firmware_request_label_fixed"]:
        return (
            "v1766-firmware-request-label-not-fixed",
            False,
            "V1763 firmware-request label is not fixed; do not select a request-trigger follow-up",
            "firmware-request-label-missing",
        )
    if not all_facts["request_generation_gap"]:
        return (
            "v1766-request-generation-gap-not-proven",
            False,
            "V1760 request-generation gap evidence is missing",
            "request-gap-missing",
        )
    if not (
        all_facts["android_pm_register_seen"]
        and all_facts["android_pm_vote_seen"]
        and all_facts["android_wlanmdsp_request_seen"]
    ):
        return (
            "v1766-android-pre-request-delta-missing",
            False,
            "Android-good pre-request PM register/vote and wlanmdsp request evidence is incomplete",
            "android-delta-missing",
        )
    if not (
        all_facts["native_reaches_wlfw_request"]
        and all_facts["native_tftp_running"]
        and all_facts["native_pm_null_branch"]
        and not all_facts["native_requested_wlanmdsp"]
        and not all_facts["native_wlfw_service69_seen"]
    ):
        return (
            "v1766-native-request-trigger-baseline-mismatch",
            False,
            "Native baseline does not match the expected WLFW-request/no-wlanmdsp/no-service69 state",
            "native-baseline-mismatch",
        )
    if stop_forbids_live_pm:
        return (
            "v1766-request-trigger-gap-identified-live-gate-suspended-host-pass",
            True,
            "Only identified concrete request-trigger gap is PeripheralManager service-object/register-vote, but the current directive suspends live PM actor/helper gates",
            "pm-service-object-gap-identified-live-suspended",
        )
    return (
        "v1766-request-trigger-gap-identified-live-gate-eligible-host-pass",
        True,
        "Only identified concrete request-trigger gap is PeripheralManager service-object/register-vote; a later bounded live gate would need explicit scope",
        "pm-service-object-gap-identified-live-eligible",
    )


def render_report(result: dict[str, Any]) -> str:
    facts_obj = result["facts"]
    return "\n".join(
        [
            "# Native Init V1766 WLAN-PD Request-trigger Directive Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1766`",
            "- Type: host-only request-trigger directive classifier",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Inputs",
            "",
            f"- V1760 request-trigger surface: `{result['inputs']['v1760']}`",
            f"- V1761 autoload/request-trigger contract: `{result['inputs']['v1761']}`",
            f"- V1763 firmware-request reconciliation: `{result['inputs']['v1763']}`",
            f"- V1764 dormant helper artifact: `{result['inputs']['v1764']}`",
            f"- V1765 active stop audit: `{result['inputs']['v1765_report']}`",
            f"- V1756 PM register trace report: `{result['inputs']['v1756_report']}`",
            f"- V1757 libperipheral branch report: `{result['inputs']['v1757_report']}`",
            "",
            "## Facts",
            "",
            f"- Fixed firmware-request label: `{facts_obj['firmware_request_label_fixed']}`",
            f"- Request-generation gap before firmware serving: `{facts_obj['request_generation_gap']}`",
            f"- Android PM register/vote before request: `{facts_obj['android_pm_register_seen']}` / `{facts_obj['android_pm_vote_seen']}`",
            f"- Android `wlanmdsp.mbn` request observed: `{facts_obj['android_wlanmdsp_request_seen']}`",
            f"- Native reaches WLFW request with `tftp_server`: `{facts_obj['native_reaches_wlfw_request']}` / `{facts_obj['native_tftp_running']}`",
            f"- Native requested `wlanmdsp` / WLFW service 69: `{facts_obj['native_requested_wlanmdsp']}` / `{facts_obj['native_wlfw_service69_seen']}`",
            f"- Native PM null branch / `asInterface` / manager-register TX: `{facts_obj['native_pm_null_branch']}` / `{facts_obj['native_as_interface_reached']}` / `{facts_obj['native_manager_register_tx_reached']}`",
            f"- V1764 dormant helper artifact available: `{facts_obj['v1764_dormant_artifact_available']}`",
            "",
            "## Interpretation",
            "",
            "- The firmware path itself is not the current blocker because native never generates a `wlanmdsp.mbn` request.",
            "- The route that matters already reaches the WLFW worker and has `tftp_server` running.",
            "- Android-good requests `wlanmdsp.mbn` after PM register/vote and WLFW request.",
            "- Native reaches the CNSS PM path but stops at the PeripheralManager service-object/null branch before `asInterface`, manager-register transaction, PM success, `wlanmdsp.mbn` request, or WLFW service 69.",
            "- Therefore the only currently identified concrete request-trigger gap is the PeripheralManager service-object/register-vote path.",
            "- The current stop directive still forbids deploying or live-running the V1764 service-object-visible helper; that artifact remains dormant.",
            "",
            "## Active Boundary",
            "",
            "- Do not rerun V1739/V1753 firmware-request capture.",
            "- Do not restart route minimization or tracefs plumbing.",
            "- Do not add PM/QCACLD/eSoC/RC1/restart-PD/Wi-Fi HAL/scan/connect/credential/DHCP/route/external-ping actors in this unit.",
            "- No device command, flash, reboot, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, or actor start was performed.",
            "",
            "## Next",
            "",
            "- With the current stop directive, the next safe work is host/source-only contract extraction around the already identified PeripheralManager service-object gap.",
            "- A live V1764-style service-object-visible discriminator should remain suspended until a new directive explicitly reopens that narrow gate.",
            "- Completion remains unproven: native Wi-Fi has not reached WLFW service 69, `wlan0`, scan/connect, or external ping.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    EvidenceStore(args.out_dir)

    v1760 = load_json(V1760)
    v1761 = load_json(V1761)
    v1763 = load_json(V1763)
    v1764 = load_json(V1764)
    stop_text = read_text(V1765_REPORT)
    all_facts = facts(v1760, v1761, v1763, v1764)
    decision, passed, reason, label = classify(all_facts, stop_text)

    result = {
        "cycle": "V1766",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": display_path(args.out_dir),
        "inputs": {
            "v1760": display_path(V1760),
            "v1761": display_path(V1761),
            "v1763": display_path(V1763),
            "v1764": display_path(V1764),
            "v1765_report": display_path(V1765_REPORT),
            "v1756_report": display_path(V1756_REPORT),
            "v1757_report": display_path(V1757_REPORT),
        },
        "facts": all_facts,
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
    }

    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.report, render_report(result))
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": display_path(args.out_dir)}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
