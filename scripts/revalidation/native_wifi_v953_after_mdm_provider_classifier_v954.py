#!/usr/bin/env python3
"""V954 host-only classifier for V953 after-mdm provider-readiness evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v954-v953-after-mdm-provider-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v954-v953-after-mdm-provider-classifier.txt")
DEFAULT_V953_MANIFEST = Path("tmp/wifi/v953-matrix-provider-readiness-after-mdm-live/manifest.json")
DEFAULT_V951_MANIFEST = Path("tmp/wifi/v951-matrix-provider-readiness-before-cnss-live/manifest.json")
DEFAULT_V856_REPORT = Path("docs/reports/NATIVE_INIT_V856_PM_SERVICE_NODE_PARITY_START_ONLY_2026-05-25.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v953-manifest", type=Path, default=DEFAULT_V953_MANIFEST)
    parser.add_argument("--v951-manifest", type=Path, default=DEFAULT_V951_MANIFEST)
    parser.add_argument("--v856-report", type=Path, default=DEFAULT_V856_REPORT)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("helper") or {}


def provider(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("provider_readiness") or {}


def contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("contract") or {}


def val(data: dict[str, str], phase: str, suffix: str) -> str:
    return data.get(f"mdm_helper_provider_readiness.{phase}.{suffix}", "")


def classify(v953: dict[str, Any], v951: dict[str, Any], v856_report: str) -> dict[str, Any]:
    p953 = provider(v953)
    c953 = contract(v953)
    p951 = provider(v951)
    pre_service_phases = [
        "cnss_before_esoc_after_per_mgr_settle",
        "cnss_before_esoc_after_mdm_helper_spawn",
    ]
    post_service_phases = [
        "cnss_before_esoc_after_service_manager_start",
        "cnss_before_esoc_after_cnss_daemon_start",
    ]
    pre_service_pm_alive = all(
        val(p953, phase, "pm_service_count") == "1"
        and val(p953, phase, "per_mgr_vndbinder_count") == "1"
        for phase in pre_service_phases
    )
    post_service_managers_present = all(
        val(p953, phase, "servicemanager_count") == "1"
        and val(p953, phase, "hwservicemanager_count") == "1"
        and val(p953, phase, "vndservicemanager_count") == "1"
        for phase in post_service_phases
    )
    post_service_pm_degraded = all(
        val(p953, phase, "pm_service_count") == "0"
        and val(p953, phase, "per_mgr_vndbinder_count") == "0"
        for phase in post_service_phases
    )
    before_cnss_pm_absent = all(
        val(p951, phase, "pm_service_count") == "0"
        for phase in (
            "cnss_before_esoc_after_per_mgr_settle",
            "cnss_before_esoc_after_mdm_helper_spawn",
            "cnss_before_esoc_after_cnss_daemon_start",
        )
    )
    pm_proxy_safe_precedent = (
        "pm-proxy` were observable" in v856_report
        and "cleanup unsafe" not in v856_report.split("`pm-proxy`", 1)[-1].split("##", 1)[0]
    )
    wlfw_missing = c953.get("result") == "wlfw-precondition-missing-no-open"
    safe_fail_closed = (
        c953.get("subsys_esoc0_open_attempted") == "0"
        and c953.get("wifi_hal_start_executed") == "0"
        and c953.get("external_ping") == "0"
        and bool(v953.get("pass"))
    )

    if (
        len(p953) > 0
        and pre_service_pm_alive
        and post_service_managers_present
        and post_service_pm_degraded
        and before_cnss_pm_absent
        and wlfw_missing
        and safe_fail_closed
    ):
        decision = "v954-pm-proxy-matrix-comparator-selected"
        pass_ok = True
        reason = (
            "after-mdm order preserves pm-service until service-manager start, then pm-service loses vndbinder/cmdline visibility and WLFW remains missing"
        )
        next_step = (
            "add a bounded matrix comparator that starts pm-proxy after per_mgr is observable; keep pm_proxy_helper, /dev/subsys_esoc0, HAL, scan, DHCP, and external ping blocked"
        )
    elif len(p953) > 0:
        decision = "v954-after-mdm-provider-classified-needs-review"
        pass_ok = True
        reason = "V953 provider-readiness evidence exists, but next lifecycle comparator is incomplete"
        next_step = "inspect V953 manually before selecting another actor"
    else:
        decision = "v954-after-mdm-provider-evidence-missing"
        pass_ok = False
        reason = "V953 did not contain provider-readiness evidence"
        next_step = "repair or rerun V953 before another matrix order"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "provider_keys": len(p953),
        "pre_service_pm_alive": pre_service_pm_alive,
        "post_service_managers_present": post_service_managers_present,
        "post_service_pm_degraded": post_service_pm_degraded,
        "before_cnss_pm_absent": before_cnss_pm_absent,
        "pm_proxy_safe_precedent": pm_proxy_safe_precedent,
        "wlfw_missing": wlfw_missing,
        "safe_fail_closed": safe_fail_closed,
        "selected_phases": {
            phase: {
                "servicemanager_count": val(p953, phase, "servicemanager_count"),
                "hwservicemanager_count": val(p953, phase, "hwservicemanager_count"),
                "vndservicemanager_count": val(p953, phase, "vndservicemanager_count"),
                "pm_service_count": val(p953, phase, "pm_service_count"),
                "per_mgr_vndbinder_count": val(p953, phase, "per_mgr_vndbinder_count"),
                "pm_proxy_count": val(p953, phase, "pm_proxy_count"),
                "pm_proxy_helper_count": val(p953, phase, "pm_proxy_helper_count"),
            }
            for phase in pre_service_phases + post_service_phases + ["cnss_before_esoc_final"]
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
        ["pre_service_pm_alive", str(classification["pre_service_pm_alive"])],
        ["post_service_managers_present", str(classification["post_service_managers_present"])],
        ["post_service_pm_degraded", str(classification["post_service_pm_degraded"])],
        ["before_cnss_pm_absent", str(classification["before_cnss_pm_absent"])],
        ["pm_proxy_safe_precedent", str(classification["pm_proxy_safe_precedent"])],
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
            "# V954 V953 After-MDM Provider Classifier Summary",
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
    v953 = load_json(args.v953_manifest)
    v951 = load_json(args.v951_manifest)
    v856_report = read_text(args.v856_report)
    classification = classify(v953, v951, v856_report)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v953_manifest": str(repo_path(args.v953_manifest)),
        "v951_manifest": str(repo_path(args.v951_manifest)),
        "v856_report": str(repo_path(args.v856_report)),
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
