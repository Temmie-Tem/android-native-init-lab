#!/usr/bin/env python3
"""WSTA174 one-shot fresh expiring handoff for WSTA170 execution.

Runs WSTA172 to refresh readiness/source-gate/preflight, then immediately runs
WSTA173 to wrap the generated command in an expiring handoff.  This does not
execute the WSTA170 command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for _path in (SCRIPT_DIR, SCRIPT_DIR.parent / "revalidation"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta172_seccomp_fresh_execute_preflight as wsta172  # noqa: E402
import run_wsta173_seccomp_expiring_execute_handoff as wsta173  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA168_COMMAND_JSON = wsta172.DEFAULT_WSTA168_COMMAND_JSON
DEFAULT_WSTA168_COMMAND_SH = wsta172.DEFAULT_WSTA168_COMMAND_SH
PASS_DECISION = "wsta174-seccomp-fresh-expiring-handoff-pass"
SUMMARY_NAME = "wsta174_result.json"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": "read-only-status-only",
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "wsta170_execute_command_generated": False,
        "handoff_generated": False,
        "wsta170_execute_command_executed": False,
        "live_command_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "fresh_preflight": result.get("fresh_preflight", {}),
        "expiring_handoff": result.get("expiring_handoff", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def wsta172_args(
    run_dir: Path,
    command_json: Path,
    command_sh: Path,
    readiness_timeout: float,
    execution_timeout: float,
) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta174-wsta172-fresh-execute-preflight",
        run_dir=run_dir,
        wsta168_command_json=command_json,
        wsta168_command_sh=command_sh,
        readiness_timeout=readiness_timeout,
        execution_timeout=execution_timeout,
        emit_fresh_wsta170_execute_preflight=True,
        print_full_json=False,
    )


def wsta173_args(run_dir: Path, wsta172_result_json: Path, max_age_sec: int) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta174-wsta173-expiring-handoff",
        run_dir=run_dir,
        wsta172_proof_json=wsta172_result_json,
        max_age_sec=max_age_sec,
        emit_expiring_handoff=True,
        print_full_json=False,
    )


def validate_fresh_preflight(result: dict[str, Any], command_json: Path, command_sh: Path) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    return {
        "decision_pass": result.get("decision") == wsta172.PASS_DECISION,
        "gate_ok": result.get("gate_decision") == "ok",
        "fresh_readiness_valid": checks.get("fresh_readiness_valid") is True,
        "source_gate_valid": checks.get("source_gate_valid") is True,
        "execute_preflight_valid": checks.get("execute_preflight_valid") is True,
        "wsta168_json_path_matches": result.get("wsta168_command_json") == rel(command_json),
        "wsta168_sh_path_matches": result.get("wsta168_command_sh") == rel(command_sh),
        "command_generated": safety.get("wsta170_execute_command_generated") is True,
        "command_not_executed": safety.get("wsta170_execute_command_executed") is False,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def validate_expiring_handoff(result: dict[str, Any], wsta172_result_json: Path) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    handoff = result.get("handoff", {})
    return {
        "decision_pass": result.get("decision") == wsta173.PASS_DECISION,
        "gate_ok": result.get("gate_decision") == "ok",
        "freshness_valid": checks.get("freshness_valid") is True,
        "wsta172_valid": checks.get("wsta172_valid") is True,
        "nested_valid": checks.get("nested_valid") is True,
        "command_valid": checks.get("command_valid") is True,
        "wsta172_path_matches": result.get("wsta172_proof_json") == rel(wsta172_result_json),
        "handoff_state_ready": handoff.get("state") == "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "handoff_not_executed": handoff.get("executed") is False,
        "handoff_generated": safety.get("handoff_generated") is True,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta174-seccomp-fresh-expiring-handoff-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    command_json = resolve_path(args.wsta168_command_json)
    command_sh = resolve_path(args.wsta168_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA174 one-shot fresh expiring WSTA170 handoff",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta168_command_json": rel(command_json),
        "wsta168_command_sh": rel(command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_bundle_gate": bool(args.emit_fresh_expiring_handoff),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta168_command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
            "wsta168_command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
            "wsta168_command_json_present": command_json.is_file(),
            "wsta168_command_sh_present": command_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta174-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_bundle_gate", "wsta174-blocked-explicit-bundle-gate-required"),
        ("wsta168_command_json_private", "wsta174-blocked-wsta168-command-json-nonprivate"),
        ("wsta168_command_sh_private", "wsta174-blocked-wsta168-command-sh-nonprivate"),
        ("wsta168_command_json_present", "wsta174-blocked-wsta168-command-json-missing"),
        ("wsta168_command_sh_present", "wsta174-blocked-wsta168-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    fresh_dir = run_dir / "wsta172-fresh-execute-preflight"
    handoff_dir = run_dir / "wsta173-expiring-handoff"
    fresh_result = wsta172.run(
        wsta172_args(fresh_dir, command_json, command_sh, args.readiness_timeout, args.execution_timeout)
    )
    fresh_json = fresh_dir / wsta172.SUMMARY_NAME
    result["fresh_preflight"] = {
        "run_dir": rel(fresh_dir),
        "result_json": rel(fresh_json),
        "decision": fresh_result.get("decision"),
        "execute_command_json": fresh_result.get("execute_preflight", {}).get("command_json"),
        "execute_command_script": fresh_result.get("execute_preflight", {}).get("command_script"),
    }
    result["fresh_preflight_checks"] = validate_fresh_preflight(fresh_result, command_json, command_sh)
    result["checks"]["fresh_preflight_valid"] = all(result["fresh_preflight_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["fresh_preflight_valid"]:
        result["decision"] = "wsta174-blocked-fresh-preflight-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    handoff_result = wsta173.run(wsta173_args(handoff_dir, fresh_json, int(args.max_age_sec)))
    result["expiring_handoff"] = {
        "run_dir": rel(handoff_dir),
        "result_json": rel(handoff_dir / wsta173.SUMMARY_NAME),
        "decision": handoff_result.get("decision"),
        "handoff_json": handoff_result.get("handoff", {}).get("handoff_json"),
        "handoff_state": handoff_result.get("handoff", {}).get("state"),
        "expires_utc": handoff_result.get("handoff", {}).get("expires_utc"),
        "command_json": handoff_result.get("handoff", {}).get("command_json"),
        "command_script": handoff_result.get("handoff", {}).get("command_script"),
        "executed": handoff_result.get("handoff", {}).get("executed"),
    }
    result["expiring_handoff_checks"] = validate_expiring_handoff(handoff_result, fresh_json)
    result["checks"]["expiring_handoff_valid"] = all(result["expiring_handoff_checks"].values())
    result["safety"]["wsta170_execute_command_generated"] = result["checks"]["fresh_preflight_valid"]
    result["safety"]["handoff_generated"] = result["checks"]["expiring_handoff_valid"]
    all_ok = result["checks"]["fresh_preflight_valid"] and result["checks"]["expiring_handoff_valid"]
    result["decision"] = PASS_DECISION if all_ok else "wsta174-blocked-expiring-handoff-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta168-command-json", type=Path, default=DEFAULT_WSTA168_COMMAND_JSON)
    parser.add_argument("--wsta168-command-sh", type=Path, default=DEFAULT_WSTA168_COMMAND_SH)
    parser.add_argument("--readiness-timeout", type=float, default=20.0)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--max-age-sec", type=int, default=900)
    parser.add_argument("--emit-fresh-expiring-handoff", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta174-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
