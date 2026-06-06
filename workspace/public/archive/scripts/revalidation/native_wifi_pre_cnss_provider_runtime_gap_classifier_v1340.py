#!/usr/bin/env python3
"""V1340 host-only classifier for the Android-order pre-CNSS provider gap.

Consumes the V1339 Android-order provider observer evidence and compares it
against earlier provider-positive/domain-fix evidence. No device command is
executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1340-pre-cnss-provider-runtime-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1340-pre-cnss-provider-runtime-gap-classifier.txt")
DEFAULT_V1339_MANIFEST = Path("tmp/wifi/v1339-android-pre-cnss-provider-observer-live/manifest.json")
DEFAULT_V1092_REPORT = Path("docs/reports/NATIVE_INIT_V1092_PM_PROVIDER_READY_2026-05-27.md")
DEFAULT_V1191_MANIFEST = Path("tmp/wifi/v1191-pm-per-mgr-policy-load/manifest.json")
DEFAULT_V1339_REPORT = Path("docs/reports/NATIVE_INIT_V1339_ANDROID_PRE_CNSS_PROVIDER_OBSERVER_2026-05-31.md")
EXPECTED_PER_MGR_DOMAIN = "u:r:vendor_per_mgr:s0"
EXPECTED_PER_PROXY_DOMAIN = "u:r:vendor_per_proxy:s0"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1339-manifest", type=Path, default=DEFAULT_V1339_MANIFEST)
    parser.add_argument("--v1339-report", type=Path, default=DEFAULT_V1339_REPORT)
    parser.add_argument("--v1092-report", type=Path, default=DEFAULT_V1092_REPORT)
    parser.add_argument("--v1191-manifest", type=Path, default=DEFAULT_V1191_MANIFEST)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    full = repo_path(path)
    if not full.exists():
        return {"_exists": False, "_path": str(path)}
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data["_exists"] = True
            data["_path"] = str(path)
            return data
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": str(path), "_json_error": str(exc)}
    return {"_exists": True, "_path": str(path), "_json_error": "top-level JSON is not object"}


def read_text(path: Path) -> str:
    full = repo_path(path)
    if not full.exists():
        return ""
    return full.read_text(encoding="utf-8", errors="replace")


def helper_keys(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    keys = helper.get("keys") or {}
    return {str(key): str(value) for key, value in keys.items()}


def helper_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "pass")


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1339 = read_json(args.v1339_manifest)
    v1191 = read_json(args.v1191_manifest)
    v1092_text = read_text(args.v1092_report)
    v1339_report_text = read_text(args.v1339_report)
    keys = helper_keys(v1339)
    contract = helper_contract(v1339)

    per_mgr_expected = keys.get("wifi_hal_composite_child.per_mgr.selinux_current.target_context", "")
    per_proxy_expected = keys.get("wifi_hal_composite_child.per_proxy.selinux_current.target_context", "")
    per_mgr_current_after = keys.get("wifi_hal_composite_child.per_mgr.selinux_current.after", "")
    per_proxy_current_after = keys.get("wifi_hal_composite_child.per_proxy.selinux_current.after", "")
    per_mgr_exec_after = keys.get("wifi_hal_composite_child.per_mgr.selinux.exec", "")
    per_proxy_exec_after = keys.get("wifi_hal_composite_child.per_proxy.selinux.exec", "")
    per_mgr_exit = contract.get("wifi_companion_start.child.per_mgr.exit_code") or keys.get("wifi_companion_start.child.per_mgr.exit_code", "")
    per_proxy_exit = contract.get("wifi_companion_start.child.per_proxy.exit_code") or keys.get("wifi_companion_start.child.per_proxy.exit_code", "")

    v1092_provider_positive = contains_any(
        v1092_text,
        (
            "v1092-pm-provider-registration-observed",
            "vendor_qcom_peripheral_manager_seen=1",
            "vendor.qcom.PeripheralManager",
        ),
    )
    v1092_policy_precondition = contains_any(
        v1092_text,
        (
            "V490 SELinux policy-load proof",
            "policy-load precondition",
            "v490-native-selinux-policy-load-proof",
            "V490 evidence",
        ),
    )
    v1191_reason = str(v1191.get("reason", ""))
    v1191_domain_fixed = (
        boolish(v1191.get("pass"))
        and v1191.get("decision") == "v1191-per-mgr-domain-fixed-gate-open"
        and EXPECTED_PER_MGR_DOMAIN in v1191_reason
    )
    v1339_report_mentions_next = "V1340 should be a host/live classifier" in v1339_report_text

    facts = {
        "v1339_manifest_exists": boolish(v1339.get("_exists")),
        "v1339_decision": v1339.get("decision", ""),
        "v1339_pass": boolish(v1339.get("pass")),
        "v1339_helper_result": contract.get("result", ""),
        "v1339_helper_reason": contract.get("reason", ""),
        "v1339_order": contract.get("order", ""),
        "v1339_per_mgr_exit": per_mgr_exit,
        "v1339_per_proxy_exit": per_proxy_exit,
        "v1339_per_mgr_expected_domain": per_mgr_expected,
        "v1339_per_mgr_current_after": per_mgr_current_after,
        "v1339_per_mgr_exec_after": per_mgr_exec_after,
        "v1339_per_proxy_expected_domain": per_proxy_expected,
        "v1339_per_proxy_current_after": per_proxy_current_after,
        "v1339_per_proxy_exec_after": per_proxy_exec_after,
        "v1339_manual_esoc_open": contract.get("manual_subsys_esoc0_open", ""),
        "v1339_wifi_hal": contract.get("wifi_hal", ""),
        "v1339_scan_connect": contract.get("scan_connect_linkup", ""),
        "v1339_external_ping": contract.get("external_ping", ""),
        "v1092_provider_positive": v1092_provider_positive,
        "v1092_policy_precondition": v1092_policy_precondition,
        "v1191_manifest_exists": boolish(v1191.get("_exists")),
        "v1191_domain_fixed": v1191_domain_fixed,
        "v1191_decision": v1191.get("decision", ""),
        "v1339_report_mentions_v1340": v1339_report_mentions_next,
    }
    flags = {
        "android_order_chain_started": facts["v1339_helper_result"] == "start-only-runtime-gap",
        "pm_children_exit_before_window": per_mgr_exit == "0" and per_proxy_exit == "1",
        "pm_domain_stuck_kernel": (
            per_mgr_current_after == "kernel"
            and per_proxy_current_after == "kernel"
            and per_mgr_expected == EXPECTED_PER_MGR_DOMAIN
            and per_proxy_expected == EXPECTED_PER_PROXY_DOMAIN
        ),
        "provider_positive_requires_policy_and_readiness": v1092_provider_positive and v1092_policy_precondition,
        "policy_load_domain_fix_known_good": v1191_domain_fixed,
        "guardrails_intact": (
            facts["v1339_manual_esoc_open"] == "0"
            and facts["v1339_wifi_hal"] == "0"
            and facts["v1339_scan_connect"] == "0"
            and facts["v1339_external_ping"] == "0"
        ),
    }
    if (
        flags["android_order_chain_started"]
        and flags["pm_children_exit_before_window"]
        and flags["pm_domain_stuck_kernel"]
        and flags["provider_positive_requires_policy_and_readiness"]
        and flags["policy_load_domain_fix_known_good"]
        and flags["guardrails_intact"]
    ):
        decision = "v1340-policy-load-vndservice-gate-gap-classified"
        passed = True
        reason = (
            "V1339 reproduced Android-order provider startup but PM children stayed in kernel SELinux "
            "context and exited before the window; earlier evidence shows provider registration needs "
            "V490 policy-load plus explicit vndservicemanager readiness/query."
        )
        next_step = (
            "V1341: add or run an Android-order pre-CNSS provider gate that refreshes V490, waits for "
            "vndservicemanager readiness/provider query, then starts pm_proxy_helper/per_mgr/per_proxy "
            "before mdm_helper/CNSS; keep HAL, scan/connect, credentials, DHCP/routes, external ping, "
            "manual eSoC open, PMIC/GPIO write, flash, and boot image writes blocked."
        )
    elif flags["pm_domain_stuck_kernel"]:
        decision = "v1340-domain-gap-classified-needs-policy-refresh"
        passed = True
        reason = "V1339 PM children stayed in kernel context; positive policy/readiness reference evidence is incomplete."
        next_step = "Refresh current-boot V490 policy-load and collect a provider readiness query before broader PM/CNSS work."
    else:
        decision = "v1340-provider-runtime-gap-unclassified"
        passed = False
        reason = "V1339 did not match the expected PM domain/lifecycle gap pattern."
        next_step = "Inspect V1339 helper transcript and add narrower PM child stdout/stderr/syscall capture."
    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "facts": facts,
        "flags": flags,
        "inputs": {
            "v1339_manifest": str(args.v1339_manifest),
            "v1339_report": str(args.v1339_report),
            "v1092_report": str(args.v1092_report),
            "v1191_manifest": str(args.v1191_manifest),
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    facts = manifest["classification"]["facts"]
    flags = manifest["classification"]["flags"]
    fact_rows = [[key, value] for key, value in facts.items()]
    flag_rows = [[key, value] for key, value in flags.items()]
    return "\n".join([
        "# V1340 Pre-CNSS Provider Runtime Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Interpretation",
        "",
        "V1339 did not fail because the Android-order provider actors were absent. It failed earlier: "
        "`pm-service` and `pm-proxy` were launched under the private namespace, but their runtime SELinux "
        "contexts remained `kernel` even though the helper requested `vendor_per_mgr`/`vendor_per_proxy`. "
        "Earlier provider-positive evidence already showed that the PM provider path needs the current-boot "
        "V490 policy-load precondition and an explicit `vndservicemanager` readiness/query gate.",
        "",
        "## Flags",
        "",
        markdown_table(["flag", "value"], flag_rows),
        "",
        "## Facts",
        "",
        markdown_table(["fact", "value"], fact_rows),
        "",
        "## Guardrails",
        "",
        "- Host-only classifier; no device command executed.",
        "- No daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, manual eSoC open, PMIC/GPIO write, flash, boot image write, or partition write.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = classify(args)
    manifest = {
        "cycle": "v1340",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "policy_load_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "manual_esoc_open_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
