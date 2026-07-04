#!/usr/bin/env python3
"""WSTA76 host-only persistent launch brief.

WSTA75 inventories currently usable arming packets.  WSTA76 is the last
default-off operator brief before a separately selected WSTA58 live gate: it
consumes a private WSTA75 inventory, reruns WSTA75 against the original scan
root, selects a fresh READY packet, loads the fresh WSTA73 recheck packet, and
writes a compact launch brief with the WSTA58 command template and required
operator checks.

It never executes the WSTA58 live gate.  It performs no device action, native
reboot, Wi-Fi association, DHCP, public tunnel, public smoke, userdata action,
switch-root, or flash.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta75_persistent_arming_inventory as wsta75  # noqa: E402


REPO_ROOT = wsta75.REPO_ROOT
PRIVATE_ROOT = wsta75.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta75.DEFAULT_RUN_BASE
PASS_DECISION = "wsta76-persistent-launch-brief-pass"


def rel(path: Path) -> str:
    return wsta75.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return wsta75.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta75.is_under(path, root)


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA76 host-only persistent launch brief",
        "default_mode": "host-only-revalidate-and-brief",
        "input": "workspace/private/runs/server-distro/<wsta75-run>/wsta75_arming_inventory.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta75-arming-inventory-json",
            "workspace/private/runs/server-distro/<wsta75-run>/wsta75_arming_inventory.json",
            "--ready-index",
            "0",
        ],
        "live_execution": "not-run-by-wsta76",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "launch_brief": result.get("launch_brief", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta75.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta76-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta76-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta76-blocked-{label}-missing"
    return path, None


def validate_inventory(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta76-blocked-inventory-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta75.PASS_DECISION:
        return False, "wsta76-blocked-inventory-not-pass", {"decision": payload.get("decision")}
    inventory = payload.get("arming_inventory")
    if not isinstance(inventory, dict):
        return False, "wsta76-blocked-inventory-missing", {}
    if inventory.get("default_public_off") is not True:
        return False, "wsta76-blocked-default-public-off-missing", {}
    if inventory.get("live_execution_requested") is not False:
        return False, "wsta76-blocked-live-execution-requested", {}
    if inventory.get("public_url_value_logged") is not False:
        return False, "wsta76-blocked-public-url-logged", {}
    if inventory.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta76-blocked-secret-values-logged", {}
    scan_root, path_error = require_private_path(inventory.get("scan_root"), "scan-root")
    if path_error or scan_root is None:
        return False, path_error or "wsta76-blocked-scan-root", {}
    return True, "ok", {"payload": payload, "inventory": inventory, "scan_root": scan_root}


def wsta75_args(run_dir: Path,
                scan_root: Path,
                max_packets: int,
                min_remaining: int | None,
                now_utc: str | None) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--scan-root",
        str(scan_root),
        "--max-packets",
        str(max_packets),
    ]
    if min_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(min_remaining)])
    if now_utc:
        argv.extend(["--now-utc", now_utc])
    return wsta75.build_arg_parser().parse_args(argv)


def ready_entries(entries: list[Any]) -> list[dict[str, Any]]:
    ready: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("state") == "READY_TO_EXECUTE_DEFAULT_OFF" and entry.get("ready_for_live") is True:
            ready.append(entry)
    return sorted(ready, key=wsta75.ready_sort_key, reverse=True)


def load_status_and_packet(entry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], Path, Path]:
    status_path, path_error = require_private_path(entry.get("wsta74_status_result"), "wsta74-status")
    if path_error or status_path is None:
        raise ValueError(path_error or "wsta76-blocked-wsta74-status")
    status_result = load_json(status_path)
    if status_result.get("decision") != wsta75.wsta74.PASS_DECISION:
        raise ValueError("wsta76-blocked-wsta74-status-not-pass")
    arming_status = status_result.get("arming_status")
    if not isinstance(arming_status, dict):
        raise ValueError("wsta76-blocked-arming-status-missing")
    recheck_path, path_error = require_private_path(arming_status.get("wsta73_recheck_result"), "wsta73-recheck")
    if path_error or recheck_path is None:
        raise ValueError(path_error or "wsta76-blocked-wsta73-recheck")
    recheck_result = load_json(recheck_path)
    if recheck_result.get("decision") != wsta75.wsta74.wsta73.PASS_DECISION:
        raise ValueError("wsta76-blocked-wsta73-recheck-not-pass")
    packet = recheck_result.get("arming_packet")
    if not isinstance(packet, dict):
        raise ValueError("wsta76-blocked-arming-packet-missing")
    if packet.get("ready_for_live") is not True:
        raise ValueError("wsta76-blocked-arming-packet-not-ready")
    if packet.get("live_execution_requested") is not False:
        raise ValueError("wsta76-blocked-live-execution-requested")
    return arming_status, packet, status_path, recheck_path


def build_launch_brief(source_inventory: Path,
                       recheck_inventory_path: Path,
                       selected_index: int,
                       ready_count: int,
                       entry: dict[str, Any],
                       arming_status: dict[str, Any],
                       packet: dict[str, Any],
                       status_path: Path,
                       recheck_path: Path,
                       out_json: Path,
                       out_md: Path) -> dict[str, Any]:
    return {
        "state": "READY_TO_EXECUTE_DEFAULT_OFF",
        "source_wsta75_inventory": rel(source_inventory),
        "wsta75_recheck_inventory": rel(recheck_inventory_path),
        "selected_ready_index": selected_index,
        "ready_candidate_count": ready_count,
        "selected_wsta73_arming_packet": entry.get("wsta73_arming_packet"),
        "wsta74_status_result": rel(status_path),
        "fresh_wsta73_recheck_result": rel(recheck_path),
        "wsta73_recheck_decision": arming_status.get("wsta73_recheck_decision"),
        "wsta65_session_state": packet.get("wsta65_session_state"),
        "ready_for_live": True,
        "initial_seconds_remaining": packet.get("initial_seconds_remaining"),
        "min_initial_seconds_remaining": packet.get("min_initial_seconds_remaining"),
        "wsta58_live_command_template": packet.get("wsta58_live_command_template"),
        "operator_required_replacements": packet.get("operator_required_replacements") or [
            "<native-confirm-token>",
            "<public-confirm-token>",
        ],
        "operator_acknowledgements_required": packet.get("operator_acknowledgements_required") or [],
        "abort_conditions": packet.get("abort_conditions") or [],
        "cleanup_expectations": packet.get("cleanup_expectations") or [],
        "operator_preflight_checks": [
            "confirm-intentional-public-exposure",
            "replace-placeholders-out-of-band",
            "run-wsta76-again-if-time-elapsed",
            "monitor-wsta58-final-manual-stop-cleanup",
            "verify-public-off-after-run",
        ],
        "recommended_next_action": "operator-may-run-explicit-wsta58-live-gate-from-brief",
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(brief: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in brief.get("wsta58_live_command_template") or [])
    lines = [
        "# WSTA Persistent Launch Brief",
        "",
        f"- State: `{brief.get('state')}`",
        f"- Source WSTA75 inventory: `{brief.get('source_wsta75_inventory')}`",
        f"- Fresh WSTA75 recheck: `{brief.get('wsta75_recheck_inventory')}`",
        f"- READY candidates: `{brief.get('ready_candidate_count')}`",
        f"- Selected READY index: `{brief.get('selected_ready_index')}`",
        f"- Selected WSTA73 packet: `{brief.get('selected_wsta73_arming_packet')}`",
        f"- Initial seconds remaining: `{brief.get('initial_seconds_remaining')}`",
        f"- WSTA65 state: `{brief.get('wsta65_session_state')}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Operator Replacements",
        "",
    ]
    for item in brief.get("operator_required_replacements", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Required Acknowledgements", ""])
    for item in brief.get("operator_acknowledgements_required", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Abort Conditions", ""])
    for item in brief.get("abort_conditions", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "## Cleanup Expectations", ""])
    for item in brief.get("cleanup_expectations", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## WSTA58 Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "This brief does not run the live gate. Replace placeholders only when explicitly running WSTA58.",
        "",
    ])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta76-persistent-launch-brief-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA76 host-only persistent launch brief",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta76-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta76-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta76_launch_brief.json"
    out_md = run_dir / "wsta76_launch_brief.md"

    if args.wsta75_arming_inventory_json is None:
        result["decision"] = "wsta76-blocked-inventory-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    inventory_path, path_error = require_private_path(args.wsta75_arming_inventory_json, "inventory")
    if path_error or inventory_path is None:
        result["decision"] = path_error or "wsta76-blocked-inventory"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    valid, decision, detail = validate_inventory(inventory_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    recheck_dir = run_dir / "wsta75-recheck"
    recheck = wsta75.run(wsta75_args(
        recheck_dir,
        detail["scan_root"],
        int(args.max_packets),
        args.min_initial_seconds_remaining,
        args.now_utc,
    ))
    recheck_path = recheck_dir / "wsta75_arming_inventory.json"
    if recheck.get("decision") != wsta75.PASS_DECISION:
        result["decision"] = "wsta76-blocked-wsta75-recheck"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"wsta75_decision": recheck.get("decision"), "wsta75_recheck": rel(recheck_path)}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    fresh_inventory = recheck.get("arming_inventory")
    if not isinstance(fresh_inventory, dict):
        result["decision"] = "wsta76-blocked-wsta75-recheck-missing-inventory"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    candidates = ready_entries(fresh_inventory.get("entries") or [])
    result["candidate_summary"] = {
        "ready_candidate_count": len(candidates),
        "selected_ready_index": args.ready_index,
    }
    if not candidates:
        result["decision"] = "wsta76-blocked-no-ready-packet"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {
            "overall_state": fresh_inventory.get("overall_state"),
            "state_counts": fresh_inventory.get("state_counts"),
            "wsta75_recheck": rel(recheck_path),
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    if args.ready_index < 0 or args.ready_index >= len(candidates):
        result["decision"] = "wsta76-blocked-ready-index-out-of-range"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    selected = candidates[int(args.ready_index)]
    try:
        arming_status, packet, status_path, packet_recheck_path = load_status_and_packet(selected)
    except Exception as exc:  # noqa: BLE001
        result["decision"] = "wsta76-blocked-selected-packet-unusable"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"error": str(exc)}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    brief = build_launch_brief(
        inventory_path,
        recheck_path,
        int(args.ready_index),
        len(candidates),
        selected,
        arming_status,
        packet,
        status_path,
        packet_recheck_path,
        out_json,
        out_md,
    )
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "launch_brief": brief,
        "checks": {
            "inventory_private": True,
            "wsta75_rechecked": True,
            "selected_packet_ready": True,
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(brief)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta76-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings + md_findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta75-arming-inventory-json", type=Path)
    parser.add_argument("--ready-index", type=int, default=0)
    parser.add_argument("--max-packets", type=int, default=wsta75.DEFAULT_MAX_PACKETS)
    parser.add_argument("--min-initial-seconds-remaining", type=int)
    parser.add_argument("--now-utc")
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta76-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
