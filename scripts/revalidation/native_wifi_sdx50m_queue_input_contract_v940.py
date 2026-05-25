#!/usr/bin/env python3
"""V940 host-only SDX50M queue input contract classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v940-sdx50m-queue-input-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v940-sdx50m-queue-input-contract.txt")
DEFAULT_V938_MANIFEST = Path("tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json")
DEFAULT_V939_MANIFEST = Path("tmp/wifi/v939-v938-lower-contract-classifier/manifest.json")
DEFAULT_V914_MANIFEST = Path("tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json")

PM_REPORTS = {
    "v857": Path("docs/reports/NATIVE_INIT_V857_PM_SERVICE_PROPERTY_CONTRACT_2026-05-25.md"),
    "v860": Path("docs/reports/NATIVE_INIT_V860_PM_SERVICE_PROPERTY_SUPERSET_2026-05-25.md"),
    "v861": Path("docs/reports/NATIVE_INIT_V861_PM_SERVICE_DOMAIN_PARITY_2026-05-25.md"),
    "v867": Path("docs/reports/NATIVE_INIT_V867_PM_INIT_CONTRACT_START_ONLY_2026-05-25.md"),
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v938-manifest", type=Path, default=DEFAULT_V938_MANIFEST)
    parser.add_argument("--v939-manifest", type=Path, default=DEFAULT_V939_MANIFEST)
    parser.add_argument("--v914-manifest", type=Path, default=DEFAULT_V914_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})


def post_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("post_surface") or {}


def queue_lines(v938: dict[str, Any]) -> list[str]:
    return [
        line
        for line in post_surface(v938).get("wlfw_or_wlan_dmesg_hits", [])
        if "unable to queue event for SDX50M" in line
    ]


def report_flags(reports: dict[str, str]) -> dict[str, Any]:
    v857 = reports.get("v857", "")
    v860 = reports.get("v860", "")
    v861 = reports.get("v861", "")
    v867 = reports.get("v867", "")
    return {
        "v857_shutdown_critical_allowed": "previously denied shutdown-critical-list writes succeeded" in v857,
        "v857_no_subsys_hold": "no fd targets remained by capture time" in v857,
        "v860_property_denials_zero": "property denial total | `0`" in v860,
        "v860_pm_service_no_subsys_hold": "`pm-service` holds `/dev/subsys_esoc0` | `false`" in v860,
        "v861_runtime_attr_kernel": (
            "`attr/current` remains `kernel`" in v861
            or "| `pm-service` runtime `attr/current` | `kernel` |" in v861
        ),
        "v861_pm_service_exit_zero": "`pm-service` exit code | `0`" in v861,
        "v867_init_contract_executed": "init_contract | `1`" in v867,
        "v867_ioprio_ok": "`per_mgr` ioprio result | `ok=1 errno=0`" in v867,
        "v867_pm_proxy_helper_dstate": "`pm_proxy_helper` remained in D-state" in v867,
        "v867_per_mgr_no_fd_retained": "`per_mgr` still did not hold `/dev/subsys_esoc0`" in v867,
    }


def classify(v938: dict[str, Any], v939: dict[str, Any], v914: dict[str, Any], reports: dict[str, str]) -> dict[str, Any]:
    c = contract(v938)
    pm = report_flags(reports)
    qlines = queue_lines(v938)
    v939_decision = str(v939.get("decision"))
    android = v914.get("classification") or {}

    actor = {
        "mdm_helper_esoc_fd": c.get("fd_esoc0_count.final") == "1",
        "mdm_helper_esoc_fd_window": c.get("fd_esoc0_count.window") == "1",
        "ks_absent": c.get("ks_count.final") == "0",
        "mhi_pipe_absent": c.get("fd_mhi_pipe_count.final") == "0",
        "per_mgr_observable": c.get("per_mgr_light.observable") == "1",
        "per_mgr_postflight_safe": c.get("per_mgr_light.postflight_safe") == "1",
        "per_mgr_precleanup_safe": c.get("per_mgr_light.postflight_safe_precleanup") == "1",
        "service_manager_started": c.get("service_manager_start_executed") == "1",
        "pm_proxy_helper_started": c.get("pm_proxy_helper_start_executed") == "1",
        "queue_failure_count": len(qlines),
    }

    pm_property_closed = bool(pm["v857_shutdown_critical_allowed"] and pm["v860_property_denials_zero"])
    pm_lifetime_gap_open = bool(
        pm["v860_pm_service_no_subsys_hold"]
        and pm["v861_runtime_attr_kernel"]
        and pm["v867_pm_proxy_helper_dstate"]
    )
    android_upper_positive = bool(android.get("pass")) and bool(android.get("boot_complete"))
    property_not_next = v939_decision == "v939-exact-property-context-gap-not-sufficient"

    if (
        bool(v938.get("pass"))
        and actor["mdm_helper_esoc_fd"]
        and actor["ks_absent"]
        and actor["mhi_pipe_absent"]
        and actor["per_mgr_observable"]
        and actor["queue_failure_count"] > 0
        and pm_property_closed
        and pm_lifetime_gap_open
        and property_not_next
        and android_upper_positive
    ):
        decision = "v940-pm-provider-queue-timing-instrumentation-selected"
        pass_ok = True
        reason = (
            "property-context and PM property-denial blockers are closed as first responses; "
            "native reaches /dev/esoc-0 but queues SDX50M failures while PM/provider lifetime remains the open correlated gap"
        )
        next_step = (
            "add helper v156 source/build-only queue-timing diagnostics around per_mgr/provider state and mdm_helper "
            "before any /dev/subsys_esoc0, eSoC notify, Wi-Fi HAL, or scan/connect retry"
        )
    elif bool(v938.get("pass")) and actor["queue_failure_count"] > 0:
        decision = "v940-queue-failure-classified-needs-review"
        pass_ok = True
        reason = "queue failures are present, but existing PM evidence does not fully select the next instrumentation point"
        next_step = "refresh Android/PM evidence or inspect reports before implementing helper changes"
    else:
        decision = "v940-queue-failure-evidence-missing"
        pass_ok = False
        reason = "V938 evidence does not show the expected SDX50M queue failure"
        next_step = "rerun or repair V938 evidence before V940 classification"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "actor": actor,
        "pm_flags": pm,
        "pm_property_closed": pm_property_closed,
        "pm_lifetime_gap_open": pm_lifetime_gap_open,
        "property_context_not_next": property_not_next,
        "android_upper_positive": android_upper_positive,
        "queue_lines": qlines,
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "daemon_start_executed": False,
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
    actor_rows = [[key, str(value)] for key, value in classification["actor"].items()]
    pm_rows = [[key, str(value)] for key, value in classification["pm_flags"].items()]
    return "\n".join(
        [
            "# V940 SDX50M Queue Input Contract Summary",
            "",
            f"decision: {classification['decision']}",
            f"pass: {classification['pass']}",
            f"reason: {classification['reason']}",
            f"next: {classification['next_step']}",
            "",
            "## Actor Surface",
            "",
            markdown_table(["marker", "value"], actor_rows),
            "",
            "## PM Evidence Flags",
            "",
            markdown_table(["marker", "value"], pm_rows),
            "",
            "## Queue Lines",
            "",
            "```text",
            "\n".join(classification["queue_lines"]),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v938 = load_json(args.v938_manifest)
    v939 = load_json(args.v939_manifest)
    v914 = load_json(args.v914_manifest)
    reports = {name: read_text(path) for name, path in PM_REPORTS.items()}
    classification = classify(v938, v939, v914, reports)
    manifest = {
        "schema": "v940-sdx50m-queue-input-contract",
        "created_at": now_iso(),
        "inputs": {
            "v938_manifest": str(args.v938_manifest),
            "v939_manifest": str(args.v939_manifest),
            "v914_manifest": str(args.v914_manifest),
            "pm_reports": {name: str(path) for name, path in PM_REPORTS.items()},
        },
        "host": collect_host_metadata(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "classification": classification,
        "guardrails": classification["guardrails"],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
