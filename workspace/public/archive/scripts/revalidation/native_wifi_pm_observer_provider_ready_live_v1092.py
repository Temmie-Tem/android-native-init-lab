#!/usr/bin/env python3
"""V1092 PM observer vndservicemanager readiness and compact provider query live gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_service_trigger_observer_live_v1066 as base
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1092-pm-observer-provider-ready-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1092-pm-observer-provider-ready-live.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1092-execns-helper-v202-build/a90_android_execns_probe")
DEFAULT_HELPER_SHA256 = "54a2488dda1d659ffef52a89be643abc5bfaf5254477c2771d41901897211435"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v202"
original_helper_surface = base.helper_surface


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_base_defaults() -> None:
    base.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    base.DEFAULT_LOCAL_HELPER = DEFAULT_LOCAL_HELPER
    base.DEFAULT_HELPER_SHA256 = DEFAULT_HELPER_SHA256
    base.DEFAULT_HELPER_MARKER = DEFAULT_HELPER_MARKER
    base.LATEST_POINTER = LATEST_POINTER
    base.helper_surface = helper_surface
    base.decide = decide


def helper_surface(text: str) -> dict[str, Any]:
    surface = original_helper_surface(text)
    keys = base.parse_keys(text)
    query = {
        key: value
        for key, value in keys.items()
        if key.startswith("wifi_vndservice_query.")
    }
    query_results = {
        key: value
        for key, value in query.items()
        if key.endswith(".result")
    }
    provider_seen = any(
        key.endswith(".vendor_qcom_peripheral_manager_seen") and value == "1"
        for key, value in query.items()
    )
    query_executed = any(key.endswith(".exec_attempted") and value == "1" for key, value in query.items())
    surface["vndservice_query"] = query
    surface["vndservice_query_results"] = query_results
    surface["vndservice_provider_seen"] = provider_seen
    surface["vndservice_query_executed"] = query_executed
    return surface


def required_query_phases(query: dict[str, str]) -> dict[str, bool]:
    return {
        "after_per_mgr": any(
            key.startswith("wifi_vndservice_query.pm_observer_after_per_mgr_probe.") and
            key.endswith(".exec_attempted") and
            value == "1"
            for key, value in query.items()
        ),
        "after_per_proxy": any(
            key.startswith("wifi_vndservice_query.pm_observer_after_per_proxy_probe.") and
            key.endswith(".exec_attempted") and
            value == "1"
            for key, value in query.items()
        ),
    }


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[dict[str, Any]],
           analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        if not (local["exists"] and local["sha256"] == args.helper_sha256 and local["marker"] and local["mode"]):
            return "v1092-plan-helper-v202-missing", False, f"local={local}", "build/deploy helper v202 before V1092"
        return "v1092-pm-observer-provider-ready-plan-ready", True, "plan-only; no device command executed", "run bounded V1092 observer live gate"
    missing = base.required_flags(args)
    if missing:
        return "v1092-pm-observer-provider-ready-approval-required", False, f"missing flags: {', '.join(missing)}", "rerun with explicit V1092 flags"
    helper = analysis.get("helper") or {}
    failed_steps = base.step_failures(steps, helper)
    if failed_steps:
        return "v1092-step-failed", False, f"failed_steps={failed_steps}", "inspect V1092 evidence before retry"
    remote = analysis.get("remote_helper") or {}
    if not (remote.get("sha_ok") and remote.get("marker_ok") and remote.get("mode_ok")):
        return "v1092-helper-v202-remote-mismatch", False, f"remote={remote}", "redeploy helper v202 before V1092"
    if helper.get("forbidden_true"):
        return "v1092-forbidden-action-detected", False, f"forbidden={helper.get('forbidden_true')}", "stop and audit helper before retry"
    contract = helper.get("contract") or {}
    if contract.get("begin") != "1" or contract.get("allowed") != "1":
        return "v1092-helper-mode-not-executed", False, f"contract={contract}", "fix V1092 helper command before retry"
    if contract.get("vndservicemanager_readiness.ready") != "1":
        return (
            "v1092-vndservicemanager-readiness-gap",
            True,
            f"checked={contract.get('vndservicemanager_readiness.checked')} ready={contract.get('vndservicemanager_readiness.ready')}",
            "repair service-manager readiness before retrying PM provider registration",
        )
    query = helper.get("vndservice_query") or {}
    phases = required_query_phases(query)
    if not phases["after_per_mgr"]:
        return (
            "v1092-vndservice-query-not-executed",
            False,
            f"phases={phases}",
            "inspect helper output and PM observer launch order",
        )
    if helper.get("vndservice_provider_seen"):
        return (
            "v1092-pm-provider-registration-observed",
            True,
            f"phases={phases}",
            "classify post-provider mdm3/WLAN-PD trigger before Wi-Fi HAL or scan/connect",
        )
    return (
        "v1092-pm-provider-registration-not-observed",
        True,
        f"phases={phases} result={contract.get('result')}",
        "compare addService failure with SELinux policy-load and vndservicemanager readiness evidence",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    contract = helper.get("contract") or {}
    query = helper.get("vndservice_query") or {}
    query_rows = [
        [key, value]
        for key, value in sorted(query.items())
        if key.endswith((".result", ".vendor_qcom_peripheral_manager_seen", ".peripheral_seen", ".exec_attempted", ".exit_code", ".signal", ".timed_out"))
    ]
    step_rows = [[step["name"], step["ok"], step["rc"], step["duration_sec"], step["file"]] for step in manifest.get("steps", [])]
    return "\n".join([
        "# V1092 PM Observer Provider Ready Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: `{manifest['next_step']}`",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- helper_sha256: `{manifest['helper_sha256']}`",
        f"- vndservicemanager_ready: `{contract.get('vndservicemanager_readiness.ready', '')}`",
        f"- provider_seen: `{helper.get('vndservice_provider_seen', False)}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Vndservice Query",
        "",
        markdown_table(["key", "value"], query_rows),
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local = base.local_helper_info(args)
    steps: list[dict[str, Any]] = []
    analysis: dict[str, Any] = {}
    if args.command == "run" and not base.required_flags(args):
        steps, analysis = base.execute(args, store)
    decision, pass_ok, reason, next_step = decide(args, local, steps, analysis)
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    return {
        "cycle": "v1092",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "local_helper": local,
        "helper": args.helper,
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "mode": base.DEFAULT_MODE,
        "property_root": args.property_root,
        "helper_timeout_sec": args.helper_timeout_sec,
        "toybox_timeout_sec": args.toybox_timeout_sec,
        "steps": steps,
        "analysis": analysis,
        "service_manager_start_executed": contract.get("service_manager_start_executed") == "1",
        "pm_proxy_helper_start_executed": contract.get("pm_proxy_helper_start_executed") == "1",
        "pm_service_start_executed": contract.get("per_mgr_start_executed") == "1",
        "pm_proxy_start_executed": contract.get("per_proxy_start_executed") == "1",
        "pm_service_subsys_modem_seen": contract.get("per_mgr_subsys_modem_seen") == "1",
        "pm_proxy_helper_subsys_modem_seen": contract.get("pm_proxy_helper_subsys_modem_seen") == "1",
        "vndservicemanager_ready": contract.get("vndservicemanager_readiness.ready") == "1",
        "vndservice_provider_seen": helper.get("vndservice_provider_seen") is True,
        "mdm_helper_start_executed": contract.get("mdm_helper_start_executed") == "1",
        "cnss_daemon_start_executed": contract.get("cnss_daemon_start_executed") == "1",
        "subsys_esoc0_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "cleanup_reboot_executed": bool(cleanup.get("requested")),
        "wifi_hal_start_executed": contract.get("wifi_hal_start_executed") == "1",
        "scan_connect_executed": contract.get("scan_connect_linkup") == "1",
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": contract.get("external_ping") == "1",
        "wifi_bringup_executed": False,
    }


def main() -> int:
    patch_base_defaults()
    args = base.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"vndservicemanager_ready: {manifest['vndservicemanager_ready']}")
    print(f"vndservice_provider_seen: {manifest['vndservice_provider_seen']}")
    print(f"pm_service_subsys_modem_seen: {manifest['pm_service_subsys_modem_seen']}")
    print(f"pm_proxy_helper_subsys_modem_seen: {manifest['pm_proxy_helper_subsys_modem_seen']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
