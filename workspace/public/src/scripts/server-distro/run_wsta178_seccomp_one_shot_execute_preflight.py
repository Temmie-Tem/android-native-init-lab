#!/usr/bin/env python3
"""WSTA178 host-only preflight for WSTA177 one-shot execution.

Consumes the WSTA177 source-gate proof plus the underlying WSTA168 command
artifacts, revalidates them, and emits the exact WSTA177 execution command.
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
import run_wsta177_seccomp_one_shot_execute_gate as wsta177  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA177_SOURCE_GATE = (
    DEFAULT_RUN_BASE
    / "wsta177-seccomp-one-shot-execute-gate-20260705T144329KST"
    / "wsta177_result.json"
)
DEFAULT_WSTA168_COMMAND_JSON = wsta177.DEFAULT_WSTA168_COMMAND_JSON
DEFAULT_WSTA168_COMMAND_SH = wsta177.DEFAULT_WSTA168_COMMAND_SH
PASS_DECISION = "wsta178-seccomp-one-shot-execute-preflight-pass"
SUMMARY_NAME = "wsta178_result.json"
COMMAND_JSON_NAME = "wsta178_wsta177_execute_command.json"
COMMAND_SH_NAME = "wsta178_wsta177_execute_command.sh"
REBASED_WSTA168_COMMAND_JSON_NAME = "wsta178_rebased_wsta168_live_command.json"
REBASED_WSTA168_COMMAND_SH_NAME = "wsta178_rebased_wsta168_live_command.sh"
EXECUTION_RUN_ID = "wsta178-seccomp-one-shot-execute"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
        "wsta177_execute_command_generated": False,
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
        "gate_decision": result.get("gate_decision"),
        "source_gate": result.get("source_gate", {}),
        "command": result.get("command", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_wsta177_source_gate(
    source_gate: dict[str, Any],
    source_gate_path: Path,
    command_json: Path,
    command_sh: Path,
) -> dict[str, bool]:
    checks = source_gate.get("checks", {})
    safety = source_gate.get("safety", {})
    fresh_checks = source_gate.get("fresh_preflight_checks", {})
    command_checks = source_gate.get("execution_command_checks", {})
    return {
        "source_gate_private": wsta160.is_under(source_gate_path, PRIVATE_ROOT),
        "decision_is_explicit_gate_block": (
            source_gate.get("decision") == "wsta177-blocked-explicit-execution-gate-required"
        ),
        "gate_decision_is_explicit_gate_block": (
            source_gate.get("gate_decision") == "wsta177-blocked-explicit-execution-gate-required"
        ),
        "explicit_prepare_gate_true": checks.get("explicit_prepare_gate") is True,
        "explicit_execution_gate_false": checks.get("explicit_execution_gate") is False,
        "fresh_preflight_valid": checks.get("fresh_preflight_valid") is True,
        "execution_command_valid": checks.get("execution_command_valid") is True,
        "fresh_checks_true": bool(fresh_checks) and all(value is True for value in fresh_checks.values()),
        "command_checks_true": bool(command_checks) and all(value is True for value in command_checks.values()),
        "wsta168_json_path_matches": source_gate.get("wsta168_command_json") == rel(command_json),
        "wsta168_sh_path_matches": source_gate.get("wsta168_command_sh") == rel(command_sh),
        "source_no_device_action": safety.get("device_action_requested") is False,
        "source_no_live_execution": safety.get("live_command_executed") is False,
        "source_no_wsta175_execution": safety.get("wsta175_execute_command_executed") is False,
        "source_no_wsta170_execution": safety.get("wsta170_execute_command_executed") is False,
        "source_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "source_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "source_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def execution_command(
    run_dir: Path,
    command_json: Path,
    command_sh: Path,
    readiness_timeout: float,
    execution_timeout: float,
    max_age_sec: int,
) -> list[str]:
    return [
        "python3",
        "workspace/public/src/scripts/server-distro/run_wsta177_seccomp_one_shot_execute_gate.py",
        "--run-id",
        EXECUTION_RUN_ID,
        "--run-dir",
        rel(run_dir / "wsta177-live-run"),
        "--wsta168-command-json",
        rel(command_json),
        "--wsta168-command-sh",
        rel(command_sh),
        "--readiness-timeout",
        str(readiness_timeout),
        "--execution-timeout",
        str(execution_timeout),
        "--max-age-sec",
        str(max_age_sec),
        "--prepare-wsta177-one-shot",
        "--execute-wsta177-one-shot",
        "--allow-wsta175-command-execution",
        "--ack-fresh-preflight",
        "--ack-no-correct-wsta161-token",
        "--ack-no-seccomp-load",
        "--ack-cleanup-required",
    ]


def command_payload(command: list[str]) -> dict[str, Any]:
    return {
        "schema": "a90-wsta178-wsta177-execute-command-v1",
        "state": "READY_TO_RUN_NOT_EXECUTED",
        "command": command,
        "required_ack_flags": [
            "--prepare-wsta177-one-shot",
            "--execute-wsta177-one-shot",
            "--allow-wsta175-command-execution",
            "--ack-fresh-preflight",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ],
        "expected_outcome": {
            "decision": wsta177.PASS_DECISION,
            "nested_wsta175_decision": wsta177.wsta175.PASS_DECISION,
            "nested_wsta170_decision": wsta177.wsta175.wsta170.PASS_DECISION,
            "nested_wsta167_decision": wsta177.wsta175.wsta170.wsta167.PASS_DECISION,
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
        "schema_ok": payload.get("schema") == "a90-wsta178-wsta177-execute-command-v1",
        "ready_not_executed": payload.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta177": (
            "workspace/public/src/scripts/server-distro/run_wsta177_seccomp_one_shot_execute_gate.py" in command
        ),
        "all_ack_flags_present": all(flag in command and flag in script_text for flag in required),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "expected_wsta177_pass": expected.get("decision") == wsta177.PASS_DECISION,
        "expected_wsta175_pass": expected.get("nested_wsta175_decision") == wsta177.wsta175.PASS_DECISION,
        "expected_wsta170_pass": expected.get("nested_wsta170_decision") == wsta177.wsta175.wsta170.PASS_DECISION,
        "expected_wsta167_pass": expected.get("nested_wsta167_decision") == wsta177.wsta175.wsta170.wsta167.PASS_DECISION,
        "expected_no_seccomp_load": expected.get("seccomp_filter_loaded") is False,
        "expected_no_seccomp_enforce": expected.get("seccomp_enforced") is False,
        "expected_no_correct_token": expected.get("correct_wsta161_token_supplied") is False,
        "secret_values_logged_zero": payload.get("secret_values_logged") == 0,
    }


def _replace_arg(command: list[str], flag: str, value: str) -> bool:
    try:
        idx = command.index(flag)
        command[idx + 1] = value
    except (ValueError, IndexError):
        return False
    return True


def rebase_wsta168_payload(payload: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    rebased = json.loads(json.dumps(payload))
    command = rebased.get("command", [])
    if isinstance(command, list) and all(isinstance(item, str) for item in command):
        _replace_arg(command, "--run-id", "wsta178-rebased-wsta167-live-observation")
        _replace_arg(command, "--run-dir", rel(run_dir / "wsta167-live-run"))
    return rebased


def rebased_wsta168_script(payload: dict[str, Any]) -> str:
    command = payload.get("command", [])
    return "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(REPO_ROOT)) + "\nexec " + " ".join(
        shlex.quote(str(item)) for item in command
    ) + "\n"


def validate_rebased_wsta168_payload(payload: dict[str, Any], script_text: str, run_dir: Path) -> dict[str, bool]:
    command = payload.get("command", [])
    text = " ".join(str(item) for item in command) + script_text
    expected_run_dir = rel(run_dir / "wsta167-live-run")
    run_dir_value = None
    run_id_value = None
    if isinstance(command, list):
        try:
            run_dir_value = command[command.index("--run-dir") + 1]
        except (ValueError, IndexError):
            run_dir_value = None
        try:
            run_id_value = command[command.index("--run-id") + 1]
        except (ValueError, IndexError):
            run_id_value = None
    return {
        "schema_ok": payload.get("schema") == "a90-wsta168-seccomp-live-observation-command-v1",
        "ready_not_executed": payload.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "command_targets_wsta167": (
            isinstance(command, list)
            and "workspace/public/src/scripts/server-distro/run_wsta167_seccomp_live_observation.py" in command
        ),
        "rebased_run_id": run_id_value == "wsta178-rebased-wsta167-live-observation",
        "rebased_run_dir": run_dir_value == expected_run_dir,
        "rebased_run_dir_private": wsta160.is_under(resolve_path(Path(expected_run_dir)), PRIVATE_ROOT),
        "all_ack_flags_present": all(flag in command and flag in script_text for flag in payload.get("required_ack_flags", [])),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "secret_values_logged_zero": payload.get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta178-seccomp-one-shot-execute-preflight-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    source_gate_path = resolve_path(args.wsta177_source_gate_json)
    wsta168_command_json = resolve_path(args.wsta168_command_json)
    wsta168_command_sh = resolve_path(args.wsta168_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA178 host-only WSTA177 one-shot execution preflight",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta177_source_gate_json": rel(source_gate_path),
        "wsta168_command_json": rel(wsta168_command_json),
        "wsta168_command_sh": rel(wsta168_command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_preflight_gate": bool(args.emit_wsta177_execute_preflight),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "source_gate_private": wsta160.is_under(source_gate_path, PRIVATE_ROOT),
            "wsta168_command_json_private": wsta160.is_under(wsta168_command_json, PRIVATE_ROOT),
            "wsta168_command_sh_private": wsta160.is_under(wsta168_command_sh, PRIVATE_ROOT),
            "source_gate_present": source_gate_path.is_file(),
            "wsta168_command_json_present": wsta168_command_json.is_file(),
            "wsta168_command_sh_present": wsta168_command_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta178-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_preflight_gate", "wsta178-blocked-explicit-preflight-gate-required"),
        ("source_gate_private", "wsta178-blocked-source-gate-nonprivate"),
        ("wsta168_command_json_private", "wsta178-blocked-wsta168-command-json-nonprivate"),
        ("wsta168_command_sh_private", "wsta178-blocked-wsta168-command-sh-nonprivate"),
        ("source_gate_present", "wsta178-blocked-source-gate-missing"),
        ("wsta168_command_json_present", "wsta178-blocked-wsta168-command-json-missing"),
        ("wsta168_command_sh_present", "wsta178-blocked-wsta168-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    source_gate = load_json(source_gate_path)
    result["source_gate"] = {
        "result_json": rel(source_gate_path),
        "decision": source_gate.get("decision"),
        "fresh_preflight": source_gate.get("fresh_preflight", {}),
    }
    result["source_gate_checks"] = validate_wsta177_source_gate(
        source_gate,
        source_gate_path,
        wsta168_command_json,
        wsta168_command_sh,
    )
    result["checks"]["source_gate_valid"] = all(result["source_gate_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["source_gate_valid"]:
        result["decision"] = "wsta178-blocked-source-gate-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    original_wsta168_payload = load_json(wsta168_command_json)
    rebased_payload = rebase_wsta168_payload(original_wsta168_payload, run_dir / "rebased-wsta168-command")
    rebased_script_text = rebased_wsta168_script(rebased_payload)
    rebased_command_json = run_dir / REBASED_WSTA168_COMMAND_JSON_NAME
    rebased_command_sh = run_dir / REBASED_WSTA168_COMMAND_SH_NAME
    result["rebased_wsta168_command_checks"] = validate_rebased_wsta168_payload(
        rebased_payload,
        rebased_script_text,
        run_dir / "rebased-wsta168-command",
    )
    result["checks"]["rebased_wsta168_command_valid"] = all(result["rebased_wsta168_command_checks"].values())
    result["rebased_wsta168_command"] = {
        "command_json": rel(rebased_command_json),
        "command_script": rel(rebased_command_sh),
        "wsta167_run_dir": rel(run_dir / "rebased-wsta168-command" / "wsta167-live-run"),
    }
    write_json(out_path, result)
    if not result["checks"]["rebased_wsta168_command_valid"]:
        result["decision"] = "wsta178-blocked-rebased-wsta168-command-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    command = execution_command(
        run_dir,
        rebased_command_json,
        rebased_command_sh,
        args.readiness_timeout,
        args.execution_timeout,
        int(args.max_age_sec),
    )
    payload = command_payload(command)
    script_text = "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(REPO_ROOT)) + "\nexec " + " ".join(
        shlex.quote(item) for item in command
    ) + "\n"
    result["execution_command_checks"] = validate_execution_command(payload, script_text)
    result["checks"]["execution_command_valid"] = all(result["execution_command_checks"].values())
    result["command"] = {
        "command_json": rel(run_dir / COMMAND_JSON_NAME),
        "command_script": rel(run_dir / COMMAND_SH_NAME),
        "rebased_wsta168_command_json": rel(rebased_command_json),
        "rebased_wsta168_command_script": rel(rebased_command_sh),
        "state": payload["state"],
        "executed": False,
        "required_ack_count": len(payload["required_ack_flags"]),
        "expected_decision": payload["expected_outcome"]["decision"],
        "expected_nested_wsta175_decision": payload["expected_outcome"]["nested_wsta175_decision"],
        "expected_nested_wsta170_decision": payload["expected_outcome"]["nested_wsta170_decision"],
        "expected_nested_wsta167_decision": payload["expected_outcome"]["nested_wsta167_decision"],
    }
    result["safety"]["wsta177_execute_command_generated"] = result["checks"]["execution_command_valid"]
    all_ok = (
        result["checks"]["source_gate_valid"]
        and result["checks"]["rebased_wsta168_command_valid"]
        and result["checks"]["execution_command_valid"]
    )
    result["decision"] = PASS_DECISION if all_ok else "wsta178-blocked-execution-command-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    if all_ok:
        write_json(rebased_command_json, rebased_payload)
        rebased_command_sh.write_text(rebased_script_text, encoding="utf-8")
        rebased_command_sh.chmod(0o755)
        write_json(run_dir / COMMAND_JSON_NAME, payload)
        (run_dir / COMMAND_SH_NAME).write_text(script_text, encoding="utf-8")
        (run_dir / COMMAND_SH_NAME).chmod(0o755)
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta177-source-gate-json", type=Path, default=DEFAULT_WSTA177_SOURCE_GATE)
    parser.add_argument("--wsta168-command-json", type=Path, default=DEFAULT_WSTA168_COMMAND_JSON)
    parser.add_argument("--wsta168-command-sh", type=Path, default=DEFAULT_WSTA168_COMMAND_SH)
    parser.add_argument("--readiness-timeout", type=float, default=20.0)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--max-age-sec", type=int, default=900)
    parser.add_argument("--emit-wsta177-execute-preflight", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta178-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
