#!/usr/bin/env python3
"""WSTA171 host-only preflight for WSTA170 live execution.

Consumes the WSTA170 source-gate proof plus the underlying WSTA169/WSTA168
artifacts, revalidates them, and emits the exact WSTA170 execution command.
This unit does not execute that command.
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
import run_wsta170_seccomp_live_observation_execute as wsta170  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA170_SOURCE_GATE = (
    DEFAULT_RUN_BASE
    / "wsta170-seccomp-live-observation-execute-source-gate-20260705T140000KST"
    / "wsta170_result.json"
)
DEFAULT_WSTA169_READINESS = wsta170.DEFAULT_WSTA169_PROOF
DEFAULT_WSTA168_COMMAND_JSON = wsta170.DEFAULT_WSTA168_COMMAND_JSON
DEFAULT_WSTA168_COMMAND_SH = wsta170.DEFAULT_WSTA168_COMMAND_SH
PASS_DECISION = "wsta171-seccomp-live-observation-execute-preflight-pass"
SUMMARY_NAME = "wsta171_result.json"
COMMAND_JSON_NAME = "wsta171_wsta170_execute_command.json"
COMMAND_SH_NAME = "wsta171_wsta170_execute_command.sh"
EXECUTION_RUN_ID = "wsta171-seccomp-live-observation-execute"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


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
        "wsta170_execute_command_generated": True,
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
        "command": result.get("command", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_wsta170_source_gate(
    source_gate: dict[str, Any],
    source_gate_path: Path,
    readiness_json: Path,
    command_json: Path,
    command_sh: Path,
) -> dict[str, bool]:
    checks = source_gate.get("checks", {})
    safety = source_gate.get("safety", {})
    readiness_checks = source_gate.get("readiness_checks", {})
    command_checks = source_gate.get("command_checks", {})
    return {
        "source_gate_private": wsta160.is_under(source_gate_path, PRIVATE_ROOT),
        "decision_is_explicit_gate_block": (
            source_gate.get("decision") == "wsta170-blocked-explicit-execution-gate-required"
        ),
        "gate_decision_is_explicit_gate_block": (
            source_gate.get("gate_decision") == "wsta170-blocked-explicit-execution-gate-required"
        ),
        "explicit_execution_gate_false": checks.get("explicit_execution_gate") is False,
        "readiness_proof_valid": checks.get("readiness_proof_valid") is True,
        "command_ready": checks.get("command_ready") is True,
        "readiness_checks_true": bool(readiness_checks) and all(value is True for value in readiness_checks.values()),
        "command_checks_true": bool(command_checks) and all(value is True for value in command_checks.values()),
        "wsta169_path_matches": source_gate.get("wsta169_readiness_json") == rel(readiness_json),
        "wsta168_json_path_matches": source_gate.get("wsta168_command_json") == rel(command_json),
        "wsta168_sh_path_matches": source_gate.get("wsta168_command_sh") == rel(command_sh),
        "source_no_device_action": safety.get("device_action") is False,
        "source_no_live_execution": safety.get("live_command_executed") is False,
        "source_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "source_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "source_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def execution_command(
    run_dir: Path,
    readiness_json: Path,
    command_json: Path,
    command_sh: Path,
    timeout: float,
) -> list[str]:
    return [
        "python3",
        "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py",
        "--run-id",
        EXECUTION_RUN_ID,
        "--run-dir",
        rel(run_dir / "wsta170-live-run"),
        "--wsta169-readiness-json",
        rel(readiness_json),
        "--wsta168-command-json",
        rel(command_json),
        "--wsta168-command-sh",
        rel(command_sh),
        "--execution-timeout",
        str(timeout),
        "--execute-wsta170-no-load-live-observation",
        "--allow-wsta168-command-execution",
        "--ack-readiness-proof-current",
        "--ack-no-correct-wsta161-token",
        "--ack-no-seccomp-load",
        "--ack-cleanup-required",
    ]


def command_payload(command: list[str]) -> dict[str, Any]:
    return {
        "schema": "a90-wsta171-wsta170-execute-command-v1",
        "state": "READY_TO_RUN_NOT_EXECUTED",
        "command": command,
        "required_ack_flags": [
            "--execute-wsta170-no-load-live-observation",
            "--allow-wsta168-command-execution",
            "--ack-readiness-proof-current",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ],
        "expected_outcome": {
            "decision": wsta170.PASS_DECISION,
            "nested_decision": wsta170.wsta167.PASS_DECISION,
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


def validate_execution_command(payload: dict[str, Any], script_text: str) -> dict[str, bool]:
    command = payload.get("command", [])
    text = " ".join(str(item) for item in command) + script_text
    required = payload.get("required_ack_flags", [])
    expected = payload.get("expected_outcome", {})
    return {
        "schema_ok": payload.get("schema") == "a90-wsta171-wsta170-execute-command-v1",
        "ready_not_executed": payload.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta170": (
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py" in command
        ),
        "all_ack_flags_present": all(flag in command and flag in script_text for flag in required),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "expected_wsta170_pass": expected.get("decision") == wsta170.PASS_DECISION,
        "expected_wsta167_pass": expected.get("nested_decision") == wsta170.wsta167.PASS_DECISION,
        "expected_no_seccomp_load": expected.get("seccomp_filter_loaded") is False,
        "expected_no_seccomp_enforce": expected.get("seccomp_enforced") is False,
        "expected_no_correct_token": expected.get("correct_wsta161_token_supplied") is False,
        "secret_values_logged_zero": payload.get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta171-seccomp-live-observation-execute-preflight-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    source_gate_path = resolve_path(args.wsta170_source_gate_json)
    readiness_json = resolve_path(args.wsta169_readiness_json)
    wsta168_command_json = resolve_path(args.wsta168_command_json)
    wsta168_command_sh = resolve_path(args.wsta168_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA171 host-only WSTA170 execution preflight",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta170_source_gate_json": rel(source_gate_path),
        "wsta169_readiness_json": rel(readiness_json),
        "wsta168_command_json": rel(wsta168_command_json),
        "wsta168_command_sh": rel(wsta168_command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_preflight_gate": bool(args.emit_wsta170_execute_preflight),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "source_gate_private": wsta160.is_under(source_gate_path, PRIVATE_ROOT),
            "readiness_private": wsta160.is_under(readiness_json, PRIVATE_ROOT),
            "wsta168_command_json_private": wsta160.is_under(wsta168_command_json, PRIVATE_ROOT),
            "wsta168_command_sh_private": wsta160.is_under(wsta168_command_sh, PRIVATE_ROOT),
            "source_gate_present": source_gate_path.is_file(),
            "readiness_present": readiness_json.is_file(),
            "wsta168_command_json_present": wsta168_command_json.is_file(),
            "wsta168_command_sh_present": wsta168_command_sh.is_file(),
        },
    }
    for key, decision in (
        ("explicit_preflight_gate", "wsta171-blocked-explicit-preflight-gate-required"),
        ("private_run_dir", "wsta171-blocked-nonprivate-run-dir"),
        ("source_gate_private", "wsta171-blocked-source-gate-nonprivate"),
        ("readiness_private", "wsta171-blocked-readiness-nonprivate"),
        ("wsta168_command_json_private", "wsta171-blocked-wsta168-command-json-nonprivate"),
        ("wsta168_command_sh_private", "wsta171-blocked-wsta168-command-sh-nonprivate"),
        ("source_gate_present", "wsta171-blocked-source-gate-missing"),
        ("readiness_present", "wsta171-blocked-readiness-missing"),
        ("wsta168_command_json_present", "wsta171-blocked-wsta168-command-json-missing"),
        ("wsta168_command_sh_present", "wsta171-blocked-wsta168-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if key.endswith("_present"):
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    source_gate = load_json(source_gate_path)
    readiness = load_json(readiness_json)
    wsta168_payload = load_json(wsta168_command_json)
    source_checks = validate_wsta170_source_gate(
        source_gate,
        source_gate_path,
        readiness_json,
        wsta168_command_json,
        wsta168_command_sh,
    )
    readiness_checks = wsta170.validate_readiness_proof(readiness, wsta168_command_json, wsta168_command_sh)
    wsta168_checks = wsta170.validate_command_payload(wsta168_payload, wsta168_command_json, wsta168_command_sh)
    command = execution_command(
        run_dir,
        readiness_json,
        wsta168_command_json,
        wsta168_command_sh,
        args.execution_timeout,
    )
    payload = command_payload(command)
    script_text = "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(REPO_ROOT)) + "\nexec " + " ".join(
        shlex.quote(item) for item in command
    ) + "\n"
    execution_command_checks = validate_execution_command(payload, script_text)
    result["source_gate_checks"] = source_checks
    result["readiness_checks"] = readiness_checks
    result["wsta168_command_checks"] = wsta168_checks
    result["execution_command_checks"] = execution_command_checks
    result["checks"].update({
        "source_gate_valid": all(source_checks.values()),
        "readiness_valid": all(readiness_checks.values()),
        "wsta168_command_valid": all(wsta168_checks.values()),
        "execution_command_valid": all(execution_command_checks.values()),
    })
    result["command"] = {
        "command_json": rel(run_dir / COMMAND_JSON_NAME),
        "command_script": rel(run_dir / COMMAND_SH_NAME),
        "state": payload["state"],
        "executed": False,
        "required_ack_count": len(payload["required_ack_flags"]),
        "expected_decision": payload["expected_outcome"]["decision"],
        "expected_nested_decision": payload["expected_outcome"]["nested_decision"],
        "expected_seccomp_filter_loaded": False,
        "expected_seccomp_enforced": False,
    }
    all_ok = all(
        result["checks"][key]
        for key in ("source_gate_valid", "readiness_valid", "wsta168_command_valid", "execution_command_valid")
    )
    result["decision"] = PASS_DECISION if all_ok else "wsta171-blocked-preflight-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / COMMAND_JSON_NAME, payload)
    (run_dir / COMMAND_SH_NAME).write_text(script_text, encoding="utf-8")
    (run_dir / COMMAND_SH_NAME).chmod(0o755)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta170-source-gate-json", type=Path, default=DEFAULT_WSTA170_SOURCE_GATE)
    parser.add_argument("--wsta169-readiness-json", type=Path, default=DEFAULT_WSTA169_READINESS)
    parser.add_argument("--wsta168-command-json", type=Path, default=DEFAULT_WSTA168_COMMAND_JSON)
    parser.add_argument("--wsta168-command-sh", type=Path, default=DEFAULT_WSTA168_COMMAND_SH)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--emit-wsta170-execute-preflight", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta171-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
