#!/usr/bin/env python3
"""V1120 live gate for internal pm_register_connect branch classification."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
import native_wifi_zero_delay_cnss_global_live_v1118 as v1118
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1120-pm-register-connect-branch-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1120-pm-register-connect-branch-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1120"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1120/pm-register-connect-branch-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1120/pm-register-connect-branch-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1120/pm-register-connect-branch-output.txt"
PROOF_PREFIX = "/tmp/a90-v1120-"

INTERNAL_EVENT_SPECS = (
    ("pm_register_connect_entry", "client", "612c", "client_ptr=%x0 event_ptr=%x1"),
    ("pm_register_connect_service_null_check", "client", "620c", "binder=%x8"),
    ("pm_register_connect_interface_null_check", "client", "6254", "iface=%x0"),
    (
        "pm_register_connect_remote_register_call",
        "client",
        "6274",
        "iface=%x0 peripheral=+0(%x1):string client=+0(%x2):string out_client=%x4 out_state=%x5",
    ),
    ("pm_register_connect_remote_register_return_check", "client", "6278", "remote_ret=%x0"),
    ("pm_register_connect_ret", "client", "612c", "ret=$retval"),
)

VALUE_RE = re.compile(r"\b(?P<key>binder|iface|remote_ret|ret)=(?P<value>0x[0-9A-Fa-f]+|-?[0-9]+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_defaults() -> None:
    v1118.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1118.LATEST_POINTER = LATEST_POINTER
    v1118.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1118.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1118.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1118.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1118.PROOF_PREFIX = PROOF_PREFIX
    v1118.patch_defaults()
    v1106.EVENT_SPECS = tuple(v1106.EVENT_SPECS) + INTERNAL_EVENT_SPECS
    v1106.RETURN_EVENT_LABELS = {
        label
        for label, _binary_key, _offset, _fetch in v1106.EVENT_SPECS
        if label.endswith("_ret")
    }


def cnss_label_count(tracefs: dict[str, Any], label: str) -> int:
    total = 0
    by_label = tracefs.get("by_label_comm") or {}
    for comm, count in (by_label.get(label) or {}).items():
        if "cnss" not in str(comm):
            continue
        try:
            total += int(count)
        except (TypeError, ValueError):
            continue
    return total


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    return v1118.cnss_return_values(tracefs, label)


def trace_values(tracefs: dict[str, Any], label: str, key: str) -> list[str]:
    values: list[str] = []
    marker = f"{label}:"
    for line in tracefs.get("trace_lines") or []:
        if marker not in str(line) or "cnss" not in str(line):
            continue
        for match in VALUE_RE.finditer(str(line)):
            if match.group("key") == key:
                values.append(match.group("value"))
    return values


def contract_value(tracefs: dict[str, Any], key: str) -> str:
    return str((tracefs.get("pm_contract") or {}).get(key, ""))


def classify_branch(tracefs: dict[str, Any]) -> dict[str, Any]:
    counts = {
        "pm_client_register_entry": cnss_label_count(tracefs, "pm_client_register_entry"),
        "pm_client_register_ret": cnss_label_count(tracefs, "pm_client_register_ret"),
        "pm_client_connect_entry": cnss_label_count(tracefs, "pm_client_connect_entry"),
        "pm_server_register_entry": cnss_label_count(tracefs, "pm_server_register_entry"),
        "pm_register_connect_entry": cnss_label_count(tracefs, "pm_register_connect_entry"),
        "pm_register_connect_service_null_check": cnss_label_count(tracefs, "pm_register_connect_service_null_check"),
        "pm_register_connect_interface_null_check": cnss_label_count(tracefs, "pm_register_connect_interface_null_check"),
        "pm_register_connect_remote_register_call": cnss_label_count(tracefs, "pm_register_connect_remote_register_call"),
        "pm_register_connect_remote_register_return_check": cnss_label_count(
            tracefs, "pm_register_connect_remote_register_return_check"
        ),
        "pm_register_connect_ret": cnss_label_count(tracefs, "pm_register_connect_ret"),
    }
    values = {
        "pm_client_register_ret": cnss_return_values(tracefs, "pm_client_register_ret"),
        "pm_register_connect_ret": cnss_return_values(tracefs, "pm_register_connect_ret"),
        "service_binder_values": trace_values(tracefs, "pm_register_connect_service_null_check", "binder"),
        "interface_values": trace_values(tracefs, "pm_register_connect_interface_null_check", "iface"),
        "remote_register_return_values": trace_values(
            tracefs, "pm_register_connect_remote_register_return_check", "remote_ret"
        ),
    }
    service_null = (
        counts["pm_register_connect_service_null_check"] > 0
        and counts["pm_register_connect_interface_null_check"] == 0
        and counts["pm_register_connect_remote_register_call"] == 0
    )
    interface_null = (
        counts["pm_register_connect_interface_null_check"] > 0
        and counts["pm_register_connect_remote_register_call"] == 0
    )
    remote_attempted = counts["pm_register_connect_remote_register_call"] > 0
    return {
        "counts": counts,
        "values": values,
        "flags": {
            "service_lookup_null_branch": service_null,
            "interface_null_branch": interface_null,
            "remote_register_attempted": remote_attempted,
            "remote_register_return_seen": counts["pm_register_connect_remote_register_return_check"] > 0,
            "pm_register_connect_ret_negative": "0xffffffff" in set(values["pm_register_connect_ret"]),
            "pm_client_register_ret_negative": "0xffffffff" in set(values["pm_client_register_ret"]),
        },
    }


def decide_v1120(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1120-pm-register-connect-branch-plan-ready",
            True,
            "plan-only; no device command, tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "run V1120 with explicit tracefs/vendor/PM/CNSS allow flags",
        )

    analysis = manifest.get("analysis") or {}
    global_fw = analysis.get("global_firmware") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    branch = classify_branch(tracefs)
    analysis["pm_register_connect_branch"] = branch
    blockers = analysis.get("global_preflight_blockers") or []
    cleanup = global_fw.get("reboot_cleanup") or {}

    if blockers:
        return ("v1120-global-preflight-blocked", False, f"blockers={blockers}", "clear global firmware preflight blockers")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1120-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1120-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if not (cleanup.get("version_seen") and cleanup.get("status_healthy")):
        return ("v1120-reboot-cleanup-unhealthy", False, f"cleanup={cleanup}", "verify native health before continuing")
    if not (
        bool(global_fw.get("holder_opened"))
        and all((global_fw.get("mounted_hits") or {}).values())
        and (global_fw.get("qrtr_rx_wait") or {}).get("seen")
    ):
        return (
            "v1120-global-holder-precondition-missing",
            False,
            f"global_fw={global_fw}",
            "repair global firmware holder prerequisite before PM branch tracing",
        )
    if contract_value(tracefs, "start_cnss_zero_delay_after_per_mgr") != "1":
        return (
            "v1120-zero-delay-contract-missing",
            False,
            f"start_cnss_zero_delay_after_per_mgr={contract_value(tracefs, 'start_cnss_zero_delay_after_per_mgr')}",
            "repair V1118 zero-delay command contract",
        )
    if branch["counts"]["pm_register_connect_entry"] == 0:
        return (
            "v1120-pm-register-connect-entry-missing",
            True,
            f"branch_counts={branch['counts']}",
            "inspect pm_client_register-to-pm_register_connect offset assumptions",
        )
    if branch["flags"]["service_lookup_null_branch"]:
        return (
            "v1120-pm-register-connect-service-lookup-null",
            True,
            f"branch_counts={branch['counts']} values={branch['values']}",
            "repair provider lifetime so vendor.qcom.PeripheralManager is registered before CNSS PM register",
        )
    if branch["flags"]["interface_null_branch"]:
        return (
            "v1120-pm-register-connect-interface-null",
            True,
            f"branch_counts={branch['counts']} values={branch['values']}",
            "repair IPeripheralManager interface conversion or vndbinder service object compatibility",
        )
    if branch["flags"]["remote_register_attempted"]:
        return (
            "v1120-pm-register-connect-remote-register-failure",
            True,
            f"branch_counts={branch['counts']} values={branch['values']}",
            "classify PM server remote register return and provider-side lifetime",
        )
    return (
        "v1120-pm-register-connect-branch-inconclusive",
        True,
        f"branch_counts={branch['counts']} values={branch['values']}",
        "inspect V1120 trace lines before changing PM service order",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    branch = analysis.get("pm_register_connect_branch") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    branch_rows = [[key, value] for key, value in (branch.get("counts") or {}).items()]
    return "\n".join([
        "# V1120 PM Register Connect Branch Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- pm_actor_executed: `{manifest['pm_actor_executed']}`",
        f"- cnss_daemon_start_executed: `{manifest['cnss_daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Branch Counts",
        "",
        markdown_table(["event", "cnss_count"], branch_rows),
        "",
        "## Branch Values",
        "",
        "```json",
        json.dumps(branch.get("values") or {}, indent=2, sort_keys=True),
        "```",
        "",
        "## PM Contract",
        "",
        "```json",
        json.dumps({
            "tracefs_result": tracefs.get("result", ""),
            "start_cnss_zero_delay_after_per_mgr": contract_value(tracefs, "start_cnss_zero_delay_after_per_mgr"),
            "per_mgr_exited": contract_value(tracefs, "child.per_mgr.exited"),
            "per_mgr_exit_code": contract_value(tracefs, "child.per_mgr.exit_code"),
            "vndservice_provider_seen": contract_value(tracefs, "vndservice_provider_seen"),
            "per_proxy_start_executed": contract_value(tracefs, "per_proxy_start_executed"),
            "child.per_proxy.start_skipped": contract_value(tracefs, "child.per_proxy.start_skipped"),
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1106.parse_args()
    args.out_dir = DEFAULT_OUT_DIR if args.out_dir == v1106.DEFAULT_OUT_DIR else args.out_dir
    args.work_dir = DEFAULT_WORK_DIR if args.work_dir == v1106.DEFAULT_WORK_DIR else args.work_dir
    args.child_script = DEFAULT_CHILD_SCRIPT if args.child_script == v1106.DEFAULT_CHILD_SCRIPT else args.child_script
    args.collector_script = (
        DEFAULT_COLLECTOR_SCRIPT if args.collector_script == v1106.DEFAULT_COLLECTOR_SCRIPT else args.collector_script
    )
    args.child_output = DEFAULT_CHILD_OUTPUT if args.child_output == v1106.DEFAULT_CHILD_OUTPUT else args.child_output
    v1118.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1120"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1120(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    global_fw = (manifest.get("analysis") or {}).get("global_firmware") or {}
    contract = ((manifest.get("analysis") or {}).get("tracefs_uprobe") or {}).get("pm_contract") or {}
    manifest["firmware_mounts_executed"] = bool(global_fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(global_fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(global_fw.get("reboot_cleanup"))
    manifest["cnss_daemon_start_executed"] = contract.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = contract.get("wifi_hal_start_executed") == "1"
    manifest["scan_connect_executed"] = contract.get("scan_connect_linkup") == "1"
    manifest["external_ping_executed"] = contract.get("external_ping") == "1"
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
