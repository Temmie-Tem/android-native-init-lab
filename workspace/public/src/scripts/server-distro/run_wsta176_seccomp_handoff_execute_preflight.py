#!/usr/bin/env python3
"""WSTA176 host-only preflight for WSTA175 handoff execution.

Runs WSTA174 to create a fresh expiring handoff, validates it through WSTA175's
source gate, and emits the exact WSTA175 execution command.  This unit does not
execute the command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shlex
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for _path in (SCRIPT_DIR, SCRIPT_DIR.parent / "revalidation"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta174_seccomp_fresh_expiring_handoff as wsta174  # noqa: E402
import run_wsta175_seccomp_handoff_execute_gate as wsta175  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA168_COMMAND_JSON = wsta174.DEFAULT_WSTA168_COMMAND_JSON
DEFAULT_WSTA168_COMMAND_SH = wsta174.DEFAULT_WSTA168_COMMAND_SH
PASS_DECISION = "wsta176-seccomp-handoff-execute-preflight-pass"
SUMMARY_NAME = "wsta176_result.json"
COMMAND_JSON_NAME = "wsta176_wsta175_execute_command.json"
COMMAND_SH_NAME = "wsta176_wsta175_execute_command.sh"
EXECUTION_RUN_ID = "wsta176-seccomp-handoff-execute"


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
        "handoff_generated": False,
        "wsta175_execute_command_generated": False,
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
        "gate_decision": result.get("gate_decision"),
        "fresh_handoff": result.get("fresh_handoff", {}),
        "source_gate": result.get("source_gate", {}),
        "command": result.get("command", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def wsta174_args(
    run_dir: Path,
    command_json: Path,
    command_sh: Path,
    readiness_timeout: float,
    execution_timeout: float,
    max_age_sec: int,
) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta176-wsta174-fresh-expiring-handoff",
        run_dir=run_dir,
        wsta168_command_json=command_json,
        wsta168_command_sh=command_sh,
        readiness_timeout=readiness_timeout,
        execution_timeout=execution_timeout,
        max_age_sec=max_age_sec,
        emit_fresh_expiring_handoff=True,
        print_full_json=False,
    )


def wsta175_source_gate_args(run_dir: Path, handoff_json: Path, execution_timeout: float) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta176-wsta175-source-gate",
        run_dir=run_dir,
        handoff_json=handoff_json,
        execution_timeout=execution_timeout,
        execute_wsta175_handoff=False,
        allow_wsta170_command_execution=False,
        ack_handoff_fresh=False,
        ack_no_correct_wsta161_token=False,
        ack_no_seccomp_load=False,
        ack_cleanup_required=False,
        print_full_json=False,
    )


def execution_command(run_dir: Path, handoff_json: Path, execution_timeout: float) -> list[str]:
    return [
        "python3",
        "workspace/public/src/scripts/server-distro/run_wsta175_seccomp_handoff_execute_gate.py",
        "--run-id",
        EXECUTION_RUN_ID,
        "--run-dir",
        rel(run_dir / "wsta175-live-run"),
        "--handoff-json",
        rel(handoff_json),
        "--execution-timeout",
        str(execution_timeout),
        "--execute-wsta175-handoff",
        "--allow-wsta170-command-execution",
        "--ack-handoff-fresh",
        "--ack-no-correct-wsta161-token",
        "--ack-no-seccomp-load",
        "--ack-cleanup-required",
    ]


def command_payload(command: list[str]) -> dict[str, Any]:
    return {
        "schema": "a90-wsta176-wsta175-execute-command-v1",
        "state": "READY_TO_RUN_NOT_EXECUTED",
        "command": command,
        "required_ack_flags": [
            "--execute-wsta175-handoff",
            "--allow-wsta170-command-execution",
            "--ack-handoff-fresh",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ],
        "expected_outcome": {
            "decision": wsta175.PASS_DECISION,
            "nested_wsta170_decision": wsta175.wsta170.PASS_DECISION,
            "nested_wsta167_decision": wsta175.wsta170.wsta167.PASS_DECISION,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "correct_wsta161_token_supplied": False,
        },
        "forbidden_inputs": [
            "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD",
            "cloudflared",
            "wifi",
            "dhcp",
            "packet-filter-mutation",
        ],
        "executed": False,
        "secret_values_logged": 0,
    }


def validate_fresh_handoff(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    handoff = result.get("expiring_handoff", {})
    return {
        "decision_pass": result.get("decision") == wsta174.PASS_DECISION,
        "fresh_preflight_valid": checks.get("fresh_preflight_valid") is True,
        "expiring_handoff_valid": checks.get("expiring_handoff_valid") is True,
        "handoff_state_ready": handoff.get("handoff_state") == "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "handoff_not_executed": handoff.get("executed") is False,
        "handoff_json_present": bool(handoff.get("handoff_json")),
        "handoff_generated": safety.get("handoff_generated") is True,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def validate_source_gate(result: dict[str, Any], handoff_json: Path) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    return {
        "decision_is_explicit_gate_block": (
            result.get("decision") == "wsta175-blocked-explicit-execution-gate-required"
        ),
        "handoff_path_matches": result.get("handoff_json") == rel(handoff_json),
        "handoff_valid": checks.get("handoff_valid") is True,
        "handoff_fresh": checks.get("handoff_fresh") is True,
        "command_artifacts_valid": checks.get("command_artifacts_valid") is True,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_wsta170_execution": safety.get("wsta170_execute_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def validate_execution_command(payload: dict[str, Any], script_text: str) -> dict[str, bool]:
    command = payload.get("command", [])
    text = " ".join(str(item) for item in command) + script_text
    required = payload.get("required_ack_flags", [])
    expected = payload.get("expected_outcome", {})
    return {
        "schema_ok": payload.get("schema") == "a90-wsta176-wsta175-execute-command-v1",
        "ready_not_executed": payload.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta175": (
            "workspace/public/src/scripts/server-distro/run_wsta175_seccomp_handoff_execute_gate.py" in command
        ),
        "all_ack_flags_present": all(flag in command and flag in script_text for flag in required),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "expected_wsta175_pass": expected.get("decision") == wsta175.PASS_DECISION,
        "expected_wsta170_pass": expected.get("nested_wsta170_decision") == wsta175.wsta170.PASS_DECISION,
        "expected_wsta167_pass": expected.get("nested_wsta167_decision") == wsta175.wsta170.wsta167.PASS_DECISION,
        "expected_no_seccomp_load": expected.get("seccomp_filter_loaded") is False,
        "expected_no_seccomp_enforce": expected.get("seccomp_enforced") is False,
        "expected_no_correct_token": expected.get("correct_wsta161_token_supplied") is False,
        "secret_values_logged_zero": payload.get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta176-seccomp-handoff-execute-preflight-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    wsta168_command_json = resolve_path(args.wsta168_command_json)
    wsta168_command_sh = resolve_path(args.wsta168_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA176 host-only WSTA175 execution preflight",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta168_command_json": rel(wsta168_command_json),
        "wsta168_command_sh": rel(wsta168_command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_preflight_gate": bool(args.emit_wsta175_execute_preflight),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta168_command_json_private": wsta160.is_under(wsta168_command_json, PRIVATE_ROOT),
            "wsta168_command_sh_private": wsta160.is_under(wsta168_command_sh, PRIVATE_ROOT),
            "wsta168_command_json_present": wsta168_command_json.is_file(),
            "wsta168_command_sh_present": wsta168_command_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta176-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_preflight_gate", "wsta176-blocked-explicit-preflight-gate-required"),
        ("wsta168_command_json_private", "wsta176-blocked-wsta168-command-json-nonprivate"),
        ("wsta168_command_sh_private", "wsta176-blocked-wsta168-command-sh-nonprivate"),
        ("wsta168_command_json_present", "wsta176-blocked-wsta168-command-json-missing"),
        ("wsta168_command_sh_present", "wsta176-blocked-wsta168-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    fresh_dir = run_dir / "wsta174-fresh-expiring-handoff"
    source_gate_dir = run_dir / "wsta175-source-gate"
    command = execution_command(run_dir, fresh_dir / "wsta173-expiring-handoff" / wsta174.wsta173.HANDOFF_NAME, args.execution_timeout)
    fresh_result = wsta174.run(
        wsta174_args(
            fresh_dir,
            wsta168_command_json,
            wsta168_command_sh,
            args.readiness_timeout,
            args.execution_timeout,
            int(args.max_age_sec),
        )
    )
    fresh_handoff_json = resolve_path(fresh_result.get("expiring_handoff", {}).get("handoff_json", ""))
    result["fresh_handoff"] = {
        "run_dir": rel(fresh_dir),
        "result_json": rel(fresh_dir / wsta174.SUMMARY_NAME),
        "decision": fresh_result.get("decision"),
        "handoff_json": rel(fresh_handoff_json) if str(fresh_handoff_json) else None,
        "expires_utc": fresh_result.get("expiring_handoff", {}).get("expires_utc"),
    }
    result["fresh_handoff_checks"] = validate_fresh_handoff(fresh_result)
    result["checks"]["fresh_handoff_valid"] = all(result["fresh_handoff_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["fresh_handoff_valid"]:
        result["decision"] = "wsta176-blocked-fresh-handoff-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    command = execution_command(run_dir, fresh_handoff_json, args.execution_timeout)
    source_result = wsta175.run(wsta175_source_gate_args(source_gate_dir, fresh_handoff_json, args.execution_timeout))
    result["source_gate"] = {
        "run_dir": rel(source_gate_dir),
        "result_json": rel(source_gate_dir / wsta175.SUMMARY_NAME),
        "decision": source_result.get("decision"),
    }
    result["source_gate_checks"] = validate_source_gate(source_result, fresh_handoff_json)
    result["checks"]["source_gate_valid"] = all(result["source_gate_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["source_gate_valid"]:
        result["decision"] = "wsta176-blocked-source-gate-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    payload = command_payload(command)
    script_text = "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(REPO_ROOT)) + "\nexec " + " ".join(
        shlex.quote(item) for item in command
    ) + "\n"
    command_checks = validate_execution_command(payload, script_text)
    result["execution_command_checks"] = command_checks
    result["checks"]["execution_command_valid"] = all(command_checks.values())
    result["command"] = {
        "command_json": rel(run_dir / COMMAND_JSON_NAME),
        "command_script": rel(run_dir / COMMAND_SH_NAME),
        "state": payload["state"],
        "executed": False,
        "required_ack_count": len(payload["required_ack_flags"]),
        "expected_decision": payload["expected_outcome"]["decision"],
        "expected_nested_wsta170_decision": payload["expected_outcome"]["nested_wsta170_decision"],
        "expected_nested_wsta167_decision": payload["expected_outcome"]["nested_wsta167_decision"],
        "handoff_json": rel(fresh_handoff_json),
    }
    result["safety"]["handoff_generated"] = True
    result["safety"]["wsta175_execute_command_generated"] = result["checks"]["execution_command_valid"]
    all_ok = (
        result["checks"]["fresh_handoff_valid"]
        and result["checks"]["source_gate_valid"]
        and result["checks"]["execution_command_valid"]
    )
    result["decision"] = PASS_DECISION if all_ok else "wsta176-blocked-execution-command-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    if all_ok:
        write_json(run_dir / COMMAND_JSON_NAME, payload)
        (run_dir / COMMAND_SH_NAME).write_text(script_text, encoding="utf-8")
        (run_dir / COMMAND_SH_NAME).chmod(0o755)
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
    parser.add_argument("--emit-wsta175-execute-preflight", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta176-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
