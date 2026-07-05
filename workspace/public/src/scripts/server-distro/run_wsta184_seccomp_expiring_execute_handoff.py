#!/usr/bin/env python3
"""WSTA184 expiring handoff for the WSTA183/WSTA182 execution command.

Runs WSTA183 to refresh WSTA181 source-gate/readiness evidence, validates the
fresh WSTA182 command packet, and emits a short-lived WSTA181 execution handoff.
This unit does not execute WSTA181.
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
import run_wsta182_seccomp_live_readiness_status as wsta182  # noqa: E402
import run_wsta183_seccomp_fresh_readiness_status as wsta183  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA180_BUNDLE_JSON = wsta183.DEFAULT_WSTA180_BUNDLE_JSON
DEFAULT_WSTA180_BUNDLE_SH = wsta183.DEFAULT_WSTA180_BUNDLE_SH
PASS_DECISION = "wsta184-seccomp-expiring-execute-handoff-pass"
SUMMARY_NAME = "wsta184_result.json"
HANDOFF_NAME = "wsta184_expiring_wsta181_execute_handoff.json"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp() -> str:
    return format_utc(now_utc())


def parse_utc(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def format_utc(value: _dt.datetime) -> str:
    return value.astimezone(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "fresh_readiness_generated": False,
        "handoff_generated": False,
        "wsta181_execute_command_generated": False,
        "wsta181_execute_command_executed": False,
        "wsta178_execute_command_executed": False,
        "wsta177_execute_command_executed": False,
        "wsta175_execute_command_executed": False,
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
        "freshness": result.get("freshness", {}),
        "handoff": result.get("handoff", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def wsta183_args(
    run_dir: Path,
    bundle_json: Path,
    bundle_sh: Path,
    execution_timeout: float,
    audit_timeout: float,
) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta184-wsta183-fresh-readiness",
        run_dir=run_dir,
        wsta180_bundle_json=bundle_json,
        wsta180_bundle_sh=bundle_sh,
        execution_timeout=execution_timeout,
        audit_timeout=audit_timeout,
        emit_wsta183_fresh_readiness=True,
        print_full_json=False,
    )


def path_from_result(result: dict[str, Any], *keys: str) -> Path | None:
    value: Any = result
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if not isinstance(value, str) or not value:
        return None
    return resolve_path(value)


def validate_fresh_readiness(result: dict[str, Any], bundle_json: Path, bundle_sh: Path) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    readiness = result.get("readiness", {})
    return {
        "decision_pass": result.get("decision") == wsta183.PASS_DECISION,
        "fresh_source_gate_valid": checks.get("fresh_source_gate_valid") is True,
        "readiness_valid": checks.get("readiness_valid") is True,
        "bundle_path_matches": result.get("wsta180_bundle_json") == rel(bundle_json),
        "bundle_script_matches": result.get("wsta180_bundle_sh") == rel(bundle_sh),
        "status_ready": readiness.get("state") == "READY_FOR_EXPLICIT_OPERATOR_APPROVAL",
        "command_json_present": bool(path_from_result(result, "readiness", "command_json")),
        "command_script_present": bool(path_from_result(result, "readiness", "command_script")),
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_wsta181_execution": safety.get("wsta181_execute_command_executed") is False,
        "no_wsta178_execution": safety.get("wsta178_execute_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def validate_readiness_result(readiness: dict[str, Any], command_json: Path, command_sh: Path) -> dict[str, bool]:
    checks = readiness.get("checks", {})
    safety = readiness.get("safety", {})
    command = readiness.get("command", {})
    status = readiness.get("status", {})
    return {
        "decision_pass": readiness.get("decision") == wsta182.PASS_DECISION,
        "source_gate_valid": checks.get("source_gate_valid") is True,
        "execution_command_valid": checks.get("execution_command_valid") is True,
        "status_ready": status.get("state") == "READY_FOR_EXPLICIT_OPERATOR_APPROVAL",
        "command_ready": command.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "command_not_executed": command.get("executed") is False,
        "command_json_matches": command.get("command_json") == rel(command_json),
        "command_script_matches": command.get("command_script") == rel(command_sh),
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_wsta181_execution": safety.get("wsta181_execute_command_executed") is False,
        "no_wsta178_execution": safety.get("wsta178_execute_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def validate_command_payload(payload: dict[str, Any], script_text: str) -> dict[str, bool]:
    return wsta182.validate_execution_command(payload, script_text)


def validate_freshness(
    fresh_result: dict[str, Any],
    readiness_result: dict[str, Any],
    max_age_sec: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    now = now_utc()
    fresh_end = parse_utc(fresh_result.get("ended_utc"))
    readiness_end = parse_utc(readiness_result.get("ended_utc"))
    timestamps = [item for item in (fresh_end, readiness_end) if item is not None]
    newest = max(timestamps) if timestamps else None
    oldest = min(timestamps) if timestamps else None
    anchor = readiness_end or fresh_end
    age = int((now - anchor).total_seconds()) if anchor else None
    expires = anchor + _dt.timedelta(seconds=max_age_sec) if anchor else None
    freshness = {
        "now_utc": format_utc(now),
        "fresh_readiness_ended_utc": format_utc(fresh_end) if fresh_end else None,
        "readiness_ended_utc": format_utc(readiness_end) if readiness_end else None,
        "age_sec": age,
        "max_age_sec": max_age_sec,
        "expires_utc": format_utc(expires) if expires else None,
        "spread_sec": int((newest - oldest).total_seconds()) if newest and oldest else None,
    }
    checks = {
        "timestamps_present": bool(fresh_end and readiness_end),
        "not_from_future": bool(age is not None and age >= 0),
        "within_max_age": bool(age is not None and age <= max_age_sec),
        "bounded_spread": bool(freshness["spread_sec"] is not None and freshness["spread_sec"] <= 60),
    }
    return freshness, checks


def handoff_payload(
    fresh_result_path: Path,
    readiness_result_path: Path,
    command_json: Path,
    command_sh: Path,
    command_payload_obj: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "a90-wsta184-expiring-wsta181-execute-handoff-v1",
        "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "wsta183_result": rel(fresh_result_path),
        "wsta182_result": rel(readiness_result_path),
        "command_json": rel(command_json),
        "command_script": rel(command_sh),
        "command": command_payload_obj.get("command", []),
        "required_ack_flags": command_payload_obj.get("required_ack_flags", []),
        "expected_outcome": command_payload_obj.get("expected_outcome", {}),
        "freshness": freshness,
        "executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta184-seccomp-expiring-execute-handoff-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    bundle_json = resolve_path(args.wsta180_bundle_json)
    bundle_sh = resolve_path(args.wsta180_bundle_sh)
    result: dict[str, Any] = {
        "scope": "WSTA184 expiring WSTA181 execution handoff",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta180_bundle_json": rel(bundle_json),
        "wsta180_bundle_sh": rel(bundle_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_handoff_gate": bool(args.emit_expiring_handoff),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "bundle_json_private": wsta160.is_under(bundle_json, PRIVATE_ROOT),
            "bundle_sh_private": wsta160.is_under(bundle_sh, PRIVATE_ROOT),
            "bundle_json_present": bundle_json.is_file(),
            "bundle_sh_present": bundle_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta184-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_handoff_gate", "wsta184-blocked-explicit-handoff-gate-required"),
        ("bundle_json_private", "wsta184-blocked-bundle-json-nonprivate"),
        ("bundle_sh_private", "wsta184-blocked-bundle-sh-nonprivate"),
        ("bundle_json_present", "wsta184-blocked-bundle-json-missing"),
        ("bundle_sh_present", "wsta184-blocked-bundle-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    fresh_dir = run_dir / "fresh-wsta183-readiness"
    fresh_result = wsta183.run(
        wsta183_args(
            fresh_dir,
            bundle_json,
            bundle_sh,
            args.execution_timeout,
            args.audit_timeout,
        )
    )
    fresh_result_path = fresh_dir / wsta183.SUMMARY_NAME
    readiness_result_path = path_from_result(fresh_result, "readiness", "result_json")
    command_json = path_from_result(fresh_result, "readiness", "command_json")
    command_sh = path_from_result(fresh_result, "readiness", "command_script")
    result["fresh_readiness"] = {
        "run_dir": rel(fresh_dir),
        "result_json": rel(fresh_result_path),
        "decision": fresh_result.get("decision"),
        "readiness_result_json": rel(readiness_result_path) if readiness_result_path else None,
        "command_json": rel(command_json) if command_json else None,
        "command_script": rel(command_sh) if command_sh else None,
    }
    path_checks = {
        "readiness_result_private": bool(readiness_result_path and wsta160.is_under(readiness_result_path, PRIVATE_ROOT)),
        "command_json_private": bool(command_json and wsta160.is_under(command_json, PRIVATE_ROOT)),
        "command_sh_private": bool(command_sh and wsta160.is_under(command_sh, PRIVATE_ROOT)),
        "readiness_result_present": bool(readiness_result_path and readiness_result_path.is_file()),
        "command_json_present": bool(command_json and command_json.is_file()),
        "command_sh_present": bool(command_sh and command_sh.is_file()),
    }
    result["path_checks"] = path_checks
    result["fresh_readiness_checks"] = validate_fresh_readiness(fresh_result, bundle_json, bundle_sh)
    result["checks"]["fresh_readiness_valid"] = all(result["fresh_readiness_checks"].values())
    result["checks"]["paths_valid"] = all(path_checks.values())
    result["safety"]["fresh_readiness_generated"] = True
    write_json(out_path, result)
    if not (result["checks"]["fresh_readiness_valid"] and result["checks"]["paths_valid"]):
        result["decision"] = "wsta184-blocked-fresh-readiness-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    assert readiness_result_path is not None
    assert command_json is not None
    assert command_sh is not None
    readiness_result = load_json(readiness_result_path)
    command_payload_obj = load_json(command_json)
    command_script = command_sh.read_text(encoding="utf-8")
    freshness, freshness_checks = validate_freshness(fresh_result, readiness_result, int(args.max_age_sec))
    result["freshness"] = freshness
    result["freshness_checks"] = freshness_checks
    result["readiness_checks"] = validate_readiness_result(readiness_result, command_json, command_sh)
    result["command_checks"] = validate_command_payload(command_payload_obj, command_script)
    result["checks"]["freshness_valid"] = all(freshness_checks.values())
    result["checks"]["readiness_valid"] = all(result["readiness_checks"].values())
    result["checks"]["command_valid"] = all(result["command_checks"].values())
    all_ok = all(result["checks"][key] for key in ("freshness_valid", "readiness_valid", "command_valid"))
    result["decision"] = PASS_DECISION if all_ok else "wsta184-blocked-handoff-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["handoff"] = {
        "handoff_json": rel(run_dir / HANDOFF_NAME),
        "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY" if all_ok else "BLOCKED",
        "expires_utc": freshness.get("expires_utc"),
        "command_json": rel(command_json),
        "command_script": rel(command_sh),
        "executed": False,
    }
    if all_ok:
        result["safety"]["handoff_generated"] = True
        result["safety"]["wsta181_execute_command_generated"] = True
        write_json(
            run_dir / HANDOFF_NAME,
            handoff_payload(
                fresh_result_path,
                readiness_result_path,
                command_json,
                command_sh,
                command_payload_obj,
                freshness,
            ),
        )
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta180-bundle-json", type=Path, default=DEFAULT_WSTA180_BUNDLE_JSON)
    parser.add_argument("--wsta180-bundle-sh", type=Path, default=DEFAULT_WSTA180_BUNDLE_SH)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--audit-timeout", type=float, default=1800.0)
    parser.add_argument("--max-age-sec", type=int, default=900)
    parser.add_argument("--emit-expiring-handoff", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta184-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
