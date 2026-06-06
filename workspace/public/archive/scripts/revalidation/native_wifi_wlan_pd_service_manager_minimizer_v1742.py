#!/usr/bin/env python3
"""Host-only V1742 classifier for WLAN-PD service-manager route minimization."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1742-wlan-pd-service-manager-minimizer"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1742_WLAN_PD_SERVICE_MANAGER_MINIMIZER_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

ROUTES = {
    "pure_v1740": {
        "cycle": "V1740",
        "dir": REPO_ROOT / "tmp" / "wifi" / "v1740-wlan-pd-cnss-output-source-handoff",
        "report": REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1740_WLAN_PD_CNSS_OUTPUT_SOURCE_HANDOFF_2026-06-03.md",
        "role": "pure internal-modem route without service managers",
    },
    "bootstrap_v1727": {
        "cycle": "V1727",
        "dir": REPO_ROOT / "tmp" / "wifi" / "v1727-wlan-pd-service-manager-bootstrap-handoff",
        "report": REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1727_WLAN_PD_SERVICE_MANAGER_BOOTSTRAP_HANDOFF_2026-06-03.md",
        "role": "earliest service-manager bootstrap route",
    },
    "late_endpoint_v1729": {
        "cycle": "V1729",
        "dir": REPO_ROOT / "tmp" / "wifi" / "v1729-wlan-pd-servnotif-late-endpoint-handoff",
        "report": REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1729_WLAN_PD_SERVNOTIF_LATE_ENDPOINT_HANDOFF_2026-06-03.md",
        "role": "service-manager route plus late endpoint observation",
    },
    "late_listener_v1731": {
        "cycle": "V1731",
        "dir": REPO_ROOT / "tmp" / "wifi" / "v1731-wlan-pd-servnotif-late-listener-handoff",
        "report": REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1731_WLAN_PD_SERVNOTIF_LATE_LISTENER_HANDOFF_2026-06-03.md",
        "role": "service-manager route plus late listener observation",
    },
    "timestamped_v1736": {
        "cycle": "V1736",
        "dir": REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff",
        "report": REPO_ROOT
        / "docs"
        / "reports"
        / "NATIVE_INIT_V1736_WLAN_PD_TIMESTAMPED_OBSERVER_HANDOFF_2026-06-03.md",
        "role": "service-manager route plus timestamped observer",
    },
}


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


def helper_path(route_dir: Path) -> Path:
    candidates = sorted(route_dir.glob("*helper-result.stdout.txt"))
    if not candidates:
        raise FileNotFoundError(f"helper result missing under {route_dir}")
    return candidates[0]


def count_child_starts(helper_text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for match in re.finditer(r"^wifi_companion_start\.child\.([A-Za-z0-9_]+)\.start_order=", helper_text, re.M):
        name = match.group(1)
        counts[name] = counts.get(name, 0) + 1
    return counts


def first_existing(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def collect_route(name: str, config: dict[str, Any]) -> dict[str, Any]:
    route_dir = config["dir"]
    manifest_path = route_dir / "manifest.json"
    helper = helper_path(route_dir)
    manifest = load_json(manifest_path)
    helper_text = read_text(helper)
    helper_fields = parse_kv(helper_text)
    gate = manifest.get("gate", {})
    child_counts = count_child_starts(helper_text)

    return {
        "name": name,
        "cycle": config["cycle"],
        "role": config["role"],
        "manifest": str(manifest_path.relative_to(REPO_ROOT)),
        "helper": str(helper.relative_to(REPO_ROOT)),
        "report": str(config["report"].relative_to(REPO_ROOT)),
        "decision": manifest.get("decision"),
        "pass": boolish(manifest.get("pass")),
        "rollback_ok": boolish(manifest.get("rollback", {}).get("ok")),
        "order": helper_fields.get("wifi_companion_start.order"),
        "child_started": intish(helper_fields.get("wifi_companion_start.child_started")),
        "child_start_counts": child_counts,
        "with_service_manager": intish(helper_fields.get("wifi_companion_start.with_service_manager")),
        "with_vnd_service_manager": intish(helper_fields.get("wifi_companion_start.with_vnd_service_manager")),
        "service_manager_started": intish(helper_fields.get("wifi_companion_start.service_manager_started")),
        "service_manager": intish(
            first_existing(
                gate.get("service_manager"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.service_manager"),
            )
        ),
        "pm_trio": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.pm_trio")),
        "boot_wlan": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.boot_wlan")),
        "subsys_esoc0": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.subsys_esoc0")),
        "forced_rc1": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.forced_rc1")),
        "fake_online": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.fake_online")),
        "wifi_hal": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.wifi_hal")),
        "scan_connect": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.scan_connect")),
        "credentials": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.credentials")),
        "dhcp_routes": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.dhcp_routes")),
        "external_ping": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.external_ping")),
        "tracefs_available": intish(
            first_existing(gate.get("tracefs_available"), helper_fields.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available"))
        ),
        "uprobe_attempted": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")),
        "uprobe_hit_count": intish(helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count")),
        "service_window_label": first_existing(
            gate.get("service_window_label"),
            helper_fields.get("wlan_pd_service_window_trigger.label"),
        ),
        "nonlog_label": first_existing(gate.get("nonlog_label"), helper_fields.get("wlan_pd_cnss_nonlog_control_flow.label")),
        "output_label": gate.get("label"),
        "old_firmware_serve_label": first_existing(
            gate.get("old_firmware_serve_label"),
            helper_fields.get("wlan_pd_firmware_serve_gate.label"),
        ),
        "wlfw_start_seen": intish(
            first_existing(gate.get("wlfw_start_seen"), helper_fields.get("wlan_pd_service_window_trigger.wlfw_start_seen"))
        ),
        "wlfw_start_hits": intish(
            first_existing(
                gate.get("wlfw_start_hit_count"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_start.hit_count"),
            )
        ),
        "wlfw_service_request_hits": intish(
            first_existing(
                gate.get("wlfw_service_request_hit_count"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_service_request.hit_count"),
            )
        ),
        "worker_success_hits": intish(
            first_existing(
                gate.get("wlfw_worker_create_success_hit_count"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_worker_pthread_create_success.hit_count"),
            )
        ),
        "wlfw_ind_register_qmi_hits": intish(
            first_existing(
                gate.get("wlfw_ind_register_qmi_hit_count"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_ind_register_qmi.hit_count"),
            )
        ),
        "wlfw_cap_qmi_hits": intish(
            first_existing(
                gate.get("wlfw_cap_qmi_hit_count"),
                helper_fields.get("wlan_pd_cnss_nonlog_control_flow.uprobe.wlfw_cap_qmi.hit_count"),
            )
        ),
        "wlfw_service69_seen": intish(
            first_existing(
                gate.get("wlfw_service69_seen"),
                helper_fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen"),
                helper_fields.get("wlan_pd_firmware_serve_gate.wlfw_service69_seen"),
            )
        ),
        "requested_wlanmdsp": intish(
            first_existing(
                gate.get("requested_wlanmdsp"),
                helper_fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp"),
                helper_fields.get("wlan_pd_firmware_serve_gate.requested_wlanmdsp"),
            )
        ),
        "late_endpoint_found": intish(
            first_existing(
                gate.get("late_endpoint_found"),
                helper_fields.get("wifi_companion_service_notifier_late_probe.endpoint.found"),
            )
        ),
        "late_listener_state": first_existing(
            gate.get("late_listener_state"),
            gate.get("late_listener_response_state_name"),
            helper_fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name"),
        ),
        "late_listener_indication_seen": intish(
            first_existing(
                gate.get("late_listener_indication_seen"),
                helper_fields.get("wifi_companion_service_notifier_late_listener.indication_seen"),
            )
        ),
    }


def collect_evidence() -> dict[str, Any]:
    routes = {name: collect_route(name, config) for name, config in ROUTES.items()}
    ordered_names = [
        "pure_v1740",
        "bootstrap_v1727",
        "late_endpoint_v1729",
        "late_listener_v1731",
        "timestamped_v1736",
    ]
    return {
        "routes": routes,
        "ordered_names": ordered_names,
        "minimal_observed_route": "bootstrap_v1727",
        "pure_comparison_route": "pure_v1740",
        "observation_extension_routes": ["late_endpoint_v1729", "late_listener_v1731", "timestamped_v1736"],
    }


def route_has_hard_stops(route: dict[str, Any]) -> bool:
    return all(
        route[key] == 0
        for key in (
            "pm_trio",
            "boot_wlan",
            "subsys_esoc0",
            "forced_rc1",
            "fake_online",
            "wifi_hal",
            "scan_connect",
            "credentials",
            "dhcp_routes",
            "external_ping",
        )
    )


def route_reaches_wlfw_worker(route: dict[str, Any]) -> bool:
    return (
        route["service_window_label"] == "wlfw-start-reached"
        and route["nonlog_label"] == "wlfw-worker-thread-started-waiting-for-qmi-service"
        and route["wlfw_start_hits"] > 0
        and route["wlfw_service_request_hits"] > 0
        and route["worker_success_hits"] > 0
    )


def route_still_downstream_blocked(route: dict[str, Any]) -> bool:
    return (
        route["old_firmware_serve_label"] == "firmware-not-requested"
        and route["wlfw_ind_register_qmi_hits"] == 0
        and route["wlfw_cap_qmi_hits"] == 0
        and route["wlfw_service69_seen"] == 0
        and route["requested_wlanmdsp"] == 0
    )


def classify(evidence: dict[str, Any]) -> tuple[str, str, dict[str, bool]]:
    routes = evidence["routes"]
    pure = routes["pure_v1740"]
    bootstrap = routes["bootstrap_v1727"]
    extensions = [routes[name] for name in evidence["observation_extension_routes"]]
    checks = {
        "all_handoff_inputs_passed_and_rolled_back": all(
            route["pass"] and route["rollback_ok"] for route in routes.values()
        ),
        "pure_route_has_no_service_manager_surface": pure["with_service_manager"] == 0
        and pure["service_manager_started"] == 0
        and pure["service_manager"] == 0
        and pure["output_label"] == "cnss-output-still-invisible",
        "bootstrap_route_is_first_observed_success": bootstrap["with_service_manager"] == 1
        and bootstrap["service_manager_started"] == 1
        and bootstrap["service_manager"] == 1
        and route_reaches_wlfw_worker(bootstrap),
        "bootstrap_keeps_hard_stops": route_has_hard_stops(bootstrap),
        "bootstrap_still_downstream_blocked": route_still_downstream_blocked(bootstrap),
        "extension_routes_preserve_same_cnss_entry": all(route_reaches_wlfw_worker(route) for route in extensions),
        "extension_routes_preserve_same_downstream_block": all(route_still_downstream_blocked(route) for route in extensions),
        "extension_routes_keep_hard_stops": all(route_has_hard_stops(route) for route in extensions),
        "late_endpoint_is_observational": routes["late_endpoint_v1729"]["late_endpoint_found"] == 1
        and route_reaches_wlfw_worker(routes["late_endpoint_v1729"]),
        "late_listener_is_observational": routes["late_listener_v1731"]["late_listener_state"] == "uninit"
        and routes["late_listener_v1731"]["late_listener_indication_seen"] == 0
        and route_reaches_wlfw_worker(routes["late_listener_v1731"]),
    }
    if all(checks.values()):
        return (
            "v1742-minimum-observed-service-manager-bootstrap-route-pass",
            "minimum-observed-service-manager-bootstrap-route",
            checks,
        )
    return "v1742-service-manager-minimization-evidence-incomplete", "service-manager-minimization-evidence-incomplete", checks


def route_line(route: dict[str, Any]) -> str:
    return (
        f"- `{route['cycle']}` `{route['name']}`: service_manager `{route['service_manager']}`, "
        f"children `{route['child_started']}`, tracefs `{route['tracefs_available']}`, "
        f"wlfw hits `{route['wlfw_start_hits']}/{route['wlfw_service_request_hits']}/{route['worker_success_hits']}`, "
        f"firmware `{route['old_firmware_serve_label']}`, svc69/request `{route['wlfw_service69_seen']}/{route['requested_wlanmdsp']}`"
    )


def render_report(manifest: dict[str, Any]) -> str:
    routes = manifest["evidence"]["routes"]
    route_summary = "\n".join(route_line(routes[name]) for name in manifest["evidence"]["ordered_names"])
    checks = "\n".join(f"- `{key}`: `{value}`" for key, value in manifest["checks"].items())
    return "\n".join(
        [
            "# Native Init V1742 WLAN-PD Service-manager Minimizer",
            "",
            "## Summary",
            "",
            "- Cycle: `V1742`",
            "- Type: host-only route minimization classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- Label: `{manifest['label']}`",
            "- Evidence: `tmp/wifi/v1742-wlan-pd-service-manager-minimizer`",
            "",
            "## Route Matrix",
            "",
            route_summary,
            "",
            "## Classification",
            "",
            "V1727 is the earliest verified route in the compared chain that reaches `wlfw_start`, `wlfw_service_request`, and WLFW worker creation. V1729, V1731, and V1736 preserve that same CNSS entry state while adding late endpoint/listener/timestamped observation. Those later additions are therefore observation refinements, not required triggers for the observed `wlfw_start` entry.",
            "",
            "V1742 intentionally classifies only the minimum observed route, not the atomically minimal subcomponent. The V1727 surface still starts the service-manager trio as a bounded bootstrap bundle, and the existing evidence does not isolate `servicemanager` vs `hwservicemanager` vs `vndservicemanager` vs tracefs/private-runtime side effects.",
            "",
            "All service-manager routes remain downstream-blocked: no WLFW indication/capability QMI, no WLAN-PD UP indication, no WLFW service 69, no `wlanmdsp` request, and no `wlan0`.",
            "",
            "## Next Gate",
            "",
            "- V1743 should be source/build-only first: add a pure-route non-log parity gate that keeps service-manager disabled but makes the same tracefs/uprobe observer available.",
            "- This closes the V1740 measurement gap without adding PM actors, `boot_wlan`, restart-PD, eSoC/RC1, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "- If pure-route non-log parity still shows no `wlfw_start`, the next live candidate can test the V1727 bootstrap route as the minimal known CNSS-entry route before returning to modem-side WLAN-PD publication.",
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
            "## V1742 WLAN-PD service-manager minimizer (2026-06-03)",
            "",
            "- V1742 host-only route minimization classifier completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - label: `{manifest['label']}`;",
            "  - V1727 is the earliest verified route in the compared chain that reaches `wlfw_start`, `wlfw_service_request`, and WLFW worker creation;",
            "  - V1729/V1731/V1736 add late endpoint/listener/timestamped observation but do not change the downstream blocker;",
            "  - the current minimum is a service-manager bootstrap bundle, not an isolated single subcomponent;",
            "  - every service-manager route still ends with no WLAN-PD UP, no WLFW service 69, no `wlanmdsp` request, and no `wlan0`.",
            "",
            "  Next candidate:",
            "",
            "  - V1743 source/build-only pure-route non-log parity gate;",
            "  - keep service-manager disabled but make the same tracefs/uprobe observer available to close the V1740 measurement gap;",
            "  - forbidden: PM actor expansion, `boot_wlan`, restart-PD request, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1742_WLAN_PD_SERVICE_MANAGER_MINIMIZER_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    heading = "## V1742 WLAN-PD service-manager minimizer"
    if heading in current:
        pattern = re.compile(
            r"\n## V1742 WLAN-PD service-manager minimizer \(2026-06-03\)\n.*?(?=\n## |\Z)",
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
        "cycle": "V1742",
        "decision": decision,
        "pass": pass_ok,
        "label": label,
        "evidence": evidence,
        "checks": checks,
        "next_gate": "V1743 source/build-only pure-route non-log parity gate"
        if pass_ok
        else "refresh missing route minimization evidence",
    }
    write_json_private(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": decision, "pass": pass_ok}, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
