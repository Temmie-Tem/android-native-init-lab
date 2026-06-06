#!/usr/bin/env python3
"""V958 host-only classifier for V957 pm-proxy matrix evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v958-v957-pm-proxy-matrix-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v958-v957-pm-proxy-matrix-classifier.txt")
DEFAULT_V957_MANIFEST = Path("tmp/wifi/v957-pm-proxy-matrix-live/manifest.json")
DEFAULT_V953_MANIFEST = Path("tmp/wifi/v953-matrix-provider-readiness-after-mdm-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v957-manifest", type=Path, default=DEFAULT_V957_MANIFEST)
    parser.add_argument("--v953-manifest", type=Path, default=DEFAULT_V953_MANIFEST)
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


def classify(v957: dict[str, Any], v953: dict[str, Any]) -> dict[str, Any]:
    p957 = provider(v957)
    p953 = provider(v953)
    c957 = contract(v957)
    key_phases = (
        "cnss_before_esoc_after_service_manager_start",
        "cnss_before_esoc_after_cnss_daemon_start",
    )
    v957_provider_persisted = all(
        val(p957, phase, "pm_service_count") == "1"
        and val(p957, phase, "pm_proxy_count") == "1"
        and val(p957, phase, "per_mgr_vndbinder_count") == "1"
        for phase in key_phases
    )
    v953_provider_degraded = all(
        val(p953, phase, "pm_service_count") == "0"
        and val(p953, phase, "per_mgr_vndbinder_count") == "0"
        for phase in key_phases
    )
    pm_proxy_clean = (
        c957.get("pm_proxy_start_attempted") == "1"
        and c957.get("pm_proxy_started") == "1"
        and c957.get("pm_proxy.postflight_safe") == "1"
        and c957.get("pm_proxy_helper_start_executed") == "0"
    )
    fail_closed = (
        c957.get("subsys_esoc0_open_attempted") == "0"
        and c957.get("wifi_hal_start_executed") == "0"
        and c957.get("scan_connect_linkup") == "0"
        and c957.get("credentials") == "0"
        and c957.get("dhcp_routing") == "0"
        and c957.get("external_ping") == "0"
        and bool(v957.get("pass"))
    )
    wlfw_missing = (
        c957.get("wlfw_precondition_observed") == "0"
        and c957.get("result") == "wlfw-precondition-missing-no-open"
    )
    if v957_provider_persisted and v953_provider_degraded and pm_proxy_clean and fail_closed and wlfw_missing:
        decision = "v958-provider-lifecycle-repaired-wlfw-gap-remains"
        pass_ok = True
        reason = (
            "pm-proxy preserves pm-service/provider surface through service-manager and CNSS start, but WLFW precondition still never appears"
        )
        next_step = (
            "run a bounded full-surface pm-proxy matrix capture to classify the post-provider WLFW/CNSS gap before any pm_proxy_helper, subsystem open, HAL, scan, DHCP, or external ping"
        )
    else:
        decision = "v958-pm-proxy-matrix-needs-review"
        pass_ok = bool(v957.get("pass"))
        reason = "V957 evidence exists but provider persistence or fail-closed markers are incomplete"
        next_step = "inspect V957 evidence manually before expanding live actions"
    phases = (
        "cnss_before_esoc_after_per_mgr_settle",
        "cnss_before_esoc_after_pm_proxy_start",
        "cnss_before_esoc_after_mdm_helper_spawn",
        "cnss_before_esoc_after_service_manager_start",
        "cnss_before_esoc_after_cnss_daemon_start",
        "cnss_before_esoc_final",
    )
    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "provider_keys": len(p957),
        "v957_provider_persisted": v957_provider_persisted,
        "v953_provider_degraded": v953_provider_degraded,
        "pm_proxy_clean": pm_proxy_clean,
        "fail_closed": fail_closed,
        "wlfw_missing": wlfw_missing,
        "selected_phases": {
            phase: {
                "svc": val(p957, phase, "servicemanager_count"),
                "hwsvc": val(p957, phase, "hwservicemanager_count"),
                "vndsvc": val(p957, phase, "vndservicemanager_count"),
                "pm_service": val(p957, phase, "pm_service_count"),
                "pm_proxy": val(p957, phase, "pm_proxy_count"),
                "pm_proxy_helper": val(p957, phase, "pm_proxy_helper_count"),
                "per_mgr_vndbinder": val(p957, phase, "per_mgr_vndbinder_count"),
            }
            for phase in phases
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
    c = manifest["classification"]
    rows = [
        ["provider_keys", str(c["provider_keys"])],
        ["v957_provider_persisted", str(c["v957_provider_persisted"])],
        ["v953_provider_degraded", str(c["v953_provider_degraded"])],
        ["pm_proxy_clean", str(c["pm_proxy_clean"])],
        ["fail_closed", str(c["fail_closed"])],
        ["wlfw_missing", str(c["wlfw_missing"])],
    ]
    phase_rows = [
        [
            phase,
            data["svc"],
            data["hwsvc"],
            data["vndsvc"],
            data["pm_service"],
            data["pm_proxy"],
            data["pm_proxy_helper"],
            data["per_mgr_vndbinder"],
        ]
        for phase, data in c["selected_phases"].items()
    ]
    return "\n".join(
        [
            "# V958 V957 PM-Proxy Matrix Classifier Summary",
            "",
            f"decision: {c['decision']}",
            f"pass: {c['pass']}",
            f"reason: {c['reason']}",
            f"next: {c['next_step']}",
            "",
            "## Markers",
            "",
            markdown_table(["marker", "value"], rows),
            "",
            "## V957 Provider Phases",
            "",
            markdown_table(
                ["phase", "svc", "hwsvc", "vndsvc", "pm_service", "pm_proxy", "pm_proxy_helper", "pm_vndbinder"],
                phase_rows,
            ),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v957 = load_json(args.v957_manifest)
    v953 = load_json(args.v953_manifest)
    classification = classify(v957, v953)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v957_manifest": str(repo_path(args.v957_manifest)),
        "v953_manifest": str(repo_path(args.v953_manifest)),
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
