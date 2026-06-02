#!/usr/bin/env python3
"""Host-only V1741 classifier for the WLAN-PD cnss-daemon route delta."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1741-wlan-pd-route-delta-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1741_WLAN_PD_ROUTE_DELTA_CLASSIFIER_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

V1736_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
V1736_HELPER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1736-wlan-pd-timestamped-observer-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
V1736_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1736_WLAN_PD_TIMESTAMPED_OBSERVER_HANDOFF_2026-06-03.md"
)
V1740_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1740-wlan-pd-cnss-output-source-handoff" / "manifest.json"
V1740_HELPER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1740-wlan-pd-cnss-output-source-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
V1740_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1740_WLAN_PD_CNSS_OUTPUT_SOURCE_HANDOFF_2026-06-03.md"
)


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def intish(value: Any) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ok"}


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$"):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value
    return values


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def report_has_safety(report: str, phrase: str) -> bool:
    return phrase in report


def collect_evidence() -> dict[str, Any]:
    v1736 = load_json(V1736_MANIFEST)
    v1740 = load_json(V1740_MANIFEST)
    v1736_gate = v1736.get("gate", {})
    v1740_gate = v1740.get("gate", {})
    v1736_kv = parse_kv(read_text(V1736_HELPER))
    v1740_kv = parse_kv(read_text(V1740_HELPER))
    v1736_report = read_text(V1736_REPORT)
    v1740_report = read_text(V1740_REPORT)

    return {
        "service_manager_route_v1736": {
            "manifest": str(V1736_MANIFEST.relative_to(REPO_ROOT)),
            "helper": str(V1736_HELPER.relative_to(REPO_ROOT)),
            "report": str(V1736_REPORT.relative_to(REPO_ROOT)),
            "decision": v1736.get("decision"),
            "pass": boolish(v1736.get("pass")),
            "rollback_ok": boolish(v1736.get("rollback", {}).get("ok")),
            "with_service_manager": intish(v1736_kv.get("wifi_companion_start.with_service_manager")),
            "with_vnd_service_manager": intish(v1736_kv.get("wifi_companion_start.with_vnd_service_manager")),
            "service_manager_started": intish(v1736_kv.get("wifi_companion_start.service_manager_started")),
            "service_manager": intish(v1736_gate.get("service_manager")),
            "pm_trio": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.pm_trio")),
            "boot_wlan": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.boot_wlan")),
            "subsys_esoc0": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.subsys_esoc0")),
            "forced_rc1": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.forced_rc1")),
            "fake_online": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.fake_online")),
            "wifi_hal": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.wifi_hal")),
            "scan_connect": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.scan_connect")),
            "credentials": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.credentials")),
            "dhcp_routes": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.dhcp_routes")),
            "external_ping": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.external_ping")),
            "service_window_label": v1736_gate.get("service_window_label"),
            "nonlog_label": v1736_gate.get("nonlog_label"),
            "old_firmware_serve_label": v1736_gate.get("old_firmware_serve_label"),
            "cnss_daemon_running": intish(v1736_gate.get("cnss_daemon_running")),
            "tftp_running": intish(v1736_gate.get("tftp_running")),
            "wlfw_start_seen": intish(v1736_gate.get("wlfw_start_seen")),
            "wlfw_start_hits": intish(v1736_gate.get("wlfw_start_hit_count")),
            "wlfw_service_request_hits": intish(v1736_gate.get("wlfw_service_request_hit_count")),
            "worker_success_hits": intish(v1736_gate.get("wlfw_worker_create_success_hit_count")),
            "wlfw_ind_register_qmi_hits": intish(v1736_gate.get("wlfw_ind_register_qmi_hit_count")),
            "wlfw_cap_qmi_hits": intish(v1736_gate.get("wlfw_cap_qmi_hit_count")),
            "wlfw_service69_seen": intish(v1736_gate.get("wlfw_service69_seen")),
            "requested_wlanmdsp": intish(v1736_gate.get("requested_wlanmdsp")),
            "late_listener_state": v1736_gate.get("late_listener_state"),
            "late_listener_indication_seen": intish(v1736_gate.get("late_listener_indication_seen")),
            "tracefs_available": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available")),
            "uprobe_attempted": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")),
            "uprobe_hit_count": intish(v1736_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count")),
            "safety_report_no_pm_boot_wlan": report_has_safety(
                v1736_report,
                "PM trio, `vendor.qcom.PeripheralManager` actor, `boot_wlan`, restart-PD request",
            ),
        },
        "pure_internal_modem_route_v1740": {
            "manifest": str(V1740_MANIFEST.relative_to(REPO_ROOT)),
            "helper": str(V1740_HELPER.relative_to(REPO_ROOT)),
            "report": str(V1740_REPORT.relative_to(REPO_ROOT)),
            "decision": v1740.get("decision"),
            "pass": boolish(v1740.get("pass")),
            "rollback_ok": boolish(v1740.get("rollback", {}).get("ok")),
            "with_service_manager": intish(v1740_kv.get("wifi_companion_start.with_service_manager")),
            "with_vnd_service_manager": intish(v1740_kv.get("wifi_companion_start.with_vnd_service_manager")),
            "service_manager_started": intish(v1740_kv.get("wifi_companion_start.service_manager_started")),
            "no_service_manager": intish(v1740_gate.get("no_service_manager")),
            "no_pm_trio": intish(v1740_gate.get("no_pm_trio")),
            "no_esoc0": intish(v1740_gate.get("no_esoc0")),
            "no_forced_rc1": intish(v1740_gate.get("no_forced_rc1")),
            "no_fake_online": intish(v1740_gate.get("no_fake_online")),
            "no_scan_connect": intish(v1740_gate.get("no_scan_connect")),
            "no_credentials": intish(v1740_gate.get("no_credentials")),
            "no_dhcp_routes": intish(v1740_gate.get("no_dhcp_routes")),
            "no_external_ping": intish(v1740_gate.get("no_external_ping")),
            "label": v1740_gate.get("label"),
            "nonlog_label": v1740_gate.get("nonlog_label"),
            "old_firmware_serve_label": v1740_gate.get("old_firmware_serve_label"),
            "property_lookup_all_match": intish(v1740_gate.get("property_lookup_all_match")),
            "cnss_daemon_running": intish(v1740_gate.get("cnss_daemon_running")),
            "tftp_running": intish(v1740_gate.get("tftp_running")),
            "stdout_bytes": intish(v1740_gate.get("stdout_bytes")),
            "stderr_bytes": intish(v1740_gate.get("stderr_bytes")),
            "wlfw_start_seen": intish(v1740_gate.get("wlfw_start_seen")),
            "wlfw_start_source": v1740_gate.get("wlfw_start_source"),
            "wlfw_start_stdout_count": intish(v1740_gate.get("wlfw_start_stdout_count")),
            "wlfw_start_stderr_count": intish(v1740_gate.get("wlfw_start_stderr_count")),
            "wlfw_start_kmsg_count": intish(v1740_gate.get("wlfw_start_kmsg_count")),
            "first_failure_slug": v1740_gate.get("first_failure_slug"),
            "failure_nl_loop_total": intish(v1740_gate.get("failure_nl_loop_stdout"))
            + intish(v1740_gate.get("failure_nl_loop_stderr"))
            + intish(v1740_gate.get("failure_nl_loop_kmsg")),
            "failure_netlink_common_total": intish(v1740_gate.get("failure_netlink_common_stdout"))
            + intish(v1740_gate.get("failure_netlink_common_stderr"))
            + intish(v1740_gate.get("failure_netlink_common_kmsg")),
            "failure_wlan_service_total": intish(v1740_gate.get("failure_wlan_service_stdout"))
            + intish(v1740_gate.get("failure_wlan_service_stderr"))
            + intish(v1740_gate.get("failure_wlan_service_kmsg")),
            "failure_wlan_datapath_total": intish(v1740_gate.get("failure_wlan_datapath_stdout"))
            + intish(v1740_gate.get("failure_wlan_datapath_stderr"))
            + intish(v1740_gate.get("failure_wlan_datapath_kmsg")),
            "wlfw_service69_seen": intish(v1740_kv.get("wlan_pd_firmware_serve_gate.wlfw_service69_seen")),
            "requested_wlanmdsp": intish(v1740_kv.get("wlan_pd_firmware_serve_gate.requested_wlanmdsp")),
            "tracefs_available": intish(v1740_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available")),
            "uprobe_attempted": intish(v1740_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")),
            "uprobe_hit_count": intish(v1740_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count")),
        },
    }


def classify(evidence: dict[str, Any]) -> tuple[str, str, dict[str, bool]]:
    service_route = evidence["service_manager_route_v1736"]
    pure_route = evidence["pure_internal_modem_route_v1740"]
    checks = {
        "both_runs_passed_and_rolled_back": service_route["pass"]
        and service_route["rollback_ok"]
        and pure_route["pass"]
        and pure_route["rollback_ok"],
        "route_delta_is_service_manager_surface": service_route["with_service_manager"] == 1
        and service_route["service_manager_started"] == 1
        and service_route["service_manager"] == 1
        and pure_route["with_service_manager"] == 0
        and pure_route["service_manager_started"] == 0
        and pure_route["no_service_manager"] == 1,
        "pm_boot_wlan_esoc_stayed_excluded": service_route["pm_trio"] == 0
        and service_route["boot_wlan"] == 0
        and service_route["subsys_esoc0"] == 0
        and pure_route["no_pm_trio"] == 1
        and pure_route["no_esoc0"] == 1
        and service_route["safety_report_no_pm_boot_wlan"],
        "wifi_connection_actions_stayed_excluded": all(
            service_route[key] == 0
            for key in ("wifi_hal", "scan_connect", "credentials", "dhcp_routes", "external_ping")
        )
        and all(
            pure_route[key] == 1
            for key in ("no_scan_connect", "no_credentials", "no_dhcp_routes", "no_external_ping")
        ),
        "pure_route_output_source_visible_but_no_wlfw": pure_route["label"] == "cnss-output-still-invisible"
        and pure_route["property_lookup_all_match"] == 1
        and pure_route["stdout_bytes"] > 0
        and pure_route["stderr_bytes"] > 0
        and pure_route["wlfw_start_seen"] == 0
        and pure_route["wlfw_start_source"] == "none"
        and pure_route["first_failure_slug"] == "none",
        "pure_route_no_named_init_failure": all(
            pure_route[key] == 0
            for key in (
                "failure_nl_loop_total",
                "failure_netlink_common_total",
                "failure_wlan_service_total",
                "failure_wlan_datapath_total",
            )
        ),
        "service_route_reaches_wlfw_worker": service_route["service_window_label"] == "wlfw-start-reached"
        and service_route["nonlog_label"] == "wlfw-worker-thread-started-waiting-for-qmi-service"
        and service_route["wlfw_start_seen"] == 1
        and service_route["wlfw_start_hits"] > 0
        and service_route["wlfw_service_request_hits"] > 0
        and service_route["worker_success_hits"] > 0,
        "service_route_stops_before_wlfw_qmi": service_route["wlfw_ind_register_qmi_hits"] == 0
        and service_route["wlfw_cap_qmi_hits"] == 0,
        "both_routes_still_firmware_not_requested": service_route["old_firmware_serve_label"] == "firmware-not-requested"
        and service_route["requested_wlanmdsp"] == 0
        and service_route["wlfw_service69_seen"] == 0
        and pure_route["old_firmware_serve_label"] == "firmware-not-requested"
        and pure_route["requested_wlanmdsp"] == 0
        and pure_route["wlfw_service69_seen"] == 0,
        "service_route_wlan_pd_still_uninit": service_route["late_listener_state"] == "uninit"
        and service_route["late_listener_indication_seen"] == 0,
    }
    if all(checks.values()):
        return (
            "v1741-service-manager-route-enables-cnss-wlfw-entry-not-wlan-pd-pass",
            "service-manager-route-enables-cnss-wlfw-entry-not-wlan-pd",
            checks,
        )
    return "v1741-route-delta-evidence-incomplete", "route-delta-evidence-incomplete", checks


def render_report(manifest: dict[str, Any]) -> str:
    service_route = manifest["evidence"]["service_manager_route_v1736"]
    pure_route = manifest["evidence"]["pure_internal_modem_route_v1740"]
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1741 WLAN-PD Route Delta Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1741`",
            "- Type: host-only route-delta classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Label: `{manifest['label']}`",
            "- Evidence: `tmp/wifi/v1741-wlan-pd-route-delta-classifier`",
            "",
            "## Compared Routes",
            "",
            "### V1740 pure internal-modem route",
            "",
            f"- decision: `{pure_route['decision']}`",
            f"- output label / non-log label: `{pure_route['label']}` / `{pure_route['nonlog_label']}`",
            f"- service-manager / PM trio / eSoC excluded: `{pure_route['no_service_manager']}` / `{pure_route['no_pm_trio']}` / `{pure_route['no_esoc0']}`",
            f"- property lookup all_match: `{pure_route['property_lookup_all_match']}`",
            f"- stdout/stderr bytes: `{pure_route['stdout_bytes']}` / `{pure_route['stderr_bytes']}`",
            f"- `wlfw_start` source/counts: `{pure_route['wlfw_start_source']}` / `{pure_route['wlfw_start_stdout_count']}` stdout, `{pure_route['wlfw_start_stderr_count']}` stderr, `{pure_route['wlfw_start_kmsg_count']}` kmsg",
            f"- first failure slug: `{pure_route['first_failure_slug']}`",
            f"- WLFW service 69 / requested `wlanmdsp`: `{pure_route['wlfw_service69_seen']}` / `{pure_route['requested_wlanmdsp']}`",
            "",
            "### V1736 service-manager route",
            "",
            f"- decision: `{service_route['decision']}`",
            f"- service-window label / non-log label: `{service_route['service_window_label']}` / `{service_route['nonlog_label']}`",
            f"- service-manager requested/started: `{service_route['with_service_manager']}` / `{service_route['service_manager_started']}`",
            f"- PM trio / `boot_wlan` / eSoC: `{service_route['pm_trio']}` / `{service_route['boot_wlan']}` / `{service_route['subsys_esoc0']}`",
            f"- `wlfw_start` / `wlfw_service_request` / worker hits: `{service_route['wlfw_start_hits']}` / `{service_route['wlfw_service_request_hits']}` / `{service_route['worker_success_hits']}`",
            f"- WLFW indication-register QMI / capability QMI hits: `{service_route['wlfw_ind_register_qmi_hits']}` / `{service_route['wlfw_cap_qmi_hits']}`",
            f"- WLAN-PD listener state / indication: `{service_route['late_listener_state']}` / `{service_route['late_listener_indication_seen']}`",
            f"- WLFW service 69 / requested `wlanmdsp`: `{service_route['wlfw_service69_seen']}` / `{service_route['requested_wlanmdsp']}`",
            "",
            "## Classification",
            "",
            "V1741 fixes the route-level delta: adding the service-manager/private-runtime surface makes stock `cnss-daemon` reach `wlfw_start`, issue `wlfw_service_request`, and create the WLFW worker. That surface is not a WLAN-PD trigger: the same service-manager route still never reaches WLFW indication/capability QMI, WLAN-PD remains `UNINIT`, WLFW service 69 is absent, and no `wlanmdsp` request reaches the firmware-serve route.",
            "",
            "The pair does not prove which subcomponent inside the service-manager surface is minimal. It only proves the bounded route delta. Further minimization must be a separate source/build or host-only unit, not actor expansion in the pure V1740 branch.",
            "",
            "## Next Gate",
            "",
            "- V1742 should be host-only/source-build minimization of the service-manager route.",
            "- Compare V1727/V1729/V1731/V1736 evidence and helper code to identify whether the required surface is service-manager bootstrap, tracefs availability, vndbinder/service-manager readiness, or a private runtime side effect.",
            "- Do not add PM actors, `boot_wlan`, restart-PD, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "## Checks",
            "",
            checks,
            "",
            "## Safety Scope",
            "",
            "This script performed host-only analysis only. It did not contact the device, flash, reboot, send QMI payloads, start services, start `boot_wlan`, use `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1741 WLAN-PD route-delta classifier (2026-06-03)",
            "",
            "- V1741 host-only route-delta classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - label: `{manifest['label']}`;",
            "  - V1740 pure internal-modem route remains `cnss-output-still-invisible` with no named pre-WLFW init failure string;",
            "  - V1736 service-manager route reaches `wlfw_start`, `wlfw_service_request`, and WLFW worker creation;",
            "  - both routes still end at `firmware-not-requested`, no WLFW service 69, no `wlanmdsp` request, and no `wlan0`;",
            "  - the service-manager/private-runtime surface is therefore a `cnss-daemon` entry enabler, not a WLAN-PD/WLFW publication trigger.",
            "",
            "  Next candidate:",
            "",
            "  - V1742 host-only/source-build minimization of the service-manager route;",
            "  - compare V1727/V1729/V1731/V1736 evidence and helper code for the minimal surface behind `wlfw_start` reachability;",
            "  - forbidden: PM actor expansion, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1741_WLAN_PD_ROUTE_DELTA_CLASSIFIER_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    heading = "## V1741 WLAN-PD route-delta classifier"
    if heading in current:
        pattern = re.compile(
            r"\n## V1741 WLAN-PD route-delta classifier \(2026-06-03\)\n.*?(?=\n## |\Z)",
            re.S,
        )
        updated = pattern.sub(entry, current.rstrip())
        NEXT_WORK_PATH.write_text(updated.rstrip() + "\n", encoding="utf-8")
    else:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    evidence = collect_evidence()
    decision, label, checks = classify(evidence)
    pass_ok = all(checks.values())
    manifest = {
        "cycle": "V1741",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "evidence": evidence,
        "checks": checks,
        "next_gate": "V1742 host-only/source-build service-manager route minimization"
        if pass_ok
        else "refresh route-delta evidence",
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": decision, "pass": pass_ok}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
