#!/usr/bin/env python3
"""V948 host-only classifier for V947 provider-readiness evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v948-v947-provider-readiness-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v948-v947-provider-readiness-classifier.txt")
DEFAULT_V947_MANIFEST = Path("tmp/wifi/v947-provider-readiness-capture-live/manifest.json")
DEFAULT_V867_REPORT = Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md")
DEFAULT_V933_REPORT = Path("docs/reports/NATIVE_INIT_V933_CNSS_SERVICE_MANAGER_BEFORE_CNSS_LIVE_2026-05-26.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v947-manifest", type=Path, default=DEFAULT_V947_MANIFEST)
    parser.add_argument("--v867-report", type=Path, default=DEFAULT_V867_REPORT)
    parser.add_argument("--v933-report", type=Path, default=DEFAULT_V933_REPORT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("helper") or {}


def provider(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("provider_readiness") or {}


def queue_timing(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("queue_timing") or {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("contract") or {}


def val(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_provider_readiness.{phase}.{suffix}", "")


def qval(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_queue_timing.{phase}.{suffix}", "")


def classify(v947: dict[str, Any], v867_report: str, v933_report: str) -> dict[str, Any]:
    provider_data = provider(v947)
    timing_data = queue_timing(v947)
    contract_data = contract(v947)
    live_phases = ["after_per_mgr_settle", "after_mdm_helper_spawn", "window", "final"]
    steady_phases = ["after_per_mgr_settle", "window", "final"]
    binder_nodes_ready = all(
        val(provider_data, phase, "path.binder.exists") == "1"
        and val(provider_data, phase, "path.hwbinder.exists") == "1"
        and val(provider_data, phase, "path.vndbinder.exists") == "1"
        for phase in live_phases
    )
    property_socket_ready = all(
        val(provider_data, phase, "path.property_service_socket.exists") == "1"
        and val(provider_data, phase, "path.property_service_socket.socket") == "1"
        for phase in live_phases
    )
    per_mgr_vndbinder_open = all(
        val(provider_data, phase, "per_mgr_vndbinder_count") == "1"
        for phase in steady_phases
    )
    service_managers_absent = all(
        val(provider_data, phase, "servicemanager_count") == "0"
        and val(provider_data, phase, "hwservicemanager_count") == "0"
        and val(provider_data, phase, "vndservicemanager_count") == "0"
        for phase in live_phases
    )
    pm_proxy_absent = all(
        val(provider_data, phase, "pm_proxy_count") == "0"
        and val(provider_data, phase, "pm_proxy_helper_count") == "0"
        for phase in live_phases
    )
    per_mgr_no_subsys = all(
        qval(timing_data, phase, "per_mgr_subsys_modem_count") == "0"
        and qval(timing_data, phase, "per_mgr_subsys_esoc0_count") == "0"
        for phase in steady_phases
    )
    mdm_helper_esoc_observed = (
        qval(timing_data, "window", "mdm_helper_esoc0_count") == "1"
        and qval(timing_data, "final", "mdm_helper_esoc0_count") == "1"
    )
    pm_proxy_helper_dstate_risk = "`pm_proxy_helper` remained in D-state" in v867_report
    simple_service_manager_not_enough = "Simple service-manager ordering is no longer the remaining blocker" in v933_report
    provider_keys = len(provider_data)

    if (
        bool(v947.get("pass"))
        and provider_keys > 0
        and contract_data.get("result") == "mdm-helper-esoc-fd-observed"
        and binder_nodes_ready
        and property_socket_ready
        and per_mgr_vndbinder_open
        and service_managers_absent
        and pm_proxy_absent
        and per_mgr_no_subsys
        and mdm_helper_esoc_observed
        and pm_proxy_helper_dstate_risk
        and simple_service_manager_not_enough
    ):
        decision = "v948-provider-surface-present-matrix-instrumentation-selected"
        pass_ok = True
        reason = (
            "binder/property surfaces and per_mgr vndbinder fd are present, but service-manager/proxy lifecycle is absent in V947 and prior matrix evidence says service-manager alone is not enough"
        )
        next_step = (
            "add provider-readiness diagnostics to the existing CNSS/service-manager matrix path; do not start pm_proxy_helper or open /dev/subsys_esoc0"
        )
    elif bool(v947.get("pass")) and provider_keys > 0:
        decision = "v948-provider-readiness-classified-needs-review"
        pass_ok = True
        reason = "provider-readiness evidence exists, but blocker correlation is incomplete"
        next_step = "inspect V947 evidence manually before selecting another live gate"
    else:
        decision = "v948-provider-readiness-evidence-missing"
        pass_ok = False
        reason = "V947 did not contain provider-readiness evidence"
        next_step = "repair or rerun V947 before another lower gate"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "provider_keys": provider_keys,
        "contract_result": contract_data.get("result"),
        "binder_nodes_ready": binder_nodes_ready,
        "property_socket_ready": property_socket_ready,
        "per_mgr_vndbinder_open": per_mgr_vndbinder_open,
        "service_managers_absent": service_managers_absent,
        "pm_proxy_absent": pm_proxy_absent,
        "per_mgr_no_subsys": per_mgr_no_subsys,
        "mdm_helper_esoc_observed": mdm_helper_esoc_observed,
        "pm_proxy_helper_dstate_risk": pm_proxy_helper_dstate_risk,
        "simple_service_manager_not_enough": simple_service_manager_not_enough,
        "selected_phases": {
            phase: {
                "servicemanager_count": val(provider_data, phase, "servicemanager_count"),
                "hwservicemanager_count": val(provider_data, phase, "hwservicemanager_count"),
                "vndservicemanager_count": val(provider_data, phase, "vndservicemanager_count"),
                "pm_service_count": val(provider_data, phase, "pm_service_count"),
                "pm_proxy_count": val(provider_data, phase, "pm_proxy_count"),
                "pm_proxy_helper_count": val(provider_data, phase, "pm_proxy_helper_count"),
                "per_mgr_vndbinder_count": val(provider_data, phase, "per_mgr_vndbinder_count"),
                "mdm_helper_vndbinder_count": val(provider_data, phase, "mdm_helper_vndbinder_count"),
                "per_mgr_subsys_modem_count": qval(timing_data, phase, "per_mgr_subsys_modem_count"),
                "per_mgr_subsys_esoc0_count": qval(timing_data, phase, "per_mgr_subsys_esoc0_count"),
                "mdm_helper_esoc0_count": qval(timing_data, phase, "mdm_helper_esoc0_count"),
            }
            for phase in live_phases
        },
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "subsys_esoc0_open_executed": False,
            "esoc_ioctl_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credentials_used": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write": False,
            "partition_write": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["provider_keys", str(classification["provider_keys"])],
        ["contract_result", str(classification["contract_result"])],
        ["binder_nodes_ready", str(classification["binder_nodes_ready"])],
        ["property_socket_ready", str(classification["property_socket_ready"])],
        ["per_mgr_vndbinder_open", str(classification["per_mgr_vndbinder_open"])],
        ["service_managers_absent", str(classification["service_managers_absent"])],
        ["pm_proxy_absent", str(classification["pm_proxy_absent"])],
        ["per_mgr_no_subsys", str(classification["per_mgr_no_subsys"])],
        ["mdm_helper_esoc_observed", str(classification["mdm_helper_esoc_observed"])],
        ["pm_proxy_helper_dstate_risk", str(classification["pm_proxy_helper_dstate_risk"])],
        ["simple_service_manager_not_enough", str(classification["simple_service_manager_not_enough"])],
    ]
    phase_rows = []
    for phase, data in classification["selected_phases"].items():
        phase_rows.append(
            [
                phase,
                data["servicemanager_count"],
                data["hwservicemanager_count"],
                data["vndservicemanager_count"],
                data["pm_service_count"],
                data["pm_proxy_count"],
                data["pm_proxy_helper_count"],
                data["per_mgr_vndbinder_count"],
                data["per_mgr_subsys_modem_count"],
                data["per_mgr_subsys_esoc0_count"],
                data["mdm_helper_esoc0_count"],
            ]
        )
    return "\n".join(
        [
            "# V948 V947 Provider-Readiness Classifier Summary",
            "",
            f"decision: {classification['decision']}",
            f"pass: {classification['pass']}",
            f"reason: {classification['reason']}",
            f"next: {classification['next_step']}",
            "",
            "## Markers",
            "",
            markdown_table(["marker", "value"], rows),
            "",
            "## Phases",
            "",
            markdown_table(
                [
                    "phase",
                    "svc",
                    "hwsvc",
                    "vndsvc",
                    "pm_service",
                    "pm_proxy",
                    "pm_proxy_helper",
                    "pm_vndbinder",
                    "pm_subsys_modem",
                    "pm_subsys_esoc0",
                    "mdm_esoc0",
                ],
                phase_rows,
            ),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v947 = load_json(args.v947_manifest)
    v867_report = read_text(args.v867_report)
    v933_report = read_text(args.v933_report)
    classification = classify(v947, v867_report, v933_report)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v947_manifest": str(repo_path(args.v947_manifest)),
        "v867_report": str(repo_path(args.v867_report)),
        "v933_report": str(repo_path(args.v933_report)),
        "classification": classification,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
