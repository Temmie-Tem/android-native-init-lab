#!/usr/bin/env python3
"""WSTA65 host-only persistent session lifecycle status.

WSTA64 answers whether a WSTA63 session is ready at audit time.  WSTA65 turns
that artifact into an operator-facing lifecycle status at the current time:
READY, STALE, EXPIRED, or NOT_READY.  It re-reads the initial private lease so a
previously green WSTA64 result cannot remain "ready" after the lease ages out.

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

import run_wsta64_persistent_session_readiness_audit as wsta64  # noqa: E402


REPO_ROOT = wsta64.REPO_ROOT
PRIVATE_ROOT = wsta64.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta64.DEFAULT_RUN_BASE
PASS_DECISION = "wsta65-persistent-session-status-pass"
DEFAULT_MIN_INITIAL_SECONDS_REMAINING = wsta64.DEFAULT_MIN_INITIAL_SECONDS_REMAINING


def rel(path: Path) -> str:
    return wsta64.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return wsta64.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta64.is_under(path, root)


def now_from_args(args: argparse.Namespace) -> _dt.datetime:
    return wsta64.now_from_args(args)


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
        "scope": "WSTA65 host-only persistent session lifecycle status",
        "default_mode": "host-only-status",
        "input": "workspace/private/runs/server-distro/<wsta64-run>/wsta64_result.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta64-result-json",
            "workspace/private/runs/server-distro/<wsta64-run>/wsta64_result.json",
            "--min-initial-seconds-remaining",
            str(DEFAULT_MIN_INITIAL_SECONDS_REMAINING),
        ],
        "live_execution": "not-run-by-wsta65",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "session_status": result.get("session_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta64.redaction_findings(payload)


def classify_from_wsta64_decision(decision: str) -> tuple[str, str, str]:
    if "lease-already-expired" in decision:
        return "EXPIRED", "initial-lease-expired", "rerun-wsta63-then-wsta64"
    if "near-expiry" in decision:
        return "STALE", "initial-lease-near-expiry", "rerun-wsta63-then-wsta64"
    return "NOT_READY", decision or "wsta64-not-pass", "inspect-wsta64-result"


def status_from_readiness(wsta64_result: dict[str, Any],
                          now: _dt.datetime,
                          min_remaining: int) -> tuple[dict[str, Any], dict[str, Any]]:
    readiness = wsta64_result.get("readiness") or {}
    status: dict[str, Any] = {
        "source_wsta64_decision": wsta64_result.get("decision"),
        "state": "PUBLIC_OFF",
        "session_state": "NOT_READY",
        "ready_for_live": False,
        "min_initial_seconds_remaining": min_remaining,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    checks: dict[str, Any] = {
        "wsta64_result_private": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    if wsta64_result.get("decision") != wsta64.PASS_DECISION:
        state, reason, next_action = classify_from_wsta64_decision(str(wsta64_result.get("decision") or ""))
        status.update({
            "session_state": state,
            "reason": reason,
            "recommended_next_action": next_action,
        })
        checks["wsta64_pass"] = False
        return status, checks

    initial_value = readiness.get("initial_private_lease_artifact")
    initial_lease, path_error = wsta64.require_private_path(initial_value, "initial-lease")
    if path_error or initial_lease is None:
        status.update({
            "reason": path_error or "initial-lease-missing",
            "recommended_next_action": "rerun-wsta63-then-wsta64",
        })
        checks["initial_private_lease_present"] = False
        return status, checks

    initial_ok, initial_decision, initial_detail = wsta64.wsta58.wsta55.validate_artifact(initial_lease, now)
    remaining = wsta64.seconds_remaining(initial_detail.get("expires_utc"), now)
    status.update({
        "initial_private_lease_artifact": rel(initial_lease),
        "initial_ttl_sec": initial_detail.get("ttl_sec"),
        "initial_seconds_remaining": remaining,
        "renewal_wsta53_result": readiness.get("renewal_wsta53_result"),
        "wsta58_preflight_result": readiness.get("wsta58_preflight_result"),
    })
    checks.update({
        "wsta64_pass": True,
        "initial_private_lease_present": True,
        "initial_private_lease_unexpired": bool(initial_ok),
    })
    if not initial_ok:
        status.update({
            "session_state": "EXPIRED" if "already-expired" in initial_decision else "NOT_READY",
            "reason": initial_decision,
            "recommended_next_action": "rerun-wsta63-then-wsta64",
        })
        return status, checks
    if remaining is None or remaining < min_remaining:
        status.update({
            "session_state": "STALE",
            "reason": "initial-lease-near-expiry",
            "recommended_next_action": "rerun-wsta63-then-wsta64",
        })
        checks["initial_seconds_remaining_min_met"] = False
        return status, checks

    renewal_source, renewal_error = wsta64.require_private_path(readiness.get("renewal_wsta53_result"), "renewal-source")
    if renewal_error or renewal_source is None:
        status.update({
            "session_state": "NOT_READY",
            "reason": renewal_error or "renewal-source-missing",
            "recommended_next_action": "rerun-wsta63-then-wsta64",
        })
        checks["renewal_source_present"] = False
        return status, checks

    preflight, preflight_error = wsta64.require_private_path(readiness.get("wsta58_preflight_result"), "wsta58-preflight")
    if preflight_error or preflight is None:
        status.update({
            "session_state": "NOT_READY",
            "reason": preflight_error or "wsta58-preflight-missing",
            "recommended_next_action": "rerun-wsta63-then-wsta64",
        })
        checks["wsta58_preflight_present"] = False
        return status, checks

    status.update({
        "session_state": "READY",
        "reason": "wsta64-ready-and-lease-fresh",
        "ready_for_live": True,
        "recommended_next_action": "operator-may-run-explicit-wsta58-live-gate",
        "renewal_wsta53_result": rel(renewal_source),
        "wsta58_preflight_result": rel(preflight),
    })
    checks.update({
        "initial_seconds_remaining_min_met": True,
        "renewal_source_present": True,
        "wsta58_preflight_present": True,
        "default_public_off": True,
    })
    return status, checks


def run(args: argparse.Namespace) -> dict[str, Any]:
    now = now_from_args(args)
    ts = utc_stamp(now)
    run_id = args.run_id or f"wsta65-persistent-session-status-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA65 host-only persistent session lifecycle status",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta65-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta65-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta65_result.json"

    if args.wsta64_result_json is None:
        result["decision"] = "wsta65-blocked-wsta64-result-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    wsta64_path, path_error = wsta64.require_private_path(args.wsta64_result_json, "wsta64-result")
    if path_error or wsta64_path is None:
        result["decision"] = path_error or "wsta65-blocked-wsta64-result"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta64_result = load_json(wsta64_path)
    status, checks = status_from_readiness(
        wsta64_result,
        now,
        int(args.min_initial_seconds_remaining),
    )
    status["wsta64_result"] = rel(wsta64_path)
    result["session_status"] = status
    result["checks"] = checks
    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta65-blocked-public-summary-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta64-result-json", type=Path)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
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
        payload = {"decision": "wsta65-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
