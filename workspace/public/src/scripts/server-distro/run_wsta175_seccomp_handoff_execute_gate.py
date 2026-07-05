#!/usr/bin/env python3
"""WSTA175 handoff-aware execution gate for the no-load seccomp observation.

Consumes a WSTA173/WSTA174 expiring handoff and, by default, stops before
execution after validating freshness and command safety.  Only the full WSTA175
acknowledgement set executes the contained WSTA170 command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for _path in (SCRIPT_DIR, SCRIPT_DIR.parent / "revalidation"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta170_seccomp_live_observation_execute as wsta170  # noqa: E402
import run_wsta173_seccomp_expiring_execute_handoff as wsta173  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_HANDOFF_JSON = (
    DEFAULT_RUN_BASE
    / "wsta174-seccomp-fresh-expiring-handoff-20260705T142628KST"
    / "wsta173-expiring-handoff"
    / wsta173.HANDOFF_NAME
)
PASS_DECISION = "wsta175-seccomp-handoff-execute-pass"
SUMMARY_NAME = "wsta175_result.json"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def parse_utc(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


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


def explicit_execution_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_wsta175_handoff:
        return False, "wsta175-blocked-explicit-execution-gate-required"
    if not args.allow_wsta170_command_execution:
        return False, "wsta175-blocked-wsta170-command-execution-allow-required"
    if not args.ack_handoff_fresh:
        return False, "wsta175-blocked-handoff-fresh-ack-required"
    if not args.ack_no_correct_wsta161_token:
        return False, "wsta175-blocked-no-correct-token-ack-required"
    if not args.ack_no_seccomp_load:
        return False, "wsta175-blocked-no-seccomp-load-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta175-blocked-cleanup-ack-required"
    return True, "ok"


def safety_flags(gate_ok: bool) -> dict[str, Any]:
    return {
        "device_action_requested": gate_ok,
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
        "handoff_consumed": False,
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
        "freshness": result.get("freshness", {}),
        "checks": result.get("checks", {}),
        "execution": {
            "returncode": result.get("execution", {}).get("returncode"),
            "wsta170_result": result.get("wsta170_result_path"),
            "wsta170_decision": result.get("wsta170_result", {}).get("decision"),
        },
        "safety": result.get("safety", {}),
    }


def command_run_dir(command: list[str]) -> Path | None:
    try:
        idx = command.index("--run-dir")
        value = command[idx + 1]
    except (ValueError, IndexError):
        return None
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def freshness_checks(handoff: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool]]:
    freshness = handoff.get("freshness", {})
    expires = parse_utc(freshness.get("expires_utc"))
    readiness_end = parse_utc(freshness.get("readiness_ended_utc"))
    now = now_utc()
    seconds_remaining = int((expires - now).total_seconds()) if expires else None
    observed = {
        "now_utc": now.strftime("%Y%m%dT%H%M%SZ"),
        "expires_utc": freshness.get("expires_utc"),
        "seconds_remaining": seconds_remaining,
        "readiness_ended_utc": freshness.get("readiness_ended_utc"),
        "max_age_sec": freshness.get("max_age_sec"),
    }
    return observed, {
        "expires_present": expires is not None,
        "readiness_timestamp_present": readiness_end is not None,
        "not_expired": bool(seconds_remaining is not None and seconds_remaining >= 0),
    }


def validate_handoff(handoff: dict[str, Any], handoff_path: Path) -> dict[str, bool]:
    command = handoff.get("command", [])
    command_text = " ".join(str(item) for item in command)
    command_json = resolve_path(handoff.get("command_json", ""))
    command_sh = resolve_path(handoff.get("command_script", ""))
    nested_run_dir = command_run_dir(command) if all(isinstance(item, str) for item in command) else None
    return {
        "handoff_private": wsta160.is_under(handoff_path, PRIVATE_ROOT),
        "schema_ok": handoff.get("schema") == "a90-wsta173-expiring-wsta170-execute-handoff-v1",
        "state_ready": handoff.get("state") == "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "handoff_not_executed": handoff.get("executed") is False,
        "no_seccomp_load": handoff.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": handoff.get("seccomp_enforced") is False,
        "no_correct_token": handoff.get("correct_wsta161_token_supplied") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta170": (
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py" in command
        ),
        "command_has_execute_gate": "--execute-wsta170-no-load-live-observation" in command,
        "command_has_allow_gate": "--allow-wsta168-command-execution" in command,
        "command_has_fresh_ack": "--ack-readiness-proof-current" in command,
        "command_has_no_correct_token_ack": "--ack-no-correct-wsta161-token" in command,
        "command_has_no_load_ack": "--ack-no-seccomp-load" in command,
        "command_has_cleanup_ack": "--ack-cleanup-required" in command,
        "command_excludes_correct_token": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in command_text,
        "command_excludes_public_tunnel": "cloudflared" not in command_text and "tunnel" not in command_text.lower(),
        "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
        "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
        "command_json_present": command_json.is_file(),
        "command_sh_present": command_sh.is_file(),
        "nested_run_dir_private": bool(nested_run_dir and wsta160.is_under(nested_run_dir, PRIVATE_ROOT)),
    }


def validate_command_artifacts(handoff: dict[str, Any]) -> dict[str, bool]:
    command_json = resolve_path(handoff.get("command_json", ""))
    command_sh = resolve_path(handoff.get("command_script", ""))
    command_payload = load_json(command_json) if command_json.is_file() else {}
    script_text = command_sh.read_text(encoding="utf-8") if command_sh.is_file() else ""
    return wsta173.validate_command_payload(command_payload, script_text)


def validate_wsta170_result(result: dict[str, Any]) -> dict[str, bool]:
    safety = result.get("safety", {})
    checks = result.get("checks", {})
    nested = result.get("nested_result", {})
    nested_checks = result.get("nested_checks", {})
    return {
        "decision_pass": result.get("decision") == wsta170.PASS_DECISION,
        "execution_returncode_ok": checks.get("execution_returncode_ok") is True,
        "nested_result_present": checks.get("nested_result_present") is True,
        "nested_result_valid": checks.get("nested_result_valid") is True,
        "nested_decision_pass": nested.get("decision") == wsta170.wsta167.PASS_DECISION,
        "nested_checks_true": bool(nested_checks) and all(value is True for value in nested_checks.values()),
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "no_flash": safety.get("boot_flash") is False,
        "no_reboot": safety.get("native_reboot") is False,
        "no_wifi": safety.get("wifi_connect") is False,
        "no_dhcp": safety.get("dhcp") is False,
        "no_public_tunnel": safety.get("public_tunnel") is False,
        "no_packet_filter_mutation": safety.get("packet_filter_mutation") is False,
    }


def run_generated_command(command: list[str], *, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_execution_gate", "wsta175-blocked-explicit-execution-gate-required"),
        ("handoff_valid", "wsta175-blocked-handoff-invalid"),
        ("handoff_fresh", "wsta175-blocked-handoff-expired"),
        ("command_artifacts_valid", "wsta175-blocked-command-artifacts-invalid"),
        ("execution_returncode_ok", "wsta175-blocked-execution-returncode"),
        ("wsta170_result_present", "wsta175-blocked-wsta170-result-missing"),
        ("wsta170_result_valid", "wsta175-blocked-wsta170-result-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta175-seccomp-handoff-execute-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    handoff_path = resolve_path(args.handoff_json)
    gate_ok, gate_decision = explicit_execution_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA175 handoff-aware no-load seccomp executor",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "handoff_json": rel(handoff_path),
        "gate_decision": gate_decision,
        "safety": safety_flags(gate_ok),
        "checks": {
            "explicit_execution_gate": gate_ok,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "handoff_private": wsta160.is_under(handoff_path, PRIVATE_ROOT),
            "handoff_present": handoff_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta175-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("handoff_private", "wsta175-blocked-handoff-nonprivate"),
        ("handoff_present", "wsta175-blocked-handoff-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    handoff = load_json(handoff_path)
    freshness, freshness_result = freshness_checks(handoff)
    handoff_checks = validate_handoff(handoff, handoff_path)
    command_artifact_checks = validate_command_artifacts(handoff)
    result["freshness"] = freshness
    result["freshness_checks"] = freshness_result
    result["handoff_checks"] = handoff_checks
    result["command_artifact_checks"] = command_artifact_checks
    result["checks"]["handoff_valid"] = all(handoff_checks.values())
    result["checks"]["handoff_fresh"] = all(freshness_result.values())
    result["checks"]["command_artifacts_valid"] = all(command_artifact_checks.values())
    write_json(out_path, result)

    if (
        not gate_ok
        or not result["checks"]["handoff_valid"]
        or not result["checks"]["handoff_fresh"]
        or not result["checks"]["command_artifacts_valid"]
    ):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    command = handoff["command"]
    nested_run_dir = command_run_dir(command)
    wsta170_result_path = nested_run_dir / wsta170.SUMMARY_NAME if nested_run_dir else None
    result["wsta170_result_path"] = rel(wsta170_result_path) if wsta170_result_path else None
    result["safety"]["device_action"] = "wsta170-handoff-no-load-live-observation"
    result["safety"]["handoff_consumed"] = True
    result["safety"]["wsta170_execute_command_executed"] = True
    result["safety"]["live_command_executed"] = True
    result["execution"] = run_generated_command(command, timeout=args.execution_timeout)
    result["checks"]["execution_returncode_ok"] = result["execution"].get("returncode") == 0
    result["checks"]["wsta170_result_present"] = bool(wsta170_result_path and wsta170_result_path.is_file())
    if result["checks"]["wsta170_result_present"] and wsta170_result_path is not None:
        wsta170_result = load_json(wsta170_result_path)
        result["wsta170_result"] = wsta170_result
        result["wsta170_checks"] = validate_wsta170_result(wsta170_result)
        result["checks"]["wsta170_result_valid"] = all(result["wsta170_checks"].values())
    else:
        result["wsta170_result"] = {}
        result["wsta170_checks"] = {}
        result["checks"]["wsta170_result_valid"] = False
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--handoff-json", type=Path, default=DEFAULT_HANDOFF_JSON)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--execute-wsta175-handoff", action="store_true")
    parser.add_argument("--allow-wsta170-command-execution", action="store_true")
    parser.add_argument("--ack-handoff-fresh", action="store_true")
    parser.add_argument("--ack-no-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-no-seccomp-load", action="store_true")
    parser.add_argument("--ack-cleanup-required", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta175-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
