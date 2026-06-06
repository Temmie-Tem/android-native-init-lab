#!/usr/bin/env python3
"""V1110 live capture for post-CNSS PM connect syscall path targets."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_ordering_no_pre_cnss_per_proxy_live_v1108 as v1108
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1110-pm-connect-path-capture-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1110-pm-connect-path-capture-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "a373aaa7954a87c9c5bb4c7a4c3f2f6b2ec046022a01c571e460b134b4596a98"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v208"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1110"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1110/pm-connect-path-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1110/pm-connect-path-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1110/pm-connect-path-output.txt"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_defaults() -> None:
    v1108.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1108.LATEST_POINTER = LATEST_POINTER
    v1108.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1108.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1108.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1108.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1108.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1108.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1108.patch_defaults()


def syscall_probe_entries(contract: dict[str, str]) -> list[dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    prefix = "syscall_probe."
    for key, value in contract.items():
        if not key.startswith(prefix):
            continue
        parts = key.split(".")
        if len(parts) < 4 or not parts[2].startswith("entry_"):
            continue
        entry_key = ".".join(parts[:3])
        field = ".".join(parts[3:])
        entries.setdefault(entry_key, {"entry_key": entry_key})[field] = value
    return sorted(entries.values(), key=lambda item: item.get("entry_key", ""))


def path_candidates(contract: dict[str, str]) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for entry in syscall_probe_entries(contract):
        if entry.get("path.valid") != "1":
            continue
        candidates.append({
            "entry_key": entry.get("entry_key", ""),
            "tid": entry.get("tid", ""),
            "comm": entry.get("comm", ""),
            "wchan": entry.get("wchan", ""),
            "nr": entry.get("nr", ""),
            "name": entry.get("name", ""),
            "path_addr": entry.get("path.addr", ""),
            "path_value": entry.get("path.value", ""),
        })
    return candidates


def path_errors(contract: dict[str, str]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for entry in syscall_probe_entries(contract):
        if "path.valid" not in entry or entry.get("path.valid") == "1":
            continue
        errors.append({
            "entry_key": entry.get("entry_key", ""),
            "tid": entry.get("tid", ""),
            "comm": entry.get("comm", ""),
            "wchan": entry.get("wchan", ""),
            "nr": entry.get("nr", ""),
            "name": entry.get("name", ""),
            "path_addr": entry.get("path.addr", ""),
            "error": entry.get("path.error", ""),
            "reason": entry.get("path.reason", ""),
        })
    return errors


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in comm:
            values.extend((labels or {}).get(label, []))
    return values


def decide_v1110(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1110-pm-connect-path-capture-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "deploy helper v208, then run bounded V1110 live capture",
        )
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}
    candidates = path_candidates(contract)
    errors = path_errors(contract)
    register_ret = cnss_return_values(tracefs, "pm_client_register_ret")
    connect_ret = cnss_return_values(tracefs, "pm_client_connect_ret")

    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1110-execns-helper-sha-mismatch", False, "remote execns helper is not v208", "deploy helper v208")
    if not (usage.get("marker_ok") and usage.get("mode_ok") and usage.get("start_cnss_before_per_proxy_flag_ok")):
        return ("v1110-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v208")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1110-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1110-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return ("v1110-pre-cnss-per-proxy-not-skipped", False, f"contract={contract}", "repair no-pre-CNSS-per_proxy contract")
    if "0x0" not in register_ret or "0x0" not in connect_ret:
        return (
            "v1110-cnss-pm-connect-success-not-reproduced",
            False,
            f"register_ret={register_ret} connect_ret={connect_ret}",
            "rerun V1110 after restoring V1108 PM ordering preconditions",
        )
    if candidates:
        return (
            "v1110-pm-connect-syscall-path-captured",
            True,
            f"path_candidates={candidates[:8]}",
            "map captured path to firmware/subsystem prerequisite before Wi-Fi HAL",
        )
    if errors:
        return (
            "v1110-pm-connect-syscall-path-read-error",
            True,
            f"path_errors={errors[:8]}",
            "use ptrace clone/thread attach or focused process_vm retry to read owner-thread path",
        )
    return (
        "v1110-pm-connect-syscall-path-not-observed",
        True,
        f"entries={syscall_probe_entries(contract)[:8]}",
        "increase post-connect sampling window or trigger path capture closer to owner block",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1110 PM Connect Path Capture Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- per_proxy_start_executed: `{contract.get('per_proxy_start_executed', '')}`",
        f"- per_proxy_start_skipped: `{contract.get('child.per_proxy.start_skipped', '')}`",
        f"- cnss_daemon_start_executed: `{contract.get('cnss_daemon_start_executed', '')}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Syscall Path Probe",
        "",
        "```json",
        json.dumps({
            "path_candidates": path_candidates(contract),
            "path_errors": path_errors(contract),
            "entries": syscall_probe_entries(contract)[:32],
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
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1110"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1110(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
