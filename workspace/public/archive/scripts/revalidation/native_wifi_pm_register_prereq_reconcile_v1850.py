#!/usr/bin/env python3
"""V1850 host-only reconciliation of the old CNSS PM-register prerequisite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1850"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1850-pm-register-prereq-reconcile"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1850_PM_REGISTER_PREREQ_RECONCILE_2026-06-03.md"
)
V1349_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1349-cnss-wlfw-runtime-prereq-classifier"
    / "manifest.json"
)
V1841_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1841-pm-callback-ack-current-route-handoff"
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


def collect_v1349(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": rel(V1349_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "checks": manifest.get("checks") or [],
    }


def collect_v1841(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") or {}
    return {
        "path": rel(V1841_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "callback_ack_label": gate.get("callback_ack_label", ""),
        "callback_ack_hit_count_total": intish(gate.get("callback_ack_hit_count_total")),
        "lower_continuation_label": gate.get("lower_continuation_label", ""),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
    }


def collect_v1847(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") or {}
    register_call = gate.get("pm_init_pm_client_register_call") or {}
    register_retcheck = gate.get("pm_init_pm_client_register_retcheck") or {}
    return {
        "path": rel(V1847_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
        "pm_client_register_rc": intish(gate.get("pm_client_register_rc")),
        "pm_client_connect_rc": intish(gate.get("pm_client_connect_rc")),
        "pm_init_return_path_rc": intish(gate.get("pm_init_return_path_rc")),
        "register_call_hits": intish(register_call.get("hit_count")),
        "register_retcheck_hits": intish(register_retcheck.get("hit_count")),
        "register_retcheck_line": str(register_retcheck.get("first_hit_line", "")),
        "callback_ack_label": gate.get("callback_ack_label", ""),
        "post_ack_label": gate.get("post_ack_label", ""),
        "open_context_label": gate.get("open_context_label", ""),
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "lower_continuation_label": gate.get("lower_continuation_label", ""),
        "post_pm_lower_state_label": gate.get("post_pm_lower_state_label", ""),
        "lower_service69_progress": bool(gate.get("lower_service69_progress")),
        "lower_wlan0_present": bool(gate.get("lower_wlan0_present")),
    }


def collect_simple(path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": rel(path),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "reason": manifest.get("reason", ""),
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    old = details["v1349"]
    ack = details["v1841"]
    current = details["v1847"]
    selection = details["v1848"]
    private_route = details["v1849"]
    old_register_blocker = (
        old["pass"]
        and old["decision"] == "v1349-cnss-pm-register-blocker-is-next-prereq"
    )
    current_register_closed_for_modem = (
        current["pass"]
        and current["pm_client_register_rc"] == 0
        and current["pm_client_connect_rc"] == 0
        and current["pm_init_return_path_rc"] == 0
        and current["register_call_hits"] >= 1
        and current["register_retcheck_hits"] >= 1
        and current["callback_ack_label"] == "callback-ack-present-no-powerup"
        and current["post_ack_label"] == "post-ack-open-branch-reached"
        and current["open_context_label"] == "open-context-modem-success-static"
        and current["open_context_path"] == "/dev/subsys_modem"
        and intish(current["open_context_fd"]) >= 0
    )
    callback_not_blocker = (
        ack["pass"]
        and ack["decision"] == "v1841-callback-ack-present-no-powerup-rollback-pass"
        and ack["callback_ack_label"] == "callback-ack-present-no-powerup"
        and ack["callback_ack_hit_count_total"] > 0
    )
    still_no_lower_publication = (
        current["lower_continuation_label"] == "lower-continuation-static-gap"
        and current["post_pm_lower_state_label"] == "stable-mdm3-offlining"
        and not current["lower_service69_progress"]
        and not current["lower_wlan0_present"]
    )
    selection_is_modem = (
        selection["pass"]
        and selection["label"] == "cnss-pm-register-selects-modem-record"
        and selection["decision"] == "v1848-cnss-pm-register-selects-modem-not-sdx50m-host-pass"
    )
    private_sdx50m_not_next_by_itself = (
        private_route["pass"]
        and private_route["label"] == "private-sdx50m-route-known-lower-gap"
        and private_route["decision"] == "v1849-private-sdx50m-route-known-lower-gap-host-pass"
    )

    if not old_register_blocker:
        return "old-prereq-review", "v1850-old-prereq-review", "Historical V1349 PM-register prerequisite input is missing or inconsistent", False
    if not current_register_closed_for_modem:
        return "current-register-review", "v1850-current-register-review", "Current V1847 route does not prove PM register/connect/return closure for the modem record", False
    if not callback_not_blocker:
        return "callback-ack-review", "v1850-callback-ack-review", "Current callback/ack evidence is missing or inconsistent", False
    if not still_no_lower_publication:
        return "lower-publication-review", "v1850-lower-publication-review", "Current route shows lower WLFW/wlan0 publication; stop before any classifier conclusion", False
    if not selection_is_modem:
        return "selection-review", "v1850-selection-review", "Current selection evidence does not prove modem-record selection", False
    if not private_sdx50m_not_next_by_itself:
        return "private-route-review", "v1850-private-route-review", "Historical private SDX50M route reuse classification is missing or inconsistent", False
    return (
        "pm-register-prereq-closed-for-modem-selection-remains",
        "v1850-pm-register-prereq-closed-for-modem-selection-remains-host-pass",
        "The old CNSS PM-register/connect prerequisite is closed on the current modem-selected route, so the remaining branch is PM peripheral selection versus known lower SDX50M response gap, not another generic register helper/mutex observer",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    old = result["details"]["v1349"]
    ack = result["details"]["v1841"]
    current = result["details"]["v1847"]
    selection = result["details"]["v1848"]
    private_route = result["details"]["v1849"]
    return "\n".join([
        "# Native Init V1850 PM Register Prerequisite Reconcile",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only reconciliation of the historical CNSS PM-register prerequisite against current V184x evidence",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Historical Prerequisite",
        "",
        f"- V1349 decision: `{old['decision']}` / pass `{old['pass']}`",
        f"- V1349 reason: {old['reason']}",
        f"- V1349 next step then: `{old['next_step']}`",
        "",
        "## Current Closure",
        "",
        f"- V1841 callback/ack: `{ack['decision']}` / `{ack['callback_ack_label']}` hits `{ack['callback_ack_hit_count_total']}`",
        f"- V1847 register/connect/return rc: `{current['pm_client_register_rc']}` / `{current['pm_client_connect_rc']}` / `{current['pm_init_return_path_rc']}`",
        f"- V1847 register call/retcheck hits: `{current['register_call_hits']}` / `{current['register_retcheck_hits']}`",
        f"- V1847 retcheck line: `{current['register_retcheck_line']}`",
        f"- V1847 post-ack/open: `{current['post_ack_label']}` / `{current['open_context_path']}` fd `{current['open_context_fd']}`",
        f"- V1847 lower state: `{current['lower_continuation_label']}` / `{current['post_pm_lower_state_label']}` service69 `{current['lower_service69_progress']}` wlan0 `{current['lower_wlan0_present']}`",
        "",
        "## Remaining Branch",
        "",
        f"- V1848 selection: `{selection['decision']}` / `{selection['label']}`",
        f"- V1849 private route: `{private_route['decision']}` / `{private_route['label']}`",
        "",
        "## Interpretation",
        "",
        "- The generic CNSS PM-register/connect blocker from V1349 is stale for the current route: V1847 shows register/connect/return rc `0` and post-ack PM-service action.",
        "- That closure applies to the selected `modem` record; V1848 proves current CNSS still requests `modem`, so PM-service opens `/dev/subsys_modem`.",
        "- V1849 proves the private `SDX50M` selection route is already known to reach eSoC powerup but then falls into the lower MDM2AP/PCIe/WLFW response gap.",
        "- The next useful unit is not another broad PM-register observer and not a blind lower mutation; it is a source/build-only bridge between current PM closure and any future SDX50M-selection route gate.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next source/build-only unit: define a no-live SDX50M-selection bridge plan that reuses current PM closure instrumentation and explicitly gates any future live private-route run on lower-response guardrails.",
        "",
    ])


def main() -> int:
    details = {
        "v1349": collect_v1349(load_json(V1349_MANIFEST)),
        "v1841": collect_v1841(load_json(V1841_MANIFEST)),
        "v1847": collect_v1847(load_json(V1847_MANIFEST)),
        "v1848": collect_simple(V1848_MANIFEST, load_json(V1848_MANIFEST)),
        "v1849": collect_simple(V1849_MANIFEST, load_json(V1849_MANIFEST)),
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
