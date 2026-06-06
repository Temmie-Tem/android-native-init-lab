#!/usr/bin/env python3
"""V952 host-only classifier for V951 matrix provider-readiness evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v952-v951-matrix-provider-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v952-v951-matrix-provider-classifier.txt")
DEFAULT_V951_MANIFEST = Path("tmp/wifi/v951-matrix-provider-readiness-before-cnss-live/manifest.json")
DEFAULT_V947_MANIFEST = Path("tmp/wifi/v947-provider-readiness-capture-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v951-manifest", type=Path, default=DEFAULT_V951_MANIFEST)
    parser.add_argument("--v947-manifest", type=Path, default=DEFAULT_V947_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("helper") or {}


def provider(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("provider_readiness") or {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("contract") or {}


def val(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_provider_readiness.{phase}.{suffix}", "")


def classify(v951: dict[str, Any], v947: dict[str, Any]) -> dict[str, Any]:
    p951 = provider(v951)
    c951 = contract(v951)
    p947 = provider(v947)
    service_phases = [
        "cnss_before_esoc_after_service_manager_start",
        "cnss_before_esoc_after_per_mgr_settle",
        "cnss_before_esoc_after_mdm_helper_spawn",
        "cnss_before_esoc_after_cnss_daemon_start",
        "cnss_before_esoc_final",
    ]
    runtime_phases = ["after_per_mgr_settle", "window", "final"]
    service_managers_present = all(
        val(p951, phase, "servicemanager_count") == "1"
        and val(p951, phase, "hwservicemanager_count") == "1"
        and val(p951, phase, "vndservicemanager_count") == "1"
        for phase in service_phases
    )
    before_cnss_pm_absent = all(
        val(p951, phase, "pm_service_count") == "0"
        for phase in service_phases
    )
    before_cnss_per_mgr_no_fds = all(
        val(p951, phase, "per_mgr_vndbinder_count") == "-1"
        for phase in service_phases
    )
    runtime_pm_alive = all(
        val(p947, phase, "pm_service_count") == "1"
        and val(p947, phase, "per_mgr_vndbinder_count") == "1"
        for phase in runtime_phases
    )
    mdm_esoc_seen = c951.get("mdm_helper_esoc0_fd_seen") == "1"
    wlfw_missing = c951.get("result") == "wlfw-precondition-missing-no-open"
    safe_fail_closed = (
        c951.get("subsys_esoc0_open_attempted") == "0"
        and c951.get("wifi_hal_start_executed") == "0"
        and c951.get("external_ping") == "0"
        and bool(v951.get("pass"))
    )

    if (
        len(p951) > 0
        and service_managers_present
        and before_cnss_pm_absent
        and before_cnss_per_mgr_no_fds
        and runtime_pm_alive
        and mdm_esoc_seen
        and wlfw_missing
        and safe_fail_closed
    ):
        decision = "v952-after-mdm-helper-esoc-fd-provider-comparator-selected"
        pass_ok = True
        reason = (
            "before-cnss matrix starts service managers but pm-service is absent by provider snapshots, while V947 runtime-contract preserves pm-service/vndbinder"
        )
        next_step = (
            "run the same v158 provider-readiness matrix with service-manager order after-mdm-helper-esoc-fd; keep pm_proxy_helper, /dev/subsys_esoc0, HAL, scan, DHCP, and external ping blocked"
        )
    elif len(p951) > 0:
        decision = "v952-matrix-provider-classified-needs-review"
        pass_ok = True
        reason = "V951 provider-readiness evidence exists, but ordering implication is incomplete"
        next_step = "inspect V951 manually before selecting another matrix order"
    else:
        decision = "v952-matrix-provider-evidence-missing"
        pass_ok = False
        reason = "V951 did not contain provider-readiness evidence"
        next_step = "repair or rerun V951 before another matrix order"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "provider_keys": len(p951),
        "service_managers_present": service_managers_present,
        "before_cnss_pm_absent": before_cnss_pm_absent,
        "before_cnss_per_mgr_no_fds": before_cnss_per_mgr_no_fds,
        "runtime_pm_alive": runtime_pm_alive,
        "mdm_esoc_seen": mdm_esoc_seen,
        "wlfw_missing": wlfw_missing,
        "safe_fail_closed": safe_fail_closed,
        "selected_phases": {
            phase: {
                "servicemanager_count": val(p951, phase, "servicemanager_count"),
                "hwservicemanager_count": val(p951, phase, "hwservicemanager_count"),
                "vndservicemanager_count": val(p951, phase, "vndservicemanager_count"),
                "pm_service_count": val(p951, phase, "pm_service_count"),
                "per_mgr_vndbinder_count": val(p951, phase, "per_mgr_vndbinder_count"),
                "pm_proxy_count": val(p951, phase, "pm_proxy_count"),
                "pm_proxy_helper_count": val(p951, phase, "pm_proxy_helper_count"),
            }
            for phase in service_phases
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
        ["service_managers_present", str(classification["service_managers_present"])],
        ["before_cnss_pm_absent", str(classification["before_cnss_pm_absent"])],
        ["before_cnss_per_mgr_no_fds", str(classification["before_cnss_per_mgr_no_fds"])],
        ["runtime_pm_alive", str(classification["runtime_pm_alive"])],
        ["mdm_esoc_seen", str(classification["mdm_esoc_seen"])],
        ["wlfw_missing", str(classification["wlfw_missing"])],
        ["safe_fail_closed", str(classification["safe_fail_closed"])],
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
                data["per_mgr_vndbinder_count"],
                data["pm_proxy_count"],
                data["pm_proxy_helper_count"],
            ]
        )
    return "\n".join(
        [
            "# V952 V951 Matrix Provider Classifier Summary",
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
                    "pm_vndbinder",
                    "pm_proxy",
                    "pm_proxy_helper",
                ],
                phase_rows,
            ),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v951 = load_json(args.v951_manifest)
    v947 = load_json(args.v947_manifest)
    classification = classify(v951, v947)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v951_manifest": str(repo_path(args.v951_manifest)),
        "v947_manifest": str(repo_path(args.v947_manifest)),
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
