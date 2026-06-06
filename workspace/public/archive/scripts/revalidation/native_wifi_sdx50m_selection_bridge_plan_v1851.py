#!/usr/bin/env python3
"""V1851 no-live SDX50M selection bridge plan classifier."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1851"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1851-sdx50m-selection-bridge-plan"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1851_SDX50M_SELECTION_BRIDGE_PLAN_2026-06-03.md"
)
V1220_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1220-cnss-daemon-sdx50m-patch"
    / "manifest.json"
)
V1221_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1221-private-cnss-daemon-sdx50m-live"
    / "manifest.json"
)
V1345_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1345-current-route-mdm2ap-timing-sampler-live"
    / "manifest.json"
)
V1349_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1349-cnss-wlfw-runtime-prereq-classifier"
    / "manifest.json"
)
V1847_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1847-pm-service-open-context-handoff"
    / "manifest.json"
)
V1848_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1848-cnss-pm-selection-classifier"
    / "manifest.json"
)
V1849_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1849-sdx50m-private-route-reuse-classifier"
    / "manifest.json"
)
V1850_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1850-pm-register-prereq-reconcile"
    / "manifest.json"
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


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value) in {"1", "True", "true", "yes"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_patch(manifest: dict[str, Any]) -> dict[str, Any]:
    output = REPO_ROOT / str(manifest.get("output", ""))
    output_exists = output.exists()
    output_sha = sha256_file(output) if output_exists else ""
    return {
        "path": rel(V1220_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "host_only": bool(manifest.get("host_only")),
        "cnss_daemon_executed": bool(manifest.get("cnss_daemon_executed")),
        "device_command_executed": bool(manifest.get("device_command_executed")),
        "wifi_hal_start_executed": bool(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
        "partition_write_executed": bool(manifest.get("partition_write_executed")),
        "flash_executed": bool(manifest.get("flash_executed")),
        "patch_literal_c_string": manifest.get("patch_literal_c_string", ""),
        "patch_offset_hex": manifest.get("patch_offset_hex", ""),
        "output": str(manifest.get("output", "")),
        "output_exists": output_exists,
        "output_sha256": manifest.get("output_sha256", ""),
        "output_sha256_actual": output_sha,
        "output_sha256_ok": output_exists and output_sha == manifest.get("output_sha256", ""),
        "output_size": intish(manifest.get("output_size")),
    }


def collect_private_route(manifest: dict[str, Any]) -> dict[str, Any]:
    thread = manifest.get("thread_analysis") or {}
    firmware = ((manifest.get("analysis") or {}).get("global_firmware") or {})
    markers = ((firmware.get("markers") or {}).get("counts") or {})
    return {
        "path": rel(V1221_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "private_cnss_daemon": manifest.get("private_cnss_daemon") or {},
        "cnss_daemon_start_executed": bool(manifest.get("cnss_daemon_start_executed")),
        "wifi_hal_start_executed": bool(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "credential_use_executed": bool(manifest.get("credential_use_executed")),
        "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
        "partition_write_executed": bool(manifest.get("partition_write_executed")),
        "flash_executed": bool(manifest.get("flash_executed")),
        "reboot_executed": bool(manifest.get("reboot_executed")),
        "cnss_registered_peripherals": thread.get("cnss_registered_peripherals") or [],
        "cnss_registered_sdx50m": bool(thread.get("cnss_registered_sdx50m")),
        "per_mgr_esoc0_any": bool(manifest.get("per_mgr_esoc0_any")),
        "mdm_subsys_powerup_any": bool(thread.get("mdm_subsys_powerup_any")),
        "mdm3_after_observer": firmware.get("mdm3_after_observer", ""),
        "marker_counts": markers,
        "wlan0_up": bool(manifest.get("wlan0_up")),
    }


def collect_current_pm(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") or {}
    register_call = gate.get("pm_init_pm_client_register_call") or {}
    register_retcheck = gate.get("pm_init_pm_client_register_retcheck") or {}
    return {
        "path": rel(V1847_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "pm_client_register_rc": intish(gate.get("pm_client_register_rc")),
        "pm_client_connect_rc": intish(gate.get("pm_client_connect_rc")),
        "pm_init_return_path_rc": intish(gate.get("pm_init_return_path_rc")),
        "register_call_hits": intish(register_call.get("hit_count")),
        "register_retcheck_hits": intish(register_retcheck.get("hit_count")),
        "callback_ack_label": gate.get("callback_ack_label", ""),
        "post_ack_label": gate.get("post_ack_label", ""),
        "open_context_label": gate.get("open_context_label", ""),
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "lower_continuation_label": gate.get("lower_continuation_label", ""),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "lower_service69_progress": bool(gate.get("lower_service69_progress")),
        "lower_wlan0_present": bool(gate.get("lower_wlan0_present")),
        "safety_ok": bool(gate.get("safety_ok")),
    }


def collect_manifest(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "checks": manifest.get("checks") or [],
    }


def bridge_contract() -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "type": "source-build-only bridge plan",
        "live_action_executed": False,
        "wifi_hal_start_allowed": False,
        "scan_connect_allowed": False,
        "credential_use_allowed": False,
        "dhcp_route_allowed": False,
        "external_ping_allowed": False,
        "direct_subsys_esoc0_open_allowed": False,
        "direct_pmic_gpio_gdsc_write_allowed": False,
        "direct_esoc_ioctl_notify_allowed": False,
        "forced_rc1_or_pci_rescan_allowed": False,
        "future_live_candidate_inputs": [
            "private SDX50M cnss-daemon artifact from V1220",
            "current PM register/connect/open-context labels from V1847",
            "CNSS PM selection compare labels from V1848",
            "lower-response stop conditions from V1345/V1849",
        ],
        "future_live_minimum_success": [
            "patched CNSS request selects SDX50M rather than modem",
            "PM-service post-ack open context selects /dev/subsys_esoc0 by PM-service path, not direct host open",
            "rollback to v724 verifies filtered version and selftest fail=0",
            "no Wi-Fi HAL/scan/connect unless WLFW service 69 and wlan0 appear first",
        ],
        "future_live_stop_conditions": [
            "PM register/connect does not return rc=0",
            "PM-service still selects modem",
            "mdm3 remains OFFLINING with no GPIO142/PCIe/MHI/WLFW/wlan0 response",
            "modem crash/down markers rise before WLFW publication",
            "any guardrail action outside the bridge contract is needed",
        ],
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    patch = details["v1220_patch"]
    private_route = details["v1221_private_route"]
    current_pm = details["v1847_current_pm"]
    selection = details["v1848_selection"]
    private_reuse = details["v1849_private_reuse"]
    prereq = details["v1850_prereq"]
    lower_window = details["v1345_lower_window"]
    runtime_prereq = details["v1349_runtime_prereq"]
    patch_ready = (
        patch["pass"]
        and patch["decision"] == "v1220-private-cnss-daemon-sdx50m-patch-ready"
        and patch["host_only"]
        and patch["output_sha256_ok"]
        and not patch["cnss_daemon_executed"]
        and not patch["device_command_executed"]
        and not patch["wifi_hal_start_executed"]
        and not patch["scan_connect_executed"]
        and not patch["credential_use_executed"]
        and not patch["dhcp_route_executed"]
        and not patch["external_ping_executed"]
        and not patch["partition_write_executed"]
        and not patch["flash_executed"]
    )
    private_route_known = (
        private_route["pass"]
        and private_route["decision"] == "v1221-sdx50m-per-mgr-esoc0"
        and private_route["cnss_daemon_start_executed"]
        and private_route["cnss_registered_sdx50m"]
        and "SDX50M" in private_route["cnss_registered_peripherals"]
        and private_route["per_mgr_esoc0_any"]
        and private_route["mdm_subsys_powerup_any"]
        and not private_route["wifi_hal_start_executed"]
        and not private_route["scan_connect_executed"]
        and not private_route["credential_use_executed"]
        and not private_route["dhcp_route_executed"]
        and not private_route["external_ping_executed"]
        and not private_route["partition_write_executed"]
        and not private_route["flash_executed"]
        and not private_route["reboot_executed"]
    )
    current_pm_closed = (
        current_pm["pass"]
        and current_pm["safety_ok"]
        and current_pm["pm_client_register_rc"] == 0
        and current_pm["pm_client_connect_rc"] == 0
        and current_pm["pm_init_return_path_rc"] == 0
        and current_pm["register_call_hits"] >= 1
        and current_pm["register_retcheck_hits"] >= 1
        and current_pm["callback_ack_label"] == "callback-ack-present-no-powerup"
        and current_pm["post_ack_label"] == "post-ack-open-branch-reached"
        and current_pm["open_context_label"] == "open-context-modem-success-static"
        and current_pm["open_context_path"] == "/dev/subsys_modem"
    )
    current_selection_known = (
        selection["pass"]
        and selection["label"] == "cnss-pm-register-selects-modem-record"
        and selection["decision"] == "v1848-cnss-pm-register-selects-modem-not-sdx50m-host-pass"
    )
    no_blind_private_rerun = (
        private_reuse["pass"]
        and private_reuse["label"] == "private-sdx50m-route-known-lower-gap"
        and private_reuse["decision"] == "v1849-private-sdx50m-route-known-lower-gap-host-pass"
    )
    prereq_reconciled = (
        prereq["pass"]
        and prereq["label"] == "pm-register-prereq-closed-for-modem-selection-remains"
        and prereq["decision"] == "v1850-pm-register-prereq-closed-for-modem-selection-remains-host-pass"
    )
    lower_response_gap_authoritative = (
        lower_window["pass"]
        and lower_window["decision"] == "v1345-current-route-mdm2ap-full-window-no-transition"
        and runtime_prereq["pass"]
        and runtime_prereq["decision"] == "v1349-cnss-pm-register-blocker-is-next-prereq"
    )
    contract = details["bridge_contract"]
    contract_safe = (
        not contract["live_action_executed"]
        and not contract["wifi_hal_start_allowed"]
        and not contract["scan_connect_allowed"]
        and not contract["credential_use_allowed"]
        and not contract["dhcp_route_allowed"]
        and not contract["external_ping_allowed"]
        and not contract["direct_subsys_esoc0_open_allowed"]
        and not contract["direct_pmic_gpio_gdsc_write_allowed"]
        and not contract["direct_esoc_ioctl_notify_allowed"]
        and not contract["forced_rc1_or_pci_rescan_allowed"]
    )

    if not patch_ready:
        return "patch-artifact-review", "v1851-patch-artifact-review", "Private SDX50M cnss-daemon artifact is missing, changed, or not host-only clean", False
    if not private_route_known:
        return "private-route-review", "v1851-private-route-review", "Historical private SDX50M route proof is missing or guardrail-unclean", False
    if not current_pm_closed:
        return "current-pm-review", "v1851-current-pm-review", "Current PM register/connect/open-context closure is missing or inconsistent", False
    if not current_selection_known:
        return "current-selection-review", "v1851-current-selection-review", "Current route selection is not fixed to the modem-record classifier", False
    if not no_blind_private_rerun:
        return "private-rerun-review", "v1851-private-rerun-review", "Private SDX50M route reuse has not been classified as a known lower-gap path", False
    if not prereq_reconciled:
        return "prereq-reconcile-review", "v1851-prereq-reconcile-review", "PM-register prerequisite reconciliation is missing", False
    if not lower_response_gap_authoritative:
        return "lower-gap-review", "v1851-lower-gap-review", "Lower-response gap evidence is missing or inconsistent", False
    if not contract_safe:
        return "contract-safety-review", "v1851-contract-safety-review", "Bridge contract permits a blocked live or Wi-Fi action", False
    return (
        "sdx50m-selection-bridge-plan-ready-no-live",
        "v1851-sdx50m-selection-bridge-plan-ready-no-live-host-pass",
        "No-live bridge inputs are coherent: private SDX50M selection can be reused only under current PM-closure instrumentation and lower-response guardrails, with Wi-Fi connect still blocked until WLFW service 69 and wlan0 appear",
        True,
    )


def render_checks(result: dict[str, Any]) -> list[str]:
    details = result["details"]
    patch = details["v1220_patch"]
    private_route = details["v1221_private_route"]
    current_pm = details["v1847_current_pm"]
    return [
        f"- patch artifact: `{patch['decision']}` sha_ok `{patch['output_sha256_ok']}` output `{patch['output']}`",
        f"- private route: `{private_route['decision']}` registrations `{private_route['cnss_registered_peripherals']}` esoc `{private_route['per_mgr_esoc0_any']}` powerup `{private_route['mdm_subsys_powerup_any']}`",
        f"- current PM closure: register/connect/return `{current_pm['pm_client_register_rc']}` / `{current_pm['pm_client_connect_rc']}` / `{current_pm['pm_init_return_path_rc']}` open `{current_pm['open_context_path']}`",
        f"- current selection: `{details['v1848_selection']['decision']}` / `{details['v1848_selection']['label']}`",
        f"- private route reuse: `{details['v1849_private_reuse']['decision']}` / `{details['v1849_private_reuse']['label']}`",
        f"- PM prereq reconcile: `{details['v1850_prereq']['decision']}` / `{details['v1850_prereq']['label']}`",
        f"- lower window/runtime: `{details['v1345_lower_window']['decision']}` / `{details['v1349_runtime_prereq']['decision']}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    contract = result["details"]["bridge_contract"]
    lines = [
        "# Native Init V1851 SDX50M Selection Bridge Plan",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: source/build-only bridge-plan classifier; no live device action",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Input Checks",
        "",
        *render_checks(result),
        "",
        "## Bridge Contract",
        "",
        f"- live action executed: `{contract['live_action_executed']}`",
        f"- Wi-Fi/credential/network allowed: `{contract['wifi_hal_start_allowed']}` / `{contract['scan_connect_allowed']}` / `{contract['credential_use_allowed']}` / `{contract['dhcp_route_allowed']}` / `{contract['external_ping_allowed']}`",
        f"- direct lower mutation allowed: subsys_esoc0 `{contract['direct_subsys_esoc0_open_allowed']}`, PMIC/GPIO/GDSC `{contract['direct_pmic_gpio_gdsc_write_allowed']}`, eSoC ioctl/notify `{contract['direct_esoc_ioctl_notify_allowed']}`, forced RC1/rescan `{contract['forced_rc1_or_pci_rescan_allowed']}`",
        f"- future live inputs: `{contract['future_live_candidate_inputs']}`",
        f"- future minimum success: `{contract['future_live_minimum_success']}`",
        f"- future stop conditions: `{contract['future_live_stop_conditions']}`",
        "",
        "## Interpretation",
        "",
        "- V1851 does not run the private SDX50M route. It only validates that the next possible live unit has coherent inputs and explicit stop conditions.",
        "- The bridge preserves V1847 PM closure instrumentation and V1848 selection comparison so a future run can distinguish `modem` selection from `SDX50M` selection.",
        "- V1849/V1345 keep the known lower-response gap authoritative; a future SDX50M run is useful only if it adds bounded evidence beyond the already-known eSoC-powerup/no-response result.",
        "- Wi-Fi connect and ping remain blocked until lower publication proves WLFW service 69 and `wlan0` exist.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next implementation candidate is a source/build-only V1852 gate scaffold that combines V1847 PM open-context labels with SDX50M-selection compare labels, but still defaults to dry-run/no-live.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    details = {
        "v1220_patch": collect_patch(load_json(V1220_MANIFEST)),
        "v1221_private_route": collect_private_route(load_json(V1221_MANIFEST)),
        "v1345_lower_window": collect_manifest(V1345_MANIFEST, load_json(V1345_MANIFEST)),
        "v1349_runtime_prereq": collect_manifest(V1349_MANIFEST, load_json(V1349_MANIFEST)),
        "v1847_current_pm": collect_current_pm(load_json(V1847_MANIFEST)),
        "v1848_selection": collect_manifest(V1848_MANIFEST, load_json(V1848_MANIFEST)),
        "v1849_private_reuse": collect_manifest(V1849_MANIFEST, load_json(V1849_MANIFEST)),
        "v1850_prereq": collect_manifest(V1850_MANIFEST, load_json(V1850_MANIFEST)),
        "bridge_contract": bridge_contract(),
    }
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
