#!/usr/bin/env python3
"""V1849 host-only classifier for reusing the private SDX50M CNSS route."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1849"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1849-sdx50m-private-route-reuse-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1849_SDX50M_PRIVATE_ROUTE_REUSE_CLASSIFIER_2026-06-03.md"
)
V1848_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1848-cnss-pm-selection-classifier"
    / "manifest.json"
)
V1221_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1221-private-cnss-daemon-sdx50m-live"
    / "manifest.json"
)
V1222_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1222-post-esoc-power-boundary-live"
    / "manifest.json"
)
V1223_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1223-sdx50m-crash-source-classifier"
    / "manifest.json"
)
V1239_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1239-post-esoc0-powerup-gap-classifier"
    / "manifest.json"
)


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value) in {"1", "True", "true", "yes"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def guardrail_summary(manifest: dict[str, Any]) -> dict[str, bool]:
    return {
        "wifi_hal_start_executed": boolish(manifest.get("wifi_hal_start_executed")),
        "scan_connect_executed": boolish(manifest.get("scan_connect_executed")),
        "credential_use_executed": boolish(manifest.get("credential_use_executed")),
        "dhcp_route_executed": boolish(manifest.get("dhcp_route_executed")),
        "external_ping_executed": boolish(manifest.get("external_ping_executed")),
        "wifi_bringup_executed": boolish(manifest.get("wifi_bringup_executed")),
        "partition_write_executed": boolish(manifest.get("partition_write_executed")),
        "flash_executed": boolish(manifest.get("flash_executed")),
        "reboot_executed": boolish(manifest.get("reboot_executed")),
    }


def manifest_safety_ok(guardrails: dict[str, bool], *, allow_cnss_live: bool = False) -> bool:
    del allow_cnss_live
    return not any(guardrails.values())


def collect_current(v1848: dict[str, Any]) -> dict[str, Any]:
    current = ((v1848.get("details") or {}).get("v1847") or {})
    return {
        "path": rel(V1848_MANIFEST),
        "decision": v1848.get("decision", ""),
        "pass": bool(v1848.get("pass")),
        "label": v1848.get("label", ""),
        "requested_values": current.get("requested_values") or [],
        "candidate_values": current.get("candidate_values") or [],
        "pm_map": current.get("pm_map") or {},
        "open_context_path": current.get("open_context_path", ""),
        "open_context_fd": current.get("open_context_fd", ""),
        "lower_continuation_label": current.get("lower_continuation_label", ""),
        "post_pm_lower_state_label": current.get("post_pm_lower_state_label", ""),
        "lower_service69_progress": bool(current.get("lower_service69_progress")),
        "lower_wlan0_present": bool(current.get("lower_wlan0_present")),
    }


def collect_v1221(v1221: dict[str, Any]) -> dict[str, Any]:
    thread = v1221.get("thread_analysis") or {}
    firmware = ((v1221.get("analysis") or {}).get("global_firmware") or {})
    marker_counts = (firmware.get("markers") or {}).get("counts") or {}
    return {
        "path": rel(V1221_MANIFEST),
        "decision": v1221.get("decision", ""),
        "pass": bool(v1221.get("pass")),
        "reason": v1221.get("reason", ""),
        "private_cnss_daemon": v1221.get("private_cnss_daemon") or {},
        "patched_cnss_sha256": v1221.get("patched_cnss_sha256", ""),
        "cnss_daemon_start_executed": bool(v1221.get("cnss_daemon_start_executed")),
        "guardrails": guardrail_summary(v1221),
        "cnss_registered_peripherals": thread.get("cnss_registered_peripherals") or [],
        "cnss_registered_sdx50m": bool(thread.get("cnss_registered_sdx50m")),
        "cnss_registered_modem": bool(thread.get("cnss_registered_modem")),
        "per_mgr_esoc0_any": bool(v1221.get("per_mgr_esoc0_any")),
        "pm_actor_executed": bool(v1221.get("pm_actor_executed")),
        "mdm_subsys_powerup_any": bool(thread.get("mdm_subsys_powerup_any")),
        "mdm_subsys_powerup_late": bool(thread.get("mdm_subsys_powerup_late")),
        "late_pm_wchans": thread.get("late_pm_wchans") or [],
        "mdm3_after_observer": firmware.get("mdm3_after_observer", ""),
        "marker_counts": marker_counts,
        "qrtr_services_after_observer": firmware.get("qrtr_services_after_observer") or {},
        "wlan0_up": bool(v1221.get("wlan0_up")),
    }


def collect_followup(manifest: dict[str, Any], path: Path) -> dict[str, Any]:
    checks = manifest.get("checks") or []
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "guardrails": guardrail_summary(manifest),
        "checks": checks,
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    current = details["current"]
    private = details["v1221"]
    v1222 = details["v1222"]
    v1223 = details["v1223"]
    v1239 = details["v1239"]
    current_modem_selection = (
        current["pass"]
        and current["label"] == "cnss-pm-register-selects-modem-record"
        and current["requested_values"] == ["modem"]
        and current["open_context_path"] == "/dev/subsys_modem"
        and current["lower_continuation_label"] == "lower-continuation-static-gap"
        and current["post_pm_lower_state_label"] == "stable-mdm3-offlining"
        and not current["lower_service69_progress"]
        and not current["lower_wlan0_present"]
    )
    private_route_reaches_esoc0 = (
        private["pass"]
        and private["decision"] == "v1221-sdx50m-per-mgr-esoc0"
        and private["cnss_daemon_start_executed"]
        and private["cnss_registered_sdx50m"]
        and "SDX50M" in private["cnss_registered_peripherals"]
        and private["per_mgr_esoc0_any"]
        and private["pm_actor_executed"]
        and private["mdm_subsys_powerup_any"]
    )
    private_guardrails_clean = (
        private["guardrails"]["wifi_hal_start_executed"] is False
        and private["guardrails"]["scan_connect_executed"] is False
        and private["guardrails"]["credential_use_executed"] is False
        and private["guardrails"]["dhcp_route_executed"] is False
        and private["guardrails"]["external_ping_executed"] is False
        and private["guardrails"]["wifi_bringup_executed"] is False
        and private["guardrails"]["partition_write_executed"] is False
        and private["guardrails"]["flash_executed"] is False
        and private["guardrails"]["reboot_executed"] is False
    )
    lower_gap_confirmed = (
        v1222["pass"]
        and v1222["decision"] == "v1222-esoc-powerup-crash-before-wlfw"
        and v1223["pass"]
        and v1223["decision"] == "v1223-sdx50m-crash-source-contract-gap-classified"
        and v1239["pass"]
        and v1239["decision"] == "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw"
    )
    followup_guardrails_clean = (
        manifest_safety_ok(v1222["guardrails"])
        and manifest_safety_ok(v1223["guardrails"])
        and manifest_safety_ok(v1239["guardrails"])
    )
    no_lower_publication = (
        private["mdm3_after_observer"] == "OFFLINING"
        and intish(private["marker_counts"].get("wlfw")) == 0
        and intish(private["marker_counts"].get("bdf")) == 0
        and intish(private["marker_counts"].get("mhi")) == 0
        and intish(private["marker_counts"].get("wlan0")) == 0
        and not private["wlan0_up"]
    )

    if not current_modem_selection:
        return "current-selection-review", "v1849-current-selection-review", "V1848 current-route modem-selection evidence is missing or inconsistent", False
    if not private_route_reaches_esoc0:
        return "private-route-review", "v1849-private-route-review", "Historical private SDX50M route did not prove eSoC PM path reachability", False
    if not private_guardrails_clean:
        return "private-guardrail-review", "v1849-private-guardrail-review", "Historical private SDX50M route crossed a Wi-Fi/network/flash guardrail", False
    if not lower_gap_confirmed:
        return "lower-gap-review", "v1849-lower-gap-review", "Historical post-eSoC lower-gap classifiers are missing or inconsistent", False
    if not followup_guardrails_clean:
        return "followup-guardrail-review", "v1849-followup-guardrail-review", "Historical follow-up classifiers crossed a Wi-Fi/network/flash guardrail", False
    if not no_lower_publication:
        return "lower-publication-review", "v1849-lower-publication-review", "Historical private route appears to have lower WLFW/MHI/wlan0 publication", False
    return (
        "private-sdx50m-route-known-lower-gap",
        "v1849-private-sdx50m-route-known-lower-gap-host-pass",
        "The private SDX50M CNSS route is known to change PM selection and reach eSoC powerup, but prior evidence already moves the blocker below /dev/subsys_esoc0 before GPIO142/PCIe/WLFW/wlan0 publication",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    current = result["details"]["current"]
    private = result["details"]["v1221"]
    v1222 = result["details"]["v1222"]
    v1223 = result["details"]["v1223"]
    v1239 = result["details"]["v1239"]
    return "\n".join([
        "# Native Init V1849 SDX50M Private Route Reuse Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only reconciliation of current CNSS selection and historical private-SDX50M lower-gap evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Current Route",
        "",
        f"- V1848 decision/label: `{current['decision']}` / `{current['label']}`",
        f"- Current requested/candidates: `{current['requested_values']}` / `{current['candidate_values']}`",
        f"- Current PM map: `{current['pm_map']}`",
        f"- Current open/lower: `{current['open_context_path']}` fd `{current['open_context_fd']}` / `{current['post_pm_lower_state_label']}`",
        "",
        "## Historical Private Route",
        "",
        f"- V1221 decision: `{private['decision']}` / pass `{private['pass']}`",
        f"- Private daemon bind/source: rc `{private['private_cnss_daemon'].get('bind_rc')}` / `{private['private_cnss_daemon'].get('source')}`",
        f"- Patched daemon SHA: `{private['patched_cnss_sha256']}`",
        f"- CNSS registrations: `{private['cnss_registered_peripherals']}`",
        f"- eSoC route: per_mgr_esoc0 `{private['per_mgr_esoc0_any']}` pm_actor `{private['pm_actor_executed']}` mdm_subsys_powerup `{private['mdm_subsys_powerup_any']}`",
        f"- late PM wchans: `{private['late_pm_wchans']}`",
        f"- lower publication: mdm3 `{private['mdm3_after_observer']}` markers `{private['marker_counts']}` wlan0_up `{private['wlan0_up']}`",
        f"- V1221 guardrails: `{private['guardrails']}`",
        "",
        "## Lower-Gap Follow-Up",
        "",
        f"- V1222: `{v1222['decision']}` / `{v1222['reason']}`",
        f"- V1223: `{v1223['decision']}` / `{v1223['reason']}`",
        f"- V1239: `{v1239['decision']}` / `{v1239['reason']}`",
        f"- V1239 checks: `{v1239['checks']}`",
        "",
        "## Interpretation",
        "",
        "- Repeating the private SDX50M CNSS route is not an information-gaining next live step by itself; V1221 already proved it changes PM selection and reaches the eSoC powerup path.",
        "- The known failure is below PM-service eSoC open: native lacks the downstream GPIO142/PCIe/SSCTL/MHI/WLFW/`wlan0` response that Android gets.",
        "- The current safe next unit should classify the lower response-input contract from source or existing evidence before any live route that can cause another `/dev/subsys_esoc0` powerup attempt.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next source-only unit: join Android positive response inputs with native lower-gap evidence around `mdm_subsys_powerup`, especially GPIO142, PCIe RC1, SSCTL/sysmon, MHI pipe creation, and `ks` lifetime/order.",
        "",
    ])


def main() -> int:
    details = {
        "current": collect_current(load_json(V1848_MANIFEST)),
        "v1221": collect_v1221(load_json(V1221_MANIFEST)),
        "v1222": collect_followup(load_json(V1222_MANIFEST), V1222_MANIFEST),
        "v1223": collect_followup(load_json(V1223_MANIFEST), V1223_MANIFEST),
        "v1239": collect_followup(load_json(V1239_MANIFEST), V1239_MANIFEST),
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
