#!/usr/bin/env python3
"""WSTA193 host-only correct-token canary source proof.

Consumes the WSTA192 risk charter and emits a source-only single-service canary
shape for a later real seccomp-load rung.  The canary references a private
runtime token environment variable, but this unit does not include, supply, or
validate the correct WSTA161 token value.  It does not contact the device or
load/enforce seccomp.
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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta192_seccomp_load_risk_charter as wsta192  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA192_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta192-seccomp-load-risk-charter-20260705T1640KST"
    / wsta192.SUMMARY_NAME
)
PASS_DECISION = "wsta193-seccomp-correct-token-canary-source-pass"
SUMMARY_NAME = "wsta193_result.json"
CONTRACT_NAME = "wsta193_correct_token_canary_contract.json"
SOURCE_NAME = "wsta193_correct_token_canary_source.sh"
PRIVATE_TOKEN_ENV = "A90_PRIVATE_WSTA161_LOAD_TOKEN"
CANARY_SERVICE = "dpublic-hud"
CANARY_COMMAND = "/bin/true"
FORBIDDEN_TOKEN_PREFIX = "WSTA161-" + "EXPLICIT"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
        "host_source_proof_only": True,
        "canary_source_generated": True,
        "canary_source_executed": False,
        "live_command_generated": False,
        "live_command_executed": False,
        "private_token_env_referenced": True,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA193 host-only correct-token canary source proof",
        "default_mode": "host-only-source-proof",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-wsta193-correct-token-canary-source",
        ],
        "private_token_env": PRIVATE_TOKEN_ENV,
        "correct_wsta161_token": "not-supplied",
        "live_execution": "not-generated-by-wsta193",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "contract": result.get("contract", {}),
        "wsta192_checks": result.get("wsta192_checks", {}),
        "source_checks": result.get("source_checks", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_wsta192_result(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    charter = payload.get("charter", {}) if isinstance(payload.get("charter"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    return {
        "decision_pass": payload.get("decision") == wsta192.PASS_DECISION,
        "charter_state_not_executable": charter.get("state") == "READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE",
        "charter_risk_class_real_load": charter.get("risk_class") == "higher-risk-real-seccomp-load",
        "future_rung_count_four": charter.get("future_rung_count") == 4,
        "charter_no_live_command": charter.get("live_command_generated") is False,
        "charter_no_correct_token": charter.get("correct_wsta161_token_supplied") is False,
        "charter_no_seccomp_load": charter.get("seccomp_filter_loaded") is False,
        "charter_no_seccomp_enforce": charter.get("seccomp_enforced") is False,
        "check_guardrail_separate_script": checks.get("charter_guardrail_separate_script") is True,
        "check_future_requires_correct_token_ack": checks.get("charter_future_requires_correct_token_ack") is True,
        "check_wsta190_live_pass": checks.get("wsta190_decision_live_pass") is True,
        "check_wsta164_contract_pass": checks.get("wsta164_decision_pass") is True,
        "safety_host_charter_only": safety.get("host_charter_only") is True,
        "safety_no_live": safety.get("live_command_executed") is False,
        "safety_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "safety_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "safety_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "secret_values_zero": safety.get("secret_values_logged") == 0,
    }


def validate_wsta192_charter(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {"charter_json_present": False}
    charter = load_json(path)
    checks = wsta192.validate_charter(charter)
    serialized = json.dumps(charter, sort_keys=True)
    return {
        "charter_json_present": True,
        "charter_json_private": wsta160.is_under(path, PRIVATE_ROOT),
        "charter_schema_ok": checks.get("schema_ok") is True,
        "charter_state_not_executable": checks.get("state_not_executable") is True,
        "charter_no_load_workflow_closed": checks.get("no_load_workflow_closed") is True,
        "charter_forbids_this_unit_load": checks.get("forbids_load_in_this_unit") is True,
        "charter_future_rungs_present": checks.get("future_rungs_present") is True,
        "charter_token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
    }


def canary_contract(wsta192_result: Path, wsta192_charter: Path, source_path: Path) -> dict[str, Any]:
    return {
        "schema": "a90-wsta193-seccomp-correct-token-canary-source-v1",
        "state": "SOURCE_ONLY_CANARY_NOT_EXECUTABLE",
        "source_wsta192_result": rel(wsta192_result),
        "source_wsta192_charter": rel(wsta192_charter),
        "canary_source_artifact": rel(source_path),
        "canary_service": CANARY_SERVICE,
        "policy_service": "dpublic-hud-intent",
        "canary_command": [CANARY_COMMAND],
        "single_service_canary": True,
        "private_token_env": PRIVATE_TOKEN_ENV,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_load_expected_in_future": True,
        "seccomp_filter_loaded_in_this_unit": False,
        "seccomp_enforced_in_this_unit": False,
        "launcher_env_template": {
            "A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN": "1",
            "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE": "1",
            "A90_SERVICE_LAUNCH_SECCOMP_HELPER_MODE": "apply",
            "A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE": "WSTA163-ALLOW-HELPER-APPLY",
            "A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE": "WSTA164-ALLOW-SECCOMP-LOAD-ENV",
            "A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN": "${" + PRIVATE_TOKEN_ENV + ":?private-token-required}",
        },
        "launcher_command": ["/usr/local/bin/a90-service-launch", CANARY_SERVICE, CANARY_COMMAND],
        "wsta194_operator_packet_requirements": [
            "consume-this-wsta193-source-contract",
            "render-private-default-off-operator-packet",
            "do-not-embed-token-value",
            "require-attended-correct-token-ack",
            "stay-single-service-canary",
        ],
        "future_acknowledgements_required": [
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
        ],
        "stop_conditions": [
            "private token env is absent at future live execution time",
            "canary expands beyond one service",
            "WSTA187 or WSTA190 no-load wrappers are reused",
            "any preflight health check regresses",
            "any generated public artifact contains the token value",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def canary_source(contract: dict[str, Any]) -> str:
    env = contract["launcher_env_template"]
    lines = [
        "#!/bin/sh",
        "# WSTA193 source-only canary fragment. Do not execute directly.",
        "set -eu",
        "",
        "wsta193_seccomp_load_canary_source_only() {",
        "  : \"${" + PRIVATE_TOKEN_ENV + ":?private-token-required}\"",
        "  /usr/bin/env -i \\",
        "    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \\",
    ]
    for key in (
        "A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN",
        "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_MODE",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE",
        "A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE",
    ):
        lines.append(f"    {key}={env[key]} \\")
    lines.extend([
        f"    A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN=\"${{{PRIVATE_TOKEN_ENV}}}\" \\",
        f"    /usr/local/bin/a90-service-launch {CANARY_SERVICE} {CANARY_COMMAND}",
        "}",
        "",
        "echo A90WSTA193_SOURCE_ONLY_CANARY=1",
        "echo A90WSTA193_NOT_EXECUTED=1",
        "exit 65",
        "",
    ])
    return "\n".join(lines)


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(contract, sort_keys=True)
    env = contract.get("launcher_env_template", {})
    return {
        "schema_ok": contract.get("schema") == "a90-wsta193-seccomp-correct-token-canary-source-v1",
        "source_only_state": contract.get("state") == "SOURCE_ONLY_CANARY_NOT_EXECUTABLE",
        "single_service_canary": contract.get("single_service_canary") is True,
        "service_is_hud": contract.get("canary_service") == CANARY_SERVICE,
        "private_token_env_named": contract.get("private_token_env") == PRIVATE_TOKEN_ENV,
        "token_value_not_included": contract.get("token_value_included") is False,
        "correct_token_not_supplied": contract.get("correct_wsta161_token_supplied") is False,
        "future_load_expected": contract.get("seccomp_filter_load_expected_in_future") is True,
        "this_unit_no_load": contract.get("seccomp_filter_loaded_in_this_unit") is False,
        "this_unit_no_enforce": contract.get("seccomp_enforced_in_this_unit") is False,
        "load_gate_present": env.get("A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE") == "WSTA164-ALLOW-SECCOMP-LOAD-ENV",
        "apply_gate_present": env.get("A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE") == "WSTA163-ALLOW-HELPER-APPLY",
        "token_placeholder_only": env.get("A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN") == (
            "${" + PRIVATE_TOKEN_ENV + ":?private-token-required}"
        ),
        "launcher_targets_single_service": contract.get("launcher_command") == [
            "/usr/local/bin/a90-service-launch",
            CANARY_SERVICE,
            CANARY_COMMAND,
        ],
        "wsta194_requirements_present": len(contract.get("wsta194_operator_packet_requirements", [])) == 5,
        "future_ack_correct_token_required": "--allow-correct-wsta161-token" in contract.get(
            "future_acknowledgements_required", []
        ),
        "secret_values_zero": contract.get("secret_values_logged") == 0,
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
    }


def validate_source(script_text: str) -> dict[str, bool]:
    return {
        "has_source_only_marker": "A90WSTA193_SOURCE_ONLY_CANARY=1" in script_text,
        "has_not_executed_marker": "A90WSTA193_NOT_EXECUTED=1" in script_text,
        "has_function_wrapper": "wsta193_seccomp_load_canary_source_only()" in script_text,
        "has_private_token_placeholder": "${" + PRIVATE_TOKEN_ENV + ":?private-token-required}" in script_text,
        "passes_token_env_to_launcher": f'A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN="${{{PRIVATE_TOKEN_ENV}}}"' in script_text,
        "has_apply_gate": "WSTA163-ALLOW-HELPER-APPLY" in script_text,
        "has_load_env_gate": "WSTA164-ALLOW-SECCOMP-LOAD-ENV" in script_text,
        "targets_single_service": f"/usr/local/bin/a90-service-launch {CANARY_SERVICE} {CANARY_COMMAND}" in script_text,
        "source_exits_before_accidental_success": "exit 65" in script_text,
        "does_not_call_wsta187": "run_wsta187" not in script_text and "WSTA187" not in script_text,
        "does_not_call_wsta190": "run_wsta190" not in script_text and "WSTA190" not in script_text,
        "no_external_network_inputs": (
            "cloudflared" not in script_text
            and "tunnel" not in script_text
            and "wifi" not in script_text.lower()
            and "dhcp" not in script_text.lower()
        ),
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in script_text,
    }


def run_shell_syntax(script_path: Path) -> dict[str, Any]:
    completed = subprocess.run(
        ["sh", "-n", str(script_path)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=10.0,
    )
    return {
        "command": ["sh", "-n", rel(script_path)],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "ok": completed.returncode == 0,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_gate", "wsta193-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta193-blocked-nonprivate-run-dir"),
        ("wsta192_result_private", "wsta193-blocked-wsta192-result-nonprivate"),
        ("wsta192_result_present", "wsta193-blocked-wsta192-result-missing"),
        ("wsta192_result_valid", "wsta193-blocked-wsta192-result-invalid"),
        ("wsta192_charter_valid", "wsta193-blocked-wsta192-charter-invalid"),
        ("contract_valid", "wsta193-blocked-contract-invalid"),
        ("source_valid", "wsta193-blocked-source-invalid"),
        ("shell_syntax_ok", "wsta193-blocked-shell-syntax-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta193-seccomp-correct-token-canary-source-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    wsta192_path = resolve_path(args.wsta192_result_json)
    result: dict[str, Any] = {
        "scope": "WSTA193 host-only correct-token canary source proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta192_result_json": rel(wsta192_path),
        "gate_decision": "not-run",
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.prepare_wsta193_correct_token_canary_source),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta192_result_private": wsta160.is_under(wsta192_path, PRIVATE_ROOT),
            "wsta192_result_present": wsta192_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("explicit_gate", "wsta192_result_private", "wsta192_result_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    wsta192_result = load_json(wsta192_path)
    wsta192_checks = validate_wsta192_result(wsta192_result)
    charter_path = resolve_path(wsta192_result.get("charter", {}).get("charter_json", ""))
    wsta192_charter_checks = validate_wsta192_charter(charter_path)
    contract_path = run_dir / CONTRACT_NAME
    source_path = run_dir / SOURCE_NAME
    contract = canary_contract(wsta192_path, charter_path, source_path)
    script_text = canary_source(contract)
    contract_checks = validate_contract(contract)
    source_checks = validate_source(script_text)
    result["wsta192_checks"] = wsta192_checks
    result["wsta192_charter_checks"] = wsta192_charter_checks
    result["contract_checks"] = contract_checks
    result["source_checks"] = source_checks
    result["contract"] = {
        "contract_json": rel(contract_path),
        "source_shell": rel(source_path),
        "state": contract["state"],
        "canary_service": contract["canary_service"],
        "single_service_canary": True,
        "private_token_env": PRIVATE_TOKEN_ENV,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded_in_this_unit": False,
        "seccomp_enforced_in_this_unit": False,
    }
    result["checks"].update({
        "wsta192_result_valid": all(wsta192_checks.values()),
        "wsta192_charter_valid": all(wsta192_charter_checks.values()),
        "contract_valid": all(contract_checks.values()),
        "source_valid": all(source_checks.values()),
    })
    write_json(contract_path, contract)
    write_text(source_path, script_text)
    shell_syntax = run_shell_syntax(source_path)
    result["shell_syntax"] = shell_syntax
    result["checks"]["shell_syntax_ok"] = shell_syntax.get("ok") is True
    result["decision"] = classify(result)
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta192-result-json", type=Path, default=DEFAULT_WSTA192_RESULT)
    parser.add_argument("--prepare-wsta193-correct-token-canary-source", action="store_true")
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
        payload = {"decision": "wsta193-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
