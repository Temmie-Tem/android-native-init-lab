#!/usr/bin/env python3
"""V1109 host-only classifier for the post-CNSS PM connect lower blocker."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_pm_server_mutex_owner_classifier_v1107 as v1107
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1109-pm-connect-subsystem-get-classifier")
DEFAULT_V1108_MANIFEST = Path("tmp/wifi/v1108-pm-ordering-no-pre-cnss-per-proxy-live/manifest.json")
DEFAULT_PM_SERVICE = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
LATEST_POINTER = Path("tmp/wifi/latest-v1109-pm-connect-subsystem-get-classifier.txt")
ALLOWED_V1108_DECISIONS = {
    "v1108-no-pre-cnss-per-proxy-cnss-connect-path-reached",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(repo_path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def cnss_returns(tracefs: dict[str, Any], label: str) -> list[str]:
    values: list[str] = []
    for comm, labels in (tracefs.get("return_values_by_comm") or {}).items():
        if "cnss" not in comm:
            continue
        values.extend((labels or {}).get(label, []))
    return values


def find_pending_pm_service_lock(tracefs: dict[str, Any]) -> dict[str, str]:
    pending = tracefs.get("pending_raw_locks_by_comm") or {}
    for comm in ("pm-service",):
        for event in pending.get(comm, []):
            if event.get("mutex") and event.get("pid"):
                line = str(event.get("line", ""))
                return {
                    "comm": comm,
                    "tid": str(event.get("pid", "")),
                    "mutex": str(event.get("mutex", "")),
                    "line": line,
                    "time": str(v1107.parse_time(line)),
                }
    for comm, events in sorted(pending.items()):
        for event in events:
            if event.get("mutex") and event.get("pid"):
                line = str(event.get("line", ""))
                return {
                    "comm": comm,
                    "tid": str(event.get("pid", "")),
                    "mutex": str(event.get("mutex", "")),
                    "line": line,
                    "time": str(v1107.parse_time(line)),
                }
    return {}


def build_analysis(args: argparse.Namespace, tracefs: dict[str, Any]) -> dict[str, Any]:
    target = find_pending_pm_service_lock(tracefs)
    mutex_owner = v1107.classify_owner(tracefs, target) if target else {}
    owner_tid = str((mutex_owner.get("owner") or {}).get("tid", ""))
    waiter_tid = str(target.get("tid", ""))
    return {
        "target_pending_lock": target,
        "mutex_owner": mutex_owner,
        "owner_thread_state": v1107.thread_state(tracefs, owner_tid) if owner_tid else {},
        "waiter_thread_state": v1107.thread_state(tracefs, waiter_tid) if waiter_tid else {},
        "cnss_pm_client_register_ret": cnss_returns(tracefs, "pm_client_register_ret"),
        "cnss_pm_client_connect_ret": cnss_returns(tracefs, "pm_client_connect_ret"),
        "disassembly": v1107.disassemble(
            args.pm_service,
            str((mutex_owner.get("owner") or {}).get("return_offset", "")),
            args.store,
        ) if hasattr(args, "store") else {},
    }


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest["command"] == "plan":
        return (
            "v1109-pm-connect-subsystem-get-classifier-plan-ready",
            True,
            "host-only plan; no device command, tracefs write, PM actor, or Wi-Fi action executed",
            "run V1109 host-only classifier against V1108 evidence",
        )
    v1108 = manifest.get("v1108") or {}
    if v1108.get("decision") not in ALLOWED_V1108_DECISIONS:
        return (
            "v1109-v1108-predecessor-missing",
            False,
            f"unexpected V1108 decision={v1108.get('decision')!r}",
            "rerun or inspect V1108 before lower PM/eSoC classification",
        )
    contract = manifest.get("v1108_contract") or {}
    analysis = manifest.get("analysis") or {}
    owner = (analysis.get("mutex_owner") or {}).get("owner") or {}
    owner_state = analysis.get("owner_thread_state") or {}
    waiter_state = analysis.get("waiter_thread_state") or {}
    register_ret = analysis.get("cnss_pm_client_register_ret") or []
    connect_ret = analysis.get("cnss_pm_client_connect_ret") or []
    owner_wchans = set(owner_state.get("wchans") or [])
    waiter_wchans = set(waiter_state.get("wchans") or [])
    mdm3_state = contract.get("post_provider_surface.after_cnss_daemon.mdm3_state") or ""

    if contract.get("per_proxy_start_executed") != "0" or contract.get("child.per_proxy.start_skipped") != "1":
        return (
            "v1109-v1108-ordering-contract-mismatch",
            False,
            f"per_proxy_start_executed={contract.get('per_proxy_start_executed')} skipped={contract.get('child.per_proxy.start_skipped')}",
            "rerun V1108 with the no-pre-CNSS-per_proxy contract",
        )
    if "0x0" not in register_ret or "0x0" not in connect_ret:
        return (
            "v1109-cnss-pm-connect-success-not-proven",
            False,
            f"register_ret={register_ret} connect_ret={connect_ret}",
            "rerun V1108 or inspect tracefs PM client return events",
        )
    if not owner:
        return (
            "v1109-post-connect-mutex-owner-not-found",
            False,
            "no unmatched mutex owner was reconstructed for the post-connect pm-service waiter",
            "extend raw mutex trace window around successful CNSS PM connect",
        )
    if {"__subsystem_get", "_request_firmware"} & owner_wchans and "futex_wait_queue_me" in waiter_wchans:
        return (
            "v1109-cnss-pm-connect-triggers-subsystem-get-blocker",
            True,
            (
                f"owner={owner} owner_wchans={sorted(owner_wchans)} "
                f"waiter_wchans={sorted(waiter_wchans)} mdm3_state={mdm3_state}"
            ),
            "capture the exact firmware/openat or subsystem_get target in a bounded V1110 live gate before Wi-Fi HAL",
        )
    return (
        "v1109-post-connect-lower-blocker-classified",
        True,
        f"owner={owner} owner_wchans={sorted(owner_wchans)} waiter_wchans={sorted(waiter_wchans)} mdm3_state={mdm3_state}",
        "interpret captured owner wait state before expanding toward Wi-Fi HAL",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1108_manifest = load_json(args.v1108_manifest)
    tracefs = (v1108_manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    setattr(args, "store", store)
    manifest: dict[str, Any] = {
        "cycle": "v1109",
        "generated_at": now_iso(),
        "command": args.command,
        "v1108": {
            "manifest": str(repo_path(args.v1108_manifest)),
            "decision": v1108_manifest.get("decision", ""),
            "pass": bool(v1108_manifest.get("pass")),
        },
        "v1108_contract": {
            key: contract.get(key, "")
            for key in (
                "order",
                "per_proxy_start_executed",
                "child.per_proxy.start_skipped",
                "start_cnss_before_per_proxy",
                "cnss_daemon_start_executed",
                "post_provider_surface.after_cnss_daemon.mdm3_state",
            )
        },
        "analysis": {},
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    if args.command == "run":
        manifest["analysis"] = build_analysis(args, tracefs)
    decision, passed, reason, next_step = decide(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V1109 PM Connect Subsystem Get Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_command_executed: `{manifest['device_command_executed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## V1108 Contract",
        "",
        "```json",
        json.dumps(manifest.get("v1108_contract") or {}, indent=2, sort_keys=True),
        "```",
        "",
        "## Analysis",
        "",
        "```json",
        json.dumps(manifest.get("analysis") or {}, indent=2, sort_keys=True),
        "```",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1108-manifest", type=Path, default=DEFAULT_V1108_MANIFEST)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_command_executed: {manifest['device_command_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
