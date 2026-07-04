#!/usr/bin/env python3
"""WSTA68 host-only bulk retire for non-liveable persistent sessions.

WSTA67 inventories prepared sessions.  WSTA68 consumes that private inventory and
creates WSTA66-compatible retire markers only for selected non-liveable states
(STALE, EXPIRED, NOT_READY by default).  READY sessions are never retired by
default, and already RETIRED sessions are skipped.

This script performs no device action, native reboot, Wi-Fi association, DHCP,
public tunnel, public smoke, userdata action, switch-root, or flash.
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

import run_wsta66_persistent_session_retire as wsta66  # noqa: E402
import run_wsta67_persistent_session_inventory as wsta67  # noqa: E402


REPO_ROOT = wsta67.REPO_ROOT
PRIVATE_ROOT = wsta67.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta67.DEFAULT_RUN_BASE
PASS_DECISION = "wsta68-persistent-session-bulk-retire-pass"
DEFAULT_TARGET_STATES = ("STALE", "EXPIRED", "NOT_READY")


def rel(path: Path) -> str:
    return wsta67.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return wsta67.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta67.is_under(path, root)


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
        "scope": "WSTA68 host-only bulk retire for non-liveable sessions",
        "default_mode": "fail-closed-host-only",
        "input": "workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--bulk-retire",
            "--ack-bulk-retire",
            "--wsta67-inventory-json",
            "workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json",
        ],
        "target_states": list(DEFAULT_TARGET_STATES),
        "live_execution": "not-run-by-wsta68",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "bulk_retire": result.get("bulk_retire", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta67.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta68-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta68-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta68-blocked-{label}-missing"
    return path, None


def parse_target_states(values: list[str] | None) -> set[str]:
    raw = values or list(DEFAULT_TARGET_STATES)
    return {item.strip().upper() for item in raw if item.strip()}


def reason_for_state(state: str) -> str:
    if state == "EXPIRED":
        return "session-expired"
    if state == "STALE":
        return "session-stale"
    return "operator-retired"


def validate_inventory(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta68-blocked-inventory-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta67.PASS_DECISION:
        return False, "wsta68-blocked-inventory-not-pass", {"decision": payload.get("decision")}
    inventory = payload.get("inventory")
    if not isinstance(inventory, dict):
        return False, "wsta68-blocked-inventory-missing", {}
    entries = inventory.get("entries")
    if not isinstance(entries, list):
        return False, "wsta68-blocked-inventory-entries-missing", {}
    if inventory.get("public_url_value_logged") is not False:
        return False, "wsta68-blocked-public-url-logged", {}
    if inventory.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta68-blocked-secret-values-logged", {}
    return True, "ok", {"payload": payload, "inventory": inventory, "entries": entries}


def marker_for_entry(entry: dict[str, Any],
                     inventory_path: Path,
                     marker_path: Path,
                     reason: str,
                     retired_utc: str) -> dict[str, Any]:
    return {
        "schema": wsta66.RETIRE_MARKER_SCHEMA,
        "decision": wsta66.PASS_DECISION,
        "retired": True,
        "session_state": "RETIRED",
        "reason": reason,
        "retired_utc": retired_utc,
        "wsta65_result": "bulk-retire-from-inventory",
        "wsta64_result": entry.get("wsta64_result"),
        "source_wsta64_decision": "inventory-derived",
        "source_inventory": rel(inventory_path),
        "previous_session_state": entry.get("session_state"),
        "previous_ready_for_live": bool(entry.get("ready_for_live")),
        "state": "PUBLIC_OFF",
        "ready_for_live": False,
        "retire_marker": rel(marker_path),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta68-persistent-session-bulk-retire-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA68 host-only bulk retire for non-liveable sessions",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta68-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta68-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta68_result.json"

    if not args.bulk_retire:
        result["decision"] = "wsta68-blocked-bulk-retire-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if not args.ack_bulk_retire:
        result["decision"] = "wsta68-blocked-bulk-retire-ack-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if args.wsta67_inventory_json is None:
        result["decision"] = "wsta68-blocked-inventory-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    inventory_path, path_error = require_private_path(args.wsta67_inventory_json, "inventory")
    if path_error or inventory_path is None:
        result["decision"] = path_error or "wsta68-blocked-inventory"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    valid, decision, detail = validate_inventory(inventory_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    target_states = parse_target_states(args.target_state)
    written: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for index, entry in enumerate(detail["entries"]):
        state = str(entry.get("session_state") or "UNKNOWN").upper()
        if state not in target_states or state == "RETIRED" or bool(entry.get("ready_for_live")):
            skipped.append({
                "wsta64_result": entry.get("wsta64_result"),
                "session_state": state,
                "reason": "not-targeted-or-ready",
            })
            continue
        marker_path = run_dir / f"retire-{index:03d}" / "wsta66_retire_marker.json"
        marker = marker_for_entry(entry, inventory_path, marker_path, reason_for_state(state), ts)
        findings = redaction_findings(marker)
        if findings:
            skipped.append({
                "wsta64_result": entry.get("wsta64_result"),
                "session_state": state,
                "reason": "redaction-finding",
            })
            continue
        write_json(marker_path, marker)
        written.append({
            "wsta64_result": entry.get("wsta64_result"),
            "retire_marker": rel(marker_path),
            "previous_session_state": state,
            "reason": marker["reason"],
        })

    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "bulk_retire": {
            "source_inventory": rel(inventory_path),
            "target_states": sorted(target_states),
            "retired_count": len(written),
            "skipped_count": len(skipped),
            "retired": written,
            "skipped": skipped,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "inventory_private": True,
            "bulk_retire_ack": True,
            "default_public_off": True,
            "ready_sessions_retired": False,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta68-blocked-public-summary-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta67-inventory-json", type=Path)
    parser.add_argument("--target-state", action="append", choices=["STALE", "EXPIRED", "NOT_READY"])
    parser.add_argument("--bulk-retire", action="store_true")
    parser.add_argument("--ack-bulk-retire", action="store_true")
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
        payload = {"decision": "wsta68-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
