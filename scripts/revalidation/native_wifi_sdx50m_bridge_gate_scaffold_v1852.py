#!/usr/bin/env python3
"""V1852 dry-run scaffold for a future SDX50M-selection bridge gate."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1852"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1852-sdx50m-bridge-gate-scaffold"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1852_SDX50M_BRIDGE_GATE_SCAFFOLD_2026-06-03.md"
)
V1851_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1851-sdx50m-selection-bridge-plan"
    / "manifest.json"
)
V1847_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1847-pm-service-open-context-handoff"
    / "manifest.json"
)
V1221_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_private_cnss_daemon_sdx50m_live_v1221.py"
V1847_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_pm_service_open_context_handoff_v1847.py"
V1851_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_sdx50m_selection_bridge_plan_v1851.py"


SELECTION_LABELS = (
    "pm_init_pm_client_register_call",
    "pm_init_pm_client_register_retcheck",
    "pm_init_pm_client_connect_call",
    "pm_init_pm_client_connect_retcheck",
    "pm_init_return_path",
    "pm_server_register_entry",
    "pm_server_register_strcmp_call",
)

OPEN_CONTEXT_LABELS = (
    "pm_service_post_ack_power_state_loaded",
    "pm_service_post_ack_open_context",
    "pm_service_post_ack_open_path_loaded",
    "pm_service_post_ack_open_fd_store",
    "pm_service_post_ack_open_fd_compare",
    "pm_service_post_ack_open_success_counter",
)

LOWER_RESPONSE_FIELDS = (
    "lower_mdm3_states",
    "lower_mhi_present",
    "lower_service69_progress",
    "lower_wlan0_present",
    "pm_focus_mhi_wlan0_progress",
    "pm_focus_change_fields",
    "pm_focus_mdm_status_delta",
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def gate_has_label(gate: dict[str, Any], label: str) -> bool:
    if label in gate:
        return True
    if f"{label}_hits" in gate:
        return True
    if f"{label}_hit_count" in gate:
        return True
    if f"{label}_first_hit_line" in gate:
        return True
    samples = gate.get("open_context_samples") or []
    if isinstance(samples, list):
        return any(isinstance(sample, dict) and sample.get("key") == label for sample in samples)
    return False


def collect_inputs(v1851: dict[str, Any], v1847: dict[str, Any]) -> dict[str, Any]:
    gate = v1847.get("gate") or {}
    return {
        "v1851": {
            "path": rel(V1851_MANIFEST),
            "decision": v1851.get("decision", ""),
            "label": v1851.get("label", ""),
            "pass": bool(v1851.get("pass")),
        },
        "scripts": {
            "private_route_reference": rel(V1221_SCRIPT),
            "private_route_reference_exists": V1221_SCRIPT.exists(),
            "open_context_reference": rel(V1847_SCRIPT),
            "open_context_reference_exists": V1847_SCRIPT.exists(),
            "bridge_plan_reference": rel(V1851_SCRIPT),
            "bridge_plan_reference_exists": V1851_SCRIPT.exists(),
        },
        "available_selection_labels": [label for label in SELECTION_LABELS if gate_has_label(gate, label)],
        "available_open_context_labels": [label for label in OPEN_CONTEXT_LABELS if gate_has_label(gate, label)],
        "available_lower_fields": [field for field in LOWER_RESPONSE_FIELDS if field in gate],
        "current_baseline": {
            "decision": v1847.get("decision", ""),
            "pass": bool(v1847.get("pass")),
            "pm_client_register_rc": intish(gate.get("pm_client_register_rc")),
            "pm_client_connect_rc": intish(gate.get("pm_client_connect_rc")),
            "pm_init_return_path_rc": intish(gate.get("pm_init_return_path_rc")),
            "pm_server_register_strcmp_requested": gate.get("pm_server_register_strcmp_requested", ""),
            "open_context_path": gate.get("open_context_path", ""),
            "open_context_fd": gate.get("open_context_fd", ""),
            "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
            "lower_service69_progress": bool(gate.get("lower_service69_progress")),
            "lower_wlan0_present": bool(gate.get("lower_wlan0_present")),
            "safety_ok": bool(gate.get("safety_ok")),
        },
    }


def scaffold_spec() -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "mode": "dry-run-only",
        "live_execution_implemented": False,
        "device_command_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "direct_subsys_esoc0_open_executed": False,
        "direct_pmic_gpio_gdsc_write_executed": False,
        "direct_esoc_ioctl_notify_executed": False,
        "forced_rc1_or_pci_rescan_executed": False,
        "future_gate_expected_paths": {
            "current_baseline": "/dev/subsys_modem",
            "sdx50m_candidate": "/dev/subsys_esoc0",
        },
        "future_gate_success_labels": [
            "sdx50m-selection-open-context-esoc0-with-lower-publication",
            "sdx50m-selection-esoc0-no-lower-publication",
            "sdx50m-selection-still-modem",
            "sdx50m-selection-register-or-connect-failed",
        ],
        "future_gate_promotion_rule": (
            "Wi-Fi HAL/scan/connect remains forbidden unless the gate observes "
            "WLFW service 69 and wlan0 after rollback-safe lower publication."
        ),
    }


def classify(inputs: dict[str, Any], spec: dict[str, Any]) -> tuple[str, str, str, bool]:
    selection_labels_ok = set(SELECTION_LABELS).issubset(inputs["available_selection_labels"])
    open_labels_ok = set(OPEN_CONTEXT_LABELS).issubset(inputs["available_open_context_labels"])
    lower_fields_ok = set(LOWER_RESPONSE_FIELDS).issubset(inputs["available_lower_fields"])
    scripts_ok = all(
        bool(value)
        for key, value in inputs["scripts"].items()
        if key.endswith("_exists")
    )
    baseline = inputs["current_baseline"]
    baseline_ok = (
        baseline["pass"]
        and baseline["safety_ok"]
        and baseline["pm_client_register_rc"] == 0
        and baseline["pm_client_connect_rc"] == 0
        and baseline["pm_init_return_path_rc"] == 0
        and baseline["pm_server_register_strcmp_requested"] == "modem"
        and baseline["open_context_path"] == spec["future_gate_expected_paths"]["current_baseline"]
        and not baseline["lower_service69_progress"]
        and not baseline["lower_wlan0_present"]
    )
    no_live_ok = (
        not spec["live_execution_implemented"]
        and not spec["device_command_executed"]
        and not spec["flash_executed"]
        and not spec["reboot_executed"]
        and not spec["wifi_hal_start_executed"]
        and not spec["scan_connect_executed"]
        and not spec["credential_use_executed"]
        and not spec["dhcp_route_executed"]
        and not spec["external_ping_executed"]
        and not spec["partition_write_executed"]
        and not spec["direct_subsys_esoc0_open_executed"]
        and not spec["direct_pmic_gpio_gdsc_write_executed"]
        and not spec["direct_esoc_ioctl_notify_executed"]
        and not spec["forced_rc1_or_pci_rescan_executed"]
    )
    if not inputs["v1851"]["pass"] or inputs["v1851"]["label"] != "sdx50m-selection-bridge-plan-ready-no-live":
        return "bridge-plan-review", "v1852-bridge-plan-review", "V1851 bridge plan is missing or not passing", False
    if not scripts_ok:
        return "script-reference-review", "v1852-script-reference-review", "Required script references are missing", False
    if not selection_labels_ok:
        return "selection-label-review", "v1852-selection-label-review", "Selection/register labels are incomplete for the scaffold", False
    if not open_labels_ok:
        return "open-context-label-review", "v1852-open-context-label-review", "Open-context labels are incomplete for the scaffold", False
    if not lower_fields_ok:
        return "lower-field-review", "v1852-lower-field-review", "Lower-response fields are incomplete for the scaffold", False
    if not baseline_ok:
        return "baseline-review", "v1852-baseline-review", "Current V1847 modem baseline no longer matches the scaffold assumptions", False
    if not no_live_ok:
        return "dry-run-safety-review", "v1852-dry-run-safety-review", "Scaffold claims a live, Wi-Fi, network, or lower-mutation action", False
    return (
        "sdx50m-bridge-gate-scaffold-dry-run-ready",
        "v1852-sdx50m-bridge-gate-scaffold-dry-run-ready-host-pass",
        "Dry-run scaffold is ready: it names the SDX50M-selection, PM open-context, and lower-response fields needed for a future rollbackable gate while executing no live or Wi-Fi action",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    inputs = result["details"]["inputs"]
    spec = result["details"]["scaffold_spec"]
    return "\n".join([
        "# Native Init V1852 SDX50M Bridge Gate Scaffold",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: dry-run source scaffold for a future SDX50M-selection bridge gate",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## References",
        "",
        f"- V1851: `{inputs['v1851']['decision']}` / `{inputs['v1851']['label']}`",
        f"- Private route script: `{inputs['scripts']['private_route_reference']}` exists `{inputs['scripts']['private_route_reference_exists']}`",
        f"- Open-context script: `{inputs['scripts']['open_context_reference']}` exists `{inputs['scripts']['open_context_reference_exists']}`",
        f"- Bridge plan script: `{inputs['scripts']['bridge_plan_reference']}` exists `{inputs['scripts']['bridge_plan_reference_exists']}`",
        "",
        "## Scaffold Fields",
        "",
        f"- selection labels: `{inputs['available_selection_labels']}`",
        f"- open-context labels: `{inputs['available_open_context_labels']}`",
        f"- lower-response fields: `{inputs['available_lower_fields']}`",
        f"- baseline: `{inputs['current_baseline']}`",
        "",
        "## Dry-Run Contract",
        "",
        f"- mode: `{spec['mode']}`",
        f"- live/device/flash/reboot executed: `{spec['live_execution_implemented']}` / `{spec['device_command_executed']}` / `{spec['flash_executed']}` / `{spec['reboot_executed']}`",
        f"- Wi-Fi/credential/network executed: `{spec['wifi_hal_start_executed']}` / `{spec['scan_connect_executed']}` / `{spec['credential_use_executed']}` / `{spec['dhcp_route_executed']}` / `{spec['external_ping_executed']}`",
        f"- lower mutation executed: subsys_esoc0 `{spec['direct_subsys_esoc0_open_executed']}`, PMIC/GPIO/GDSC `{spec['direct_pmic_gpio_gdsc_write_executed']}`, eSoC ioctl/notify `{spec['direct_esoc_ioctl_notify_executed']}`, forced RC1/rescan `{spec['forced_rc1_or_pci_rescan_executed']}`",
        f"- expected paths: `{spec['future_gate_expected_paths']}`",
        f"- future labels: `{spec['future_gate_success_labels']}`",
        f"- promotion rule: {spec['future_gate_promotion_rule']}",
        "",
        "## Interpretation",
        "",
        "- V1852 is executable only as a host dry-run scaffold. It does not start the private SDX50M route.",
        "- The scaffold locks the exact PM register/connect, PM-service compare, PM open-context, and lower-response fields a future gate must collect.",
        "- The future gate still cannot promote to Wi-Fi connect until WLFW service 69 and `wlan0` are observed first.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This scaffold did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next candidate is source/build-only helper integration that can emit this scaffold's labels in a rollbackable test image, still without running the live private SDX50M route.",
        "",
    ])


def main() -> int:
    inputs = collect_inputs(load_json(V1851_MANIFEST), load_json(V1847_MANIFEST))
    spec = scaffold_spec()
    label, decision, reason, passed = classify(inputs, spec)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": {
            "inputs": inputs,
            "scaffold_spec": spec,
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
