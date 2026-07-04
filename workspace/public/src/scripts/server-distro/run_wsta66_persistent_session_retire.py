#!/usr/bin/env python3
"""WSTA66 host-only persistent session retire marker.

WSTA66 marks a WSTA65 session as intentionally retired without deleting private
artifacts and without touching the device.  The marker is consumed by WSTA65:
when supplied, status is forced to RETIRED and ready_for_live=false even if the
underlying WSTA64 artifact was previously READY.

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
PASS_DECISION = wsta65.RETIRE_PASS_DECISION
RETIRE_MARKER_SCHEMA = wsta65.RETIRE_MARKER_SCHEMA
ALLOWED_REASONS = {
    "operator-retired",
    "session-stale",
    "session-expired",
    "superseded-by-fresh-session",
}


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
        "scope": "WSTA66 host-only persistent session retire marker",
        "default_mode": "fail-closed-host-only",
        "input": "workspace/private/runs/server-distro/<wsta65-run>/wsta65_result.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--retire-session",
            "--ack-retire-session",
            "--wsta65-result-json",
            "workspace/private/runs/server-distro/<wsta65-run>/wsta65_result.json",
            "--reason",
            "operator-retired",
        ],
        "live_execution": "not-run-by-wsta66",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "retire": result.get("retire", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta65.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta66-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta66-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta66-blocked-{label}-missing"
    return path, None


def validate_wsta65_result(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta66-blocked-wsta65-result-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta65.PASS_DECISION:
        return False, "wsta66-blocked-wsta65-not-pass", {"decision": payload.get("decision")}
    status = payload.get("session_status") or {}
    wsta64_result = status.get("wsta64_result")
    if not isinstance(wsta64_result, str) or not wsta64_result:
        return False, "wsta66-blocked-wsta64-result-missing", {}
    if status.get("public_url_value_logged") is not False:
        return False, "wsta66-blocked-public-url-logged", {}
    if status.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta66-blocked-secret-values-logged", {}
    return True, "ok", {
        "payload": payload,
        "session_status": status,
        "wsta64_result": wsta64_result,
    }


def marker_payload(wsta65_path: Path,
                   wsta65_result: dict[str, Any],
                   reason: str,
                   retired_utc: str) -> dict[str, Any]:
    status = wsta65_result.get("session_status") or {}
    return {
        "schema": RETIRE_MARKER_SCHEMA,
        "decision": PASS_DECISION,
        "retired": True,
        "session_state": "RETIRED",
        "reason": reason,
        "retired_utc": retired_utc,
        "wsta65_result": rel(wsta65_path),
        "wsta64_result": status.get("wsta64_result"),
        "source_wsta64_decision": status.get("source_wsta64_decision"),
        "previous_session_state": status.get("session_state"),
        "previous_ready_for_live": bool(status.get("ready_for_live")),
        "state": "PUBLIC_OFF",
        "ready_for_live": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta66-persistent-session-retire-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA66 host-only persistent session retire marker",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta66-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta66-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta66_result.json"
    marker_path = run_dir / "wsta66_retire_marker.json"

    if not args.retire_session:
        result["decision"] = "wsta66-blocked-retire-session-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if not args.ack_retire_session:
        result["decision"] = "wsta66-blocked-retire-ack-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if args.reason not in ALLOWED_REASONS:
        result["decision"] = "wsta66-blocked-retire-reason-invalid"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"reason": args.reason, "allowed": sorted(ALLOWED_REASONS)}
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if args.wsta65_result_json is None:
        result["decision"] = "wsta66-blocked-wsta65-result-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta65_path, path_error = require_private_path(args.wsta65_result_json, "wsta65-result")
    if path_error or wsta65_path is None:
        result["decision"] = path_error or "wsta66-blocked-wsta65-result"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    valid, decision, detail = validate_wsta65_result(wsta65_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    marker = marker_payload(wsta65_path, detail["payload"], args.reason, ts)
    findings = redaction_findings(marker)
    if findings:
        result["decision"] = "wsta66-blocked-retire-marker-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    write_json(marker_path, marker)
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "retire": {
            "retire_marker": rel(marker_path),
            "wsta65_result": rel(wsta65_path),
            "wsta64_result": detail["wsta64_result"],
            "session_state": "RETIRED",
            "reason": args.reason,
            "ready_for_live": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
        "checks": {
            "wsta65_result_private": True,
            "retire_marker_written": True,
            "default_public_off": True,
            "ready_for_live": False,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta66-blocked-public-summary-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta65-result-json", type=Path)
    parser.add_argument("--reason", default="operator-retired")
    parser.add_argument("--retire-session", action="store_true")
    parser.add_argument("--ack-retire-session", action="store_true")
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
        payload = {"decision": "wsta66-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
