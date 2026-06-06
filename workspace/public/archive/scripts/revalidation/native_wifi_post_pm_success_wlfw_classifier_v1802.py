#!/usr/bin/env python3
"""V1802 host-only classifier for V1801 post-PM-success WLFW state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_wlan_pd_pm_service_count_sample_handoff_v1796 as prev1796


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1802"
SOURCE_DIR = REPO_ROOT / "tmp" / "wifi" / "v1801-pm-service-devnode-projection-handoff"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1802-post-pm-success-wlfw-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1802_POST_PM_SUCCESS_WLFW_CLASSIFIER_2026-06-03.md"
)

UPROBE_PREFIX = "wlan_pd_cnss_nonlog_control_flow.uprobe."


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def intish(value: object) -> int:
    return prev1796.intish(value)


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = UPROBE_PREFIX + name + "."
    return {
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "register_rc": fields.get(prefix + "register_rc", ""),
        "enable_rc": fields.get(prefix + "enable_rc", ""),
    }


def classify(fields: dict[str, str], source_manifest: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    wlfw_start = event(fields, "wlfw_start")
    wlfw_service_request = event(fields, "wlfw_service_request")
    wlfw_ind_register = event(fields, "wlfw_ind_register_qmi")
    wlfw_cap = event(fields, "wlfw_cap_qmi")
    dms_service_request = event(fields, "dms_service_request")
    dms_init_call = event(fields, "wlfw_dms_initialize_call")
    dms_init_retcheck = event(fields, "wlfw_dms_initialize_retcheck")
    worker_create_call = event(fields, "wlfw_worker_pthread_create_call")
    worker_create_success = event(fields, "wlfw_worker_pthread_create_success")
    worker_create_failure = event(fields, "wlfw_worker_pthread_create_failure")
    pm_client_register = event(fields, "pm_init_pm_client_register_call")
    pm_client_register_ret = event(fields, "pm_init_pm_client_register_retcheck")
    pm_client_connect = event(fields, "pm_init_pm_client_connect_call")
    pm_client_connect_ret = event(fields, "pm_init_pm_client_connect_retcheck")
    nonlog_label = fields.get("wlan_pd_cnss_nonlog_control_flow.label", "")
    details: dict[str, Any] = {
        "source_decision": source_manifest.get("decision", ""),
        "source_pass": bool(source_manifest.get("pass")),
        "source_projection_label": source_manifest.get("gate", {}).get("pm_service_devnode_projection_label", ""),
        "source_pm_server_label": source_manifest.get("gate", {}).get("pm_server_label", ""),
        "source_list_commit_hits": source_manifest.get("gate", {}).get("pm_service_add_peripheral_list_commit_hits", ""),
        "source_pm_register_success_hits": source_manifest.get("gate", {}).get("pm_server_success_return_hits", ""),
        "nonlog_label": nonlog_label,
        "requested_wlanmdsp": fields.get("wlan_pd_service_object_visible_trigger.requested_wlanmdsp", ""),
        "wlfw_service69_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_service69_seen", ""),
        "wlan0_present": fields.get("wlan_pd_service_object_visible_trigger.wlan0_present", ""),
        "wlfw_start_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_start_seen", ""),
        "wlfw_service_request_seen": fields.get("wlan_pd_service_object_visible_trigger.wlfw_service_request_seen", ""),
        "wlfw_start": wlfw_start,
        "wlfw_service_request": wlfw_service_request,
        "wlfw_ind_register_qmi": wlfw_ind_register,
        "wlfw_cap_qmi": wlfw_cap,
        "dms_service_request": dms_service_request,
        "wlfw_dms_initialize_call": dms_init_call,
        "wlfw_dms_initialize_retcheck": dms_init_retcheck,
        "wlfw_worker_pthread_create_call": worker_create_call,
        "wlfw_worker_pthread_create_success": worker_create_success,
        "wlfw_worker_pthread_create_failure": worker_create_failure,
        "pm_init_pm_client_register_call": pm_client_register,
        "pm_init_pm_client_register_retcheck": pm_client_register_ret,
        "pm_init_pm_client_connect_call": pm_client_connect,
        "pm_init_pm_client_connect_retcheck": pm_client_connect_ret,
    }

    if not bool(source_manifest.get("pass")):
        return "source-v1801-not-pass", "V1801 source manifest was not PASS", details
    if intish(source_manifest.get("gate", {}).get("pm_service_add_peripheral_list_commit_hits")) <= 0:
        return "pm-service-list-not-committed", "V1801 did not prove PM-service list commit", details
    if intish(wlfw_start.get("hit_count")) <= 0:
        return "wlfw-start-missing-after-pm-success", "PM-service succeeded but `wlfw_start` did not run", details
    if intish(wlfw_service_request.get("hit_count")) <= 0:
        return "wlfw-worker-missing-after-pm-success", "`wlfw_start` ran but `wlfw_service_request` did not", details
    if intish(wlfw_ind_register.get("hit_count")) > 0 or intish(wlfw_cap.get("hit_count")) > 0:
        return "wlfw-qmi-send-progress", "WLFW worker reached first QMI send path", details
    if intish(dms_service_request.get("hit_count")) > 0:
        return "wlfw-worker-waiting-for-qmi-service", "WLFW worker started and DMS request ran, but WLFW indication/capability QMI sends did not", details
    return "wlfw-worker-started-no-qmi-service-discriminator", "WLFW worker started but QMI service wait discriminator was incomplete", details


def render_event(name: str, data: dict[str, str]) -> list[str]:
    return [
        f"- `{name}` hits/registered/enabled: `{data.get('hit_count')}` / `{data.get('registered')}` / `{data.get('enabled')}`",
        f"- `{name}` first hit: `{data.get('first_hit_line')}`",
    ]


def render_report(result: dict[str, Any]) -> str:
    details = result["details"]
    lines = [
        "# Native Init V1802 Post-PM-success WLFW Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1802`",
        "- Type: host-only classifier over V1801 rollback-verified helper evidence",
        f"- Decision: `{result['decision']}`",
        "- Result: PASS",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        f"- Source evidence: `{details['source_dir']}`",
        "",
        "## Source Gate",
        "",
        f"- V1801 decision: `{details['source_decision']}`",
        f"- projection label: `{details['source_projection_label']}`",
        f"- PM server label: `{details['source_pm_server_label']}`",
        f"- list commit hits: `{details['source_list_commit_hits']}`",
        f"- PM register success hits: `{details['source_pm_register_success_hits']}`",
        "",
        "## WLFW State",
        "",
        f"- non-log label: `{details['nonlog_label']}`",
        f"- requested `wlanmdsp`: `{details['requested_wlanmdsp']}`",
        f"- WLFW service 69 seen: `{details['wlfw_service69_seen']}`",
        f"- wlan0 present: `{details['wlan0_present']}`",
        f"- summary wlfw start/service-request: `{details['wlfw_start_seen']}` / `{details['wlfw_service_request_seen']}`",
        *render_event("wlfw_start", details["wlfw_start"]),
        *render_event("wlfw_service_request", details["wlfw_service_request"]),
        *render_event("dms_service_request", details["dms_service_request"]),
        *render_event("wlfw_ind_register_qmi", details["wlfw_ind_register_qmi"]),
        *render_event("wlfw_cap_qmi", details["wlfw_cap_qmi"]),
        "",
        "## PM-client Path",
        "",
        *render_event("pm_init_pm_client_register_call", details["pm_init_pm_client_register_call"]),
        *render_event("pm_init_pm_client_register_retcheck", details["pm_init_pm_client_register_retcheck"]),
        *render_event("pm_init_pm_client_connect_call", details["pm_init_pm_client_connect_call"]),
        *render_event("pm_init_pm_client_connect_retcheck", details["pm_init_pm_client_connect_retcheck"]),
        "",
        "## Interpretation",
        "",
        "- V1801 fixed the PM-service list/register blocker and reached `wlfw_start` plus `wlfw_service_request`.",
        "- The current blocker is downstream of WLFW worker start and before WLFW indication/capability QMI sends, while WLFW service 69 and `wlanmdsp.mbn` request remain absent.",
        "- The next unit should classify QMI service readiness/wait state without starting Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    source_manifest_path = SOURCE_DIR / "manifest.json"
    if not source_manifest_path.exists():
        raise SystemExit(f"missing source manifest: {source_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    fields = prev1796.runner.fwbase.parse_helper_fields(SOURCE_DIR)
    label, reason, details = classify(fields, source_manifest)
    details["source_dir"] = rel(SOURCE_DIR)
    result = {
        "cycle": CYCLE,
        "decision": f"v1802-{label}-host-pass",
        "pass": True,
        "reason": reason,
        "source_manifest": rel(source_manifest_path),
        "out_dir": rel(OUT_DIR),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_report(result), encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "pass": True, "label": label}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
