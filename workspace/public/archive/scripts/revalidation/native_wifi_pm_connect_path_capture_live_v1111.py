#!/usr/bin/env python3
"""V1111 live retry for tagged AArch64 PM connect syscall path targets."""

from __future__ import annotations

import json
from pathlib import Path

import native_wifi_pm_connect_path_capture_live_v1110 as v1110
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1111-pm-connect-path-capture-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1111-pm-connect-path-capture-live.txt")
DEFAULT_EXECNS_HELPER_SHA256 = "467ea2ef54a7b1ad95d95876ce8a8b5fe90bb4d8c9bfce6360211d6848c874a5"
DEFAULT_EXECNS_HELPER_MARKER = "a90_android_execns_probe v209"
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1111"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1111/pm-connect-path-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1111/pm-connect-path-tracefs-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1111/pm-connect-path-output.txt"


def patch_defaults() -> None:
    v1110.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1110.LATEST_POINTER = LATEST_POINTER
    v1110.DEFAULT_EXECNS_HELPER_SHA256 = DEFAULT_EXECNS_HELPER_SHA256
    v1110.DEFAULT_EXECNS_HELPER_MARKER = DEFAULT_EXECNS_HELPER_MARKER
    v1110.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1110.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1110.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1110.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1110.patch_defaults()


def decide_v1111(args, manifest):
    decision, passed, reason, next_step = v1110.decide_v1110(args, manifest)
    next_step = next_step.replace("V1110", "V1111").replace("v208", "v209")
    return decision.replace("v1110", "v1111", 1), passed, reason, next_step


def render_summary(manifest):
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    rows = [
        [step.get("name"), step.get("ok"), step.get("rc"), step.get("duration_sec"), step.get("file")]
        for step in manifest.get("steps", [])
    ]
    return "\n".join([
        "# V1111 PM Connect Tagged Path Capture Live",
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
            "path_candidates": v1110.path_candidates(contract),
            "path_errors": v1110.path_errors(contract),
            "entries": v1110.syscall_probe_entries(contract)[:32],
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
    args = v1110.v1106.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1110.v1106.build_manifest(args, store)
    manifest["base_v1106_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1111"
    manifest["generated_at"] = v1110.now_iso()
    decision, passed, reason, next_step = decide_v1111(args, manifest)
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
