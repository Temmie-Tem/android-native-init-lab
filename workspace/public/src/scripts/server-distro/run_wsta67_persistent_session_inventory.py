#!/usr/bin/env python3
"""WSTA67 host-only persistent session inventory.

WSTA63-WSTA66 operate on one prepared session.  WSTA67 scans private WSTA run
artifacts and builds a redacted operator inventory of all discovered WSTA64
session roots, recalculating each session's current lifecycle state through the
WSTA65 status logic.  Retire markers produced by WSTA66 take precedence.

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

import run_wsta65_persistent_session_status as wsta65  # noqa: E402


REPO_ROOT = wsta65.REPO_ROOT
PRIVATE_ROOT = wsta65.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta65.DEFAULT_RUN_BASE
PASS_DECISION = "wsta67-persistent-session-inventory-pass"
DEFAULT_MAX_SESSIONS = 50


def rel(path: Path) -> str:
    return wsta65.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return wsta65.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta65.is_under(path, root)


def now_from_args(args: argparse.Namespace) -> _dt.datetime:
    return wsta65.now_from_args(args)


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
        "scope": "WSTA67 host-only persistent session inventory",
        "default_mode": "host-only-inventory",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--scan-root",
            "workspace/private/runs/server-distro",
            "--max-sessions",
            str(DEFAULT_MAX_SESSIONS),
        ],
        "live_execution": "not-run-by-wsta67",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "inventory": result.get("inventory", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta65.redaction_findings(payload)


def newest_first(paths: list[Path]) -> list[Path]:
    return sorted(paths, key=lambda path: (path.stat().st_mtime, str(path)), reverse=True)


def scan_paths(root: Path, name: str, limit: int) -> tuple[list[Path], bool]:
    matches = newest_first([path for path in root.rglob(name) if path.is_file()])
    truncated = len(matches) > limit
    return matches[:limit], truncated


def retire_marker_map(markers: list[Path]) -> dict[str, Path]:
    by_wsta64: dict[str, tuple[str, Path]] = {}
    for marker_path in markers:
        try:
            marker = load_json(marker_path)
        except Exception:  # noqa: BLE001
            continue
        wsta64_result = marker.get("wsta64_result")
        retired_utc = marker.get("retired_utc") or ""
        if not isinstance(wsta64_result, str) or not wsta64_result:
            continue
        previous = by_wsta64.get(wsta64_result)
        if previous is None or retired_utc >= previous[0]:
            by_wsta64[wsta64_result] = (str(retired_utc), marker_path)
    return {key: value[1] for key, value in by_wsta64.items()}


def status_for_wsta64(path: Path,
                      retire_markers: dict[str, Path],
                      now: _dt.datetime,
                      min_remaining: int) -> tuple[dict[str, Any], dict[str, Any]]:
    marker_path = retire_markers.get(rel(path))
    if marker_path is not None:
        retire_ok, _, detail = wsta65.validate_retire_marker(marker_path, path)
        if retire_ok:
            return wsta65.retired_status(detail["marker"], detail["path"])
    wsta64_result = load_json(path)
    status, checks = wsta65.status_from_readiness(wsta64_result, now, min_remaining)
    status["wsta64_result"] = rel(path)
    return status, checks


def inventory_entry(path: Path,
                    status: dict[str, Any],
                    checks: dict[str, Any]) -> dict[str, Any]:
    return {
        "wsta64_result": rel(path),
        "session_state": status.get("session_state"),
        "ready_for_live": bool(status.get("ready_for_live")),
        "reason": status.get("reason"),
        "recommended_next_action": status.get("recommended_next_action"),
        "initial_seconds_remaining": status.get("initial_seconds_remaining"),
        "retire_marker": status.get("retire_marker"),
        "state": "PUBLIC_OFF",
        "default_public_off": bool(checks.get("default_public_off")),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def count_states(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        state = str(entry.get("session_state") or "UNKNOWN")
        counts[state] = counts.get(state, 0) + 1
    return counts


def run(args: argparse.Namespace) -> dict[str, Any]:
    now = now_from_args(args)
    ts = utc_stamp(now)
    run_id = args.run_id or f"wsta67-persistent-session-inventory-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    scan_root = resolve_path(args.scan_root)
    result: dict[str, Any] = {
        "scope": "WSTA67 host-only persistent session inventory",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta67-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta67-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not is_under(scan_root, PRIVATE_ROOT):
        result["decision"] = "wsta67-blocked-nonprivate-scan-root"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    if not scan_root.exists():
        result["decision"] = "wsta67-blocked-scan-root-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta67_inventory.json"

    wsta64_paths, wsta64_truncated = scan_paths(scan_root, "wsta64_result.json", int(args.max_sessions))
    retire_paths, retire_truncated = scan_paths(scan_root, "wsta66_retire_marker.json", int(args.max_retire_markers))
    retire_by_wsta64 = retire_marker_map(retire_paths)
    entries: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    for path in wsta64_paths:
        try:
            status, checks = status_for_wsta64(path, retire_by_wsta64, now, int(args.min_initial_seconds_remaining))
            entries.append(inventory_entry(path, status, checks))
        except Exception as exc:  # noqa: BLE001
            invalid.append({"wsta64_result": rel(path), "error": str(exc)})

    counts = count_states(entries)
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "inventory": {
            "scan_root": rel(scan_root),
            "session_count": len(entries),
            "invalid_session_count": len(invalid),
            "state_counts": counts,
            "ready_count": counts.get("READY", 0),
            "retired_count": counts.get("RETIRED", 0),
            "stale_count": counts.get("STALE", 0),
            "expired_count": counts.get("EXPIRED", 0),
            "not_ready_count": counts.get("NOT_READY", 0),
            "wsta64_scan_truncated": wsta64_truncated,
            "retire_marker_scan_truncated": retire_truncated,
            "entries": entries,
            "invalid_entries": invalid,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "scan_root_private": True,
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta67-blocked-public-summary-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--scan-root", type=Path, default=DEFAULT_RUN_BASE)
    parser.add_argument("--max-sessions", type=int, default=DEFAULT_MAX_SESSIONS)
    parser.add_argument("--max-retire-markers", type=int, default=DEFAULT_MAX_SESSIONS)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=wsta65.DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
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
        payload = {"decision": "wsta67-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
