#!/usr/bin/env python3
"""V1108 PM ordering live gate without pre-CNSS per_proxy connect.

This reuses the V1106 tracefs collector but runs helper v207 with
`--pm-observer-start-cnss-before-per-proxy`, so the PM provider is observed
after `per_mgr` and `cnss-daemon` starts before any `pm-proxy` connect path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_cnss_voter_surface_live_v1095 as v1095
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1108-pm-ordering-no-pre-cnss-per-proxy-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "57cccbae22dd325e09b40641f91fef6b3c1abbfe631186539cc68e30ea2e6a0c"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v207"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1108"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1108/pm-ordering-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1108/pm-ordering-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1108/pm-ordering-output.txt"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def patch_defaults() -> None:
    v1095.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v1108-execns-helper-v207-build/a90_android_execns_probe")
    v1095.DEFAULT_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1095.DEFAULT_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1095.patch_defaults()

    v1106.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1106.LATEST_POINTER = LATEST_POINTER
    v1106.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1106.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1106.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1106.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1106.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1106.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1106.remote_marker_check = remote_marker_check
    v1106.pm_cnss_child_command = pm_cnss_child_command


def pm_cnss_child_command(args: argparse.Namespace) -> list[str]:
    command = v1095.helper_command(args)
    if len(command) >= 3 and command[0] == args.toybox and command[1] == "timeout":
        command = command[3:]
    command.append("--pm-observer-start-cnss-before-per-proxy")
    return command


def remote_marker_check(args: argparse.Namespace,
                        store: EvidenceStore,
                        steps: list[dict[str, Any]]) -> dict[str, Any]:
    step = v1106.base.run_tcpctl(args, store, steps, "execns-helper-usage", [args.helper], timeout=30.0)
    text = v1106.step_payload(store, step)
    return {
        "file": step["file"],
        "marker_ok": args.helper_marker in text,
        "mode_ok": v1106.base.DEFAULT_MODE in text,
        "start_cnss_flag_ok": "--pm-observer-start-cnss-after-provider" in text,
        "start_cnss_before_per_proxy_flag_ok": "--pm-observer-start-cnss-before-per-proxy" in text,
    }


def cnss_return_values(tracefs: dict[str, Any], label: str) -> list[str]:
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" in comm:
            values.extend((labels or {}).get(label, []))
    return values


def decide_v1108(args: argparse.Namespace, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1108-pm-ordering-no-pre-cnss-per-proxy-plan-ready",
            True,
            "plan-only; no tracefs write, PM actor, CNSS actor, or Wi-Fi action executed",
            "deploy helper v207, then run V1108 with explicit allow flags",
        )

    base_decision = str(manifest.get("decision", ""))
    analysis = manifest.get("analysis") or {}
    tracefs = analysis.get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    usage = analysis.get("execns_usage") or {}

    if not analysis.get("execns_helper", {}).get("ok"):
        return ("v1108-execns-helper-sha-mismatch", False, "remote execns helper is not v207", "deploy helper v207")
    if not (
        usage.get("marker_ok")
        and usage.get("mode_ok")
        and usage.get("start_cnss_flag_ok")
        and usage.get("start_cnss_before_per_proxy_flag_ok")
    ):
        return ("v1108-execns-helper-usage-mismatch", False, f"usage={usage}", "redeploy or rebuild helper v207")
    if tracefs.get("result") != "tracefs-uprobe-pass":
        return ("v1108-tracefs-uprobe-failed", False, f"tracefs result={tracefs.get('result')}", "inspect tracefs collector transcript")
    if tracefs.get("forbidden_true"):
        return ("v1108-forbidden-action-observed", False, f"forbidden={tracefs.get('forbidden_true')}", "stop and audit helper contract")
    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1108-pre-cnss-per-proxy-not-skipped",
            False,
            f"per_proxy_start_executed={contract.get('per_proxy_start_executed')} skipped={contract.get('child.per_proxy.start_skipped')}",
            "repair helper v207 ordering contract before interpreting live output",
        )
    if contract.get("start_cnss_before_per_proxy") != "1" or contract.get("cnss_daemon_start_executed") != "1":
        return (
            "v1108-cnss-before-per-proxy-contract-missing",
            False,
            f"start_cnss_before_per_proxy={contract.get('start_cnss_before_per_proxy')} cnss={contract.get('cnss_daemon_start_executed')}",
            "repair child command flags before retry",
        )

    by_label = tracefs.get("by_label_comm") or {}
    cnss_register_entries = sum(
        int(count)
        for comm, count in (by_label.get("pm_client_register_entry") or {}).items()
        if "cnss" in comm
    )
    cnss_connect_entries = sum(
        int(count)
        for comm, count in (by_label.get("pm_client_connect_entry") or {}).items()
        if "cnss" in comm
    )
    cnss_register_returns = cnss_return_values(tracefs, "pm_client_register_ret")
    cnss_connect_returns = cnss_return_values(tracefs, "pm_client_connect_ret")
    cnss_pending = {
        comm: events
        for comm, events in (tracefs.get("pending_raw_locks_by_comm") or {}).items()
        if "cnss" in comm
    }
    mdm3_state = contract.get("post_provider_surface.after_cnss_daemon.mdm3_state") or ""

    if cnss_connect_entries > 0 or cnss_connect_returns:
        return (
            "v1108-no-pre-cnss-per-proxy-cnss-connect-path-reached",
            True,
            f"register_ret={cnss_register_returns} connect_entries={cnss_connect_entries} connect_ret={cnss_connect_returns} mdm3_state={mdm3_state}",
            "classify PM connect result and lower modem/eSoC side effects before Wi-Fi HAL",
        )
    if cnss_register_returns:
        return (
            "v1108-no-pre-cnss-per-proxy-cnss-register-returned",
            True,
            f"register_entries={cnss_register_entries} register_ret={cnss_register_returns} mdm3_state={mdm3_state}",
            "trace cnss-daemon path between PM register return and PM connect",
        )
    if cnss_pending:
        return (
            "v1108-cnss-mutex-wait-persists-without-pre-cnss-per-proxy",
            True,
            f"cnss_pending_raw_locks={cnss_pending} mdm3_state={mdm3_state} base_decision={base_decision}",
            "classify pm-service mutex owner without pre-CNSS per_proxy, likely pm_proxy_helper/per_mgr lower subsystem path",
        )
    if cnss_register_entries > 0:
        return (
            "v1108-cnss-register-entry-no-return-without-pre-cnss-per-proxy",
            True,
            f"register_entries={cnss_register_entries} base_decision={base_decision} mdm3_state={mdm3_state}",
            "inspect V1108 trace checkpoints to find new no-return boundary",
        )
    return (
        "v1108-cnss-register-entry-missing-without-pre-cnss-per-proxy",
        True,
        f"base_decision={base_decision} by_comm={tracefs.get('by_comm', {})}",
        "inspect child order and provider visibility before retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    step_rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1108 PM Ordering No Pre-CNSS per_proxy Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- base_v1106_decision: `{manifest.get('base_v1106_decision', '')}`",
        f"- helper_marker: `{DEFAULT_EXECNS_HELPER_MARKER}`",
        f"- per_proxy_start_executed: `{contract.get('per_proxy_start_executed', '')}`",
        f"- per_proxy_start_skipped: `{contract.get('child.per_proxy.start_skipped', '')}`",
        f"- start_cnss_before_per_proxy: `{contract.get('start_cnss_before_per_proxy', '')}`",
        f"- cnss_daemon_start_executed: `{contract.get('cnss_daemon_start_executed', '')}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Tracefs",
        "",
        "```json",
        json.dumps({
            "result": tracefs.get("result"),
            "hit_count": tracefs.get("hit_count"),
            "by_comm": tracefs.get("by_comm") or {},
            "return_values_by_comm": tracefs.get("return_values_by_comm") or {},
            "pending_raw_locks_by_comm": tracefs.get("pending_raw_locks_by_comm") or {},
            "completed_raw_locks_by_comm": tracefs.get("completed_raw_locks_by_comm") or {},
            "pending_raw_lock_thread_samples": tracefs.get("pending_raw_lock_thread_samples") or {},
            "thread_sample_count": tracefs.get("thread_sample_count") or 0,
        }, indent=2, sort_keys=True),
        "```",
        "",
        "## Steps",
        "",
        markdown_table(["name", "ok", "rc", "duration_sec", "file"], step_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1106.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1108"
    manifest["generated_at"] = now_iso()
    decision, passed, reason, next_step = decide_v1108(args, manifest)
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
