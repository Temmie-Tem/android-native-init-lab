#!/usr/bin/env python3
"""WSTA185 expiring WSTA184 handoff execution gate.

Consumes the short-lived WSTA184 WSTA181 execution handoff.  By default this
validates the handoff, its WSTA182 command artifacts, and expiry, then stops
before execution.  Only the full WSTA185 acknowledgement set executes the
embedded WSTA181 command and validates the resulting WSTA181 audit summary.
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
import run_wsta181_seccomp_handoff_execute_audit_gate as wsta181  # noqa: E402
import run_wsta184_seccomp_expiring_execute_handoff as wsta184  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_HANDOFF_JSON = (
    DEFAULT_RUN_BASE
    / "wsta184-seccomp-expiring-execute-handoff-20260705T151924KST"
    / wsta184.HANDOFF_NAME
)
PASS_DECISION = "wsta185-seccomp-expiring-handoff-execute-pass"
SUMMARY_NAME = "wsta185_result.json"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
    if not args.execute_wsta185_handoff:
        return False, "wsta185-blocked-explicit-execution-gate-required"
    if not args.allow_wsta181_command_execution:
        return False, "wsta185-blocked-wsta181-command-execution-allow-required"
    if not args.ack_handoff_fresh:
        return False, "wsta185-blocked-handoff-fresh-ack-required"
    if not args.ack_no_correct_wsta161_token:
        return False, "wsta185-blocked-no-correct-token-ack-required"
    if not args.ack_no_seccomp_load:
        return False, "wsta185-blocked-no-seccomp-load-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta185-blocked-cleanup-ack-required"
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
        "wsta181_execute_command_executed": False,
        "wsta178_execute_command_executed": False,
        "wsta177_execute_command_executed": False,
        "wsta175_execute_command_executed": False,
        "wsta170_execute_command_executed": False,
        "post_run_audit_executed": False,
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
        "handoff": result.get("handoff", {}),
        "freshness": result.get("freshness", {}),
        "checks": result.get("checks", {}),
        "execution": {
            "returncode": result.get("execution", {}).get("returncode"),
            "wsta181_decision": result.get("wsta181_result", {}).get("decision"),
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


def command_text(command: list[str], script_text: str = "") -> str:
    return " ".join(str(item) for item in command) + "\n" + script_text


def validate_handoff(handoff: dict[str, Any], handoff_path: Path) -> dict[str, bool]:
    command = handoff.get("command", [])
    command_json = resolve_path(handoff.get("command_json", ""))
    command_sh = resolve_path(handoff.get("command_script", ""))
    run_dir = command_run_dir(command) if isinstance(command, list) else None
    text = command_text(command) if isinstance(command, list) else ""
    required_flags = (
        "--execute-wsta181-handoff",
        "--allow-wsta178-command-execution",
        "--ack-handoff-ready",
        "--ack-no-correct-wsta161-token",
        "--ack-no-seccomp-load",
        "--ack-post-run-audit-required",
        "--ack-cleanup-required",
    )
    return {
        "handoff_private": wsta160.is_under(handoff_path, PRIVATE_ROOT),
        "schema_ok": handoff.get("schema") == "a90-wsta184-expiring-wsta181-execute-handoff-v1",
        "state_ready_until_expiry": handoff.get("state") == "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "not_executed": handoff.get("executed") is False,
        "no_seccomp_load": handoff.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": handoff.get("seccomp_enforced") is False,
        "no_correct_token": handoff.get("correct_wsta161_token_supplied") is False,
        "secret_values_logged_zero": handoff.get("secret_values_logged") == 0,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta181": (
            isinstance(command, list)
            and "workspace/public/src/scripts/server-distro/run_wsta181_seccomp_handoff_execute_audit_gate.py"
            in command
        ),
        "command_has_wsta181_ack_flags": isinstance(command, list) and all(flag in command for flag in required_flags),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
        "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
        "command_json_present": command_json.is_file(),
        "command_sh_present": command_sh.is_file(),
        "nested_run_dir_private": bool(run_dir and wsta160.is_under(run_dir, PRIVATE_ROOT)),
    }


def validate_command_artifacts(handoff: dict[str, Any]) -> dict[str, bool]:
    command_json = resolve_path(handoff.get("command_json", ""))
    command_sh = resolve_path(handoff.get("command_script", ""))
    if not command_json.is_file() or not command_sh.is_file():
        return {"artifacts_present": False}
    payload = load_json(command_json)
    script_text = command_sh.read_text(encoding="utf-8")
    checks = wsta184.validate_command_payload(payload, script_text)
    checks["payload_command_matches_handoff"] = payload.get("command") == handoff.get("command")
    return checks


def freshness_checks(handoff: dict[str, Any]) -> tuple[dict[str, Any], dict[str, bool]]:
    now = _dt.datetime.now(_dt.timezone.utc)
    freshness = handoff.get("freshness", {})
    expires = parse_utc(freshness.get("expires_utc")) if isinstance(freshness, dict) else None
    age_sec = freshness.get("age_sec") if isinstance(freshness, dict) else None
    max_age_sec = freshness.get("max_age_sec") if isinstance(freshness, dict) else None
    seconds_remaining = int((expires - now).total_seconds()) if expires else None
    summary = {
        "now_utc": utc_stamp(),
        "expires_utc": freshness.get("expires_utc") if isinstance(freshness, dict) else None,
        "age_sec": age_sec,
        "max_age_sec": max_age_sec,
        "seconds_remaining": seconds_remaining,
    }
    checks = {
        "expires_timestamp_present": expires is not None,
        "not_expired": bool(seconds_remaining is not None and seconds_remaining >= 0),
        "bounded_original_age": (
            isinstance(age_sec, int)
            and isinstance(max_age_sec, int)
            and age_sec >= 0
            and age_sec <= max_age_sec
        ),
    }
    return summary, checks


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


def validate_wsta181_result(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    audit = result.get("post_run_audit_result", {})
    deep = result.get("post_run_deep_audit_checks", {})
    return {
        "decision_pass": result.get("decision") == wsta181.PASS_DECISION,
        "handoff_bundle_valid": checks.get("handoff_bundle_valid") is True,
        "execution_packet_valid": checks.get("execution_packet_valid") is True,
        "post_run_audit_command_valid": checks.get("post_run_audit_command_valid") is True,
        "execution_returncode_ok": checks.get("execution_returncode_ok") is True,
        "post_run_audit_returncode_ok": checks.get("post_run_audit_returncode_ok") is True,
        "post_run_audit_result_present": checks.get("post_run_audit_result_present") is True,
        "post_run_audit_result_valid": checks.get("post_run_audit_result_valid") is True,
        "wsta181_handoff_consumed": safety.get("handoff_consumed") is True,
        "wsta178_executed": safety.get("wsta178_execute_command_executed") is True,
        "wsta177_executed": safety.get("wsta177_execute_command_executed") is True,
        "wsta175_executed": safety.get("wsta175_execute_command_executed") is True,
        "wsta170_executed": safety.get("wsta170_execute_command_executed") is True,
        "post_run_audit_executed": safety.get("post_run_audit_executed") is True,
        "live_command_executed": safety.get("live_command_executed") is True,
        "deep_wsta175_executed": deep.get("source_wsta175_executed") is True,
        "deep_wsta170_executed": deep.get("source_wsta170_executed") is True,
        "deep_wsta175_decision_pass": deep.get("wsta175_decision_pass") is True,
        "deep_wsta170_decision_pass": deep.get("wsta170_decision_pass") is True,
        "deep_wsta167_decision_pass": deep.get("wsta167_decision_pass") is True,
        "no_flash": safety.get("boot_flash") is False,
        "no_reboot": safety.get("native_reboot") is False,
        "no_wifi": safety.get("wifi_connect") is False,
        "no_dhcp": safety.get("dhcp") is False,
        "no_public_tunnel": safety.get("public_tunnel") is False,
        "no_packet_filter_mutation": safety.get("packet_filter_mutation") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "post_run_audit_decision_pass": audit.get("decision") == wsta181.wsta179.PASS_DECISION,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("handoff_valid", "wsta185-blocked-handoff-invalid"),
        ("command_artifacts_valid", "wsta185-blocked-command-artifacts-invalid"),
        ("freshness_valid", "wsta185-blocked-handoff-expired-or-stale"),
        ("explicit_execution_gate", result.get("gate_decision") or "wsta185-blocked-explicit-execution-gate-required"),
        ("execution_returncode_ok", "wsta185-blocked-wsta181-returncode"),
        ("wsta181_result_present", "wsta185-blocked-wsta181-result-missing"),
        ("wsta181_result_valid", "wsta185-blocked-wsta181-result-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta185-seccomp-expiring-handoff-execute-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    handoff_json = resolve_path(args.handoff_json)
    gate_ok, gate_decision = explicit_execution_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA185 expiring WSTA184 handoff execute gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "handoff_json": rel(handoff_json),
        "gate_decision": gate_decision,
        "safety": safety_flags(gate_ok),
        "checks": {
            "explicit_execution_gate": gate_ok,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "handoff_json_private": wsta160.is_under(handoff_json, PRIVATE_ROOT),
            "handoff_json_present": handoff_json.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta185-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("handoff_json_private", "wsta185-blocked-handoff-json-nonprivate"),
        ("handoff_json_present", "wsta185-blocked-handoff-json-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    handoff = load_json(handoff_json)
    command = handoff.get("command", [])
    command_dir = command_run_dir(command) if isinstance(command, list) else None
    wsta181_result_path = command_dir / wsta181.SUMMARY_NAME if command_dir else None
    result["handoff"] = {
        "state": handoff.get("state"),
        "command_json": handoff.get("command_json"),
        "command_script": handoff.get("command_script"),
        "wsta181_run_dir": rel(command_dir) if command_dir else None,
        "wsta181_result_json": rel(wsta181_result_path) if wsta181_result_path else None,
        "executed": handoff.get("executed"),
    }
    result["handoff_checks"] = validate_handoff(handoff, handoff_json)
    result["command_artifact_checks"] = validate_command_artifacts(handoff)
    result["freshness"], result["freshness_checks"] = freshness_checks(handoff)
    result["checks"]["handoff_valid"] = all(result["handoff_checks"].values())
    result["checks"]["command_artifacts_valid"] = all(result["command_artifact_checks"].values())
    result["checks"]["freshness_valid"] = all(result["freshness_checks"].values())
    write_json(out_path, result)
    if (
        not result["checks"]["handoff_valid"]
        or not result["checks"]["command_artifacts_valid"]
        or not result["checks"]["freshness_valid"]
        or not gate_ok
    ):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    assert isinstance(command, list)
    result["safety"]["device_action"] = "wsta185-wsta181-expiring-handoff-no-load-live-observation"
    result["safety"]["handoff_consumed"] = True
    result["safety"]["wsta181_execute_command_executed"] = True
    result["safety"]["wsta178_execute_command_executed"] = True
    result["safety"]["wsta177_execute_command_executed"] = True
    result["safety"]["live_command_executed"] = True
    result["execution"] = run_generated_command(command, timeout=args.execution_timeout)
    result["checks"]["execution_returncode_ok"] = result["execution"].get("returncode") == 0
    result["checks"]["wsta181_result_present"] = bool(wsta181_result_path and wsta181_result_path.is_file())
    if result["checks"]["wsta181_result_present"] and wsta181_result_path is not None:
        wsta181_result = load_json(wsta181_result_path)
        result["wsta181_result"] = {
            "decision": wsta181_result.get("decision"),
            "post_run_audit_decision": wsta181_result.get("post_run_audit_result", {}).get("decision"),
            "deep_audit": wsta181_result.get("post_run_deep_audit_checks", {}),
        }
        result["wsta181_result_checks"] = validate_wsta181_result(wsta181_result)
        result["checks"]["wsta181_result_valid"] = all(result["wsta181_result_checks"].values())
        if wsta181_result.get("safety", {}).get("post_run_audit_executed") is True:
            result["safety"]["post_run_audit_executed"] = True
        if wsta181_result.get("safety", {}).get("wsta175_execute_command_executed") is True:
            result["safety"]["wsta175_execute_command_executed"] = True
        if wsta181_result.get("safety", {}).get("wsta170_execute_command_executed") is True:
            result["safety"]["wsta170_execute_command_executed"] = True
    else:
        result["wsta181_result"] = {}
        result["wsta181_result_checks"] = {}
        result["checks"]["wsta181_result_valid"] = False
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
    parser.add_argument("--execute-wsta185-handoff", action="store_true")
    parser.add_argument("--allow-wsta181-command-execution", action="store_true")
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
        payload = {"decision": "wsta185-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
