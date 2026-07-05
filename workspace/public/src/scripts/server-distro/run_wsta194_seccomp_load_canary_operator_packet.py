#!/usr/bin/env python3
"""WSTA194 private default-off operator packet for the seccomp-load canary.

Consumes the WSTA193 source-only canary contract and renders a private operator
packet for a future attended single-service seccomp-load canary.  This unit
does not execute a live command, does not include or supply the correct
WSTA161 token, and does not load/enforce seccomp.  The generated shell wrapper
fails closed until a later WSTA196 live runner exists.
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
import run_wsta193_seccomp_correct_token_canary_source as wsta193  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA193_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta193-seccomp-correct-token-canary-source-20260705T1642KST"
    / wsta193.SUMMARY_NAME
)
PASS_DECISION = "wsta194-seccomp-load-canary-operator-packet-pass"
SUMMARY_NAME = "wsta194_result.json"
PACKET_JSON_NAME = "wsta194_seccomp_load_canary_operator_packet.json"
PACKET_SH_NAME = "wsta194_seccomp_load_canary_operator_packet.sh"
PACKET_MD_NAME = "wsta194_seccomp_load_canary_operator_packet.md"
FUTURE_WSTA196_RUNNER = "workspace/public/src/scripts/server-distro/run_wsta196_seccomp_load_canary_execute.py"
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
        "host_operator_packet_only": True,
        "operator_packet_generated": True,
        "operator_packet_executed": False,
        "shell_wrapper_generated": True,
        "shell_wrapper_executed": False,
        "live_command_generated": False,
        "live_command_executed": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA194 host-only seccomp-load canary operator packet",
        "default_mode": "host-only-operator-packet",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-wsta194-seccomp-load-canary-operator-packet",
        ],
        "live_execution": "not-generated-by-wsta194",
        "correct_wsta161_token": "not-supplied",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "operator_packet": result.get("operator_packet", {}),
        "wsta193_checks": result.get("wsta193_checks", {}),
        "contract_checks": result.get("contract_checks", {}),
        "packet_checks": result.get("packet_checks", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_wsta193_result(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    contract = payload.get("contract", {}) if isinstance(payload.get("contract"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    return {
        "decision_pass": payload.get("decision") == wsta193.PASS_DECISION,
        "contract_valid": checks.get("contract_valid") is True,
        "source_valid": checks.get("source_valid") is True,
        "shell_syntax_ok": checks.get("shell_syntax_ok") is True,
        "single_service_canary": contract.get("single_service_canary") is True,
        "canary_service_hud": contract.get("canary_service") == wsta193.CANARY_SERVICE,
        "private_token_env_named": contract.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": contract.get("token_value_included") is False,
        "correct_token_not_supplied": contract.get("correct_wsta161_token_supplied") is False,
        "this_unit_no_load": contract.get("seccomp_filter_loaded_in_this_unit") is False,
        "this_unit_no_enforce": contract.get("seccomp_enforced_in_this_unit") is False,
        "safety_no_live": safety.get("live_command_executed") is False,
        "safety_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "safety_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "safety_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "secret_values_zero": safety.get("secret_values_logged") == 0,
    }


def validate_wsta193_contract(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {"contract_json_present": False}
    contract = load_json(path)
    checks = wsta193.validate_contract(contract)
    serialized = json.dumps(contract, sort_keys=True)
    return {
        "contract_json_present": True,
        "contract_json_private": wsta160.is_under(path, PRIVATE_ROOT),
        "schema_ok": checks.get("schema_ok") is True,
        "source_only_state": checks.get("source_only_state") is True,
        "single_service_canary": checks.get("single_service_canary") is True,
        "private_token_env_named": checks.get("private_token_env_named") is True,
        "token_placeholder_only": checks.get("token_placeholder_only") is True,
        "token_value_not_included": checks.get("token_value_not_included") is True,
        "correct_token_not_supplied": checks.get("correct_token_not_supplied") is True,
        "this_unit_no_load": checks.get("this_unit_no_load") is True,
        "this_unit_no_enforce": checks.get("this_unit_no_enforce") is True,
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
    }


def validate_wsta193_source(path: Path) -> dict[str, bool]:
    if not path.is_file():
        return {"source_shell_present": False}
    text = path.read_text(encoding="utf-8")
    checks = wsta193.validate_source(text)
    return {
        "source_shell_present": True,
        "source_shell_private": wsta160.is_under(path, PRIVATE_ROOT),
        "source_only_marker": checks.get("has_source_only_marker") is True,
        "source_not_executed_marker": checks.get("has_not_executed_marker") is True,
        "source_has_private_token_placeholder": checks.get("has_private_token_placeholder") is True,
        "source_targets_single_service": checks.get("targets_single_service") is True,
        "source_exits_65": checks.get("source_exits_before_accidental_success") is True,
        "source_no_wsta187": checks.get("does_not_call_wsta187") is True,
        "source_no_wsta190": checks.get("does_not_call_wsta190") is True,
        "source_token_literal_absent": checks.get("token_literal_absent") is True,
    }


def future_command_template(packet_json: Path) -> list[str]:
    return [
        "python3",
        FUTURE_WSTA196_RUNNER,
        "--run-id",
        "wsta196-seccomp-load-canary-execute-live-<fresh-timestamp>",
        "--wsta194-operator-packet-json",
        rel(packet_json),
        "--execute-real-seccomp-load-canary",
        "--allow-correct-wsta161-token",
        "--ack-seccomp-load-risk",
        "--ack-single-service-canary-only",
        "--ack-no-flash-no-reboot",
        "--ack-cleanup-required",
        "--print-full-json",
    ]


def shell_wrapper() -> str:
    return "\n".join([
        "#!/bin/sh",
        "set -eu",
        "echo A90WSTA194_OPERATOR_PACKET_DEFAULT_OFF=1",
        "echo A90WSTA194_WSTA196_REQUIRED=1",
        "echo a90_wsta194_decision=blocked-wsta196-not-implemented",
        "exit 65",
        "",
    ])


def packet_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# WSTA194 Seccomp-Load Canary Operator Packet",
        "",
        f"- State: `{packet.get('state')}`",
        f"- Canary service: `{packet.get('canary_service')}`",
        f"- Private token env: `{packet.get('private_token_env')}`",
        f"- Shell wrapper: `{packet.get('operator_packet_shell')}`",
        f"- Default off: `{str(packet.get('default_off')).lower()}`",
        f"- Live execution requested: `{str(packet.get('live_execution_requested')).lower()}`",
        "",
        "## Boundary",
        "",
        "- WSTA194 does not execute the canary.",
        "- The generated shell wrapper fails closed until WSTA196 exists.",
        "- The correct WSTA161 token value is not embedded.",
        "- The canary remains single-service only.",
        "",
    ]
    return "\n".join(lines)


def build_packet(run_dir: Path, wsta193_result_path: Path, contract_path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    packet_json = run_dir / PACKET_JSON_NAME
    packet_sh = run_dir / PACKET_SH_NAME
    packet_md = run_dir / PACKET_MD_NAME
    return {
        "schema": "a90-wsta194-seccomp-load-canary-operator-packet-v1",
        "state": "READY_OPERATOR_PACKET_SINGLE_SERVICE_CANARY_DEFAULT_OFF_WSTA196_REQUIRED",
        "default_off": True,
        "ready_for_live_execution": False,
        "ready_for_wsta195_readiness": True,
        "ready_for_wsta196_design": True,
        "source_wsta193_result": rel(wsta193_result_path),
        "source_wsta193_contract": rel(contract_path),
        "source_wsta193_shell": contract.get("canary_source_artifact"),
        "canary_service": contract.get("canary_service"),
        "policy_service": contract.get("policy_service"),
        "canary_command": contract.get("canary_command"),
        "launcher_command": contract.get("launcher_command"),
        "single_service_canary": True,
        "private_token_env": contract.get("private_token_env"),
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "future_live_command_template": future_command_template(packet_json),
        "operator_packet_shell": rel(packet_sh),
        "operator_packet_markdown": rel(packet_md),
        "operator_acknowledgements_required": contract.get("future_acknowledgements_required", []),
        "operator_preflight_checks": [
            "run-WSTA194-immediately-before-WSTA195-readiness",
            "confirm-WSTA193-source-contract-valid",
            "confirm-token-value-remains-private",
            "confirm-single-service-canary-only",
            "confirm-final-selftest-fail-zero-before-and-after-live-run",
        ],
        "abort_conditions": [
            "WSTA193-contract-invalid-or-stale",
            "WSTA196-runner-absent",
            "operator-not-present",
            "private-token-env-absent",
            "canary-expanded-beyond-one-service",
            "unexpected-flash-or-reboot-request",
        ],
        "cleanup_expectations": [
            "no boot image rollback expected",
            "no public tunnel to retire",
            "post-run audit required after any future WSTA196 execution",
        ],
        "safety_boundary": {
            "boot_flash": False,
            "native_reboot": False,
            "wifi_connect": False,
            "dhcp": False,
            "public_tunnel": False,
            "packet_filter_mutation": False,
            "userdata_touch": False,
            "switch_root": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
            "correct_wsta161_token_supplied": False,
        },
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
        "json_path": rel(packet_json),
    }


def validate_packet(packet: dict[str, Any], script_text: str, markdown_text: str) -> dict[str, bool]:
    serialized = json.dumps(packet, sort_keys=True) + "\n" + script_text + "\n" + markdown_text
    command = packet.get("future_live_command_template", [])
    active_surface = json.dumps(command, sort_keys=True) + "\n" + script_text + "\n" + markdown_text
    ack = packet.get("operator_acknowledgements_required", [])
    return {
        "schema_ok": packet.get("schema") == "a90-wsta194-seccomp-load-canary-operator-packet-v1",
        "state_default_off": (
            packet.get("state") == "READY_OPERATOR_PACKET_SINGLE_SERVICE_CANARY_DEFAULT_OFF_WSTA196_REQUIRED"
        ),
        "default_off": packet.get("default_off") is True,
        "not_ready_for_live_execution": packet.get("ready_for_live_execution") is False,
        "ready_for_wsta195": packet.get("ready_for_wsta195_readiness") is True,
        "ready_for_wsta196_design": packet.get("ready_for_wsta196_design") is True,
        "single_service_canary": packet.get("single_service_canary") is True,
        "canary_service_hud": packet.get("canary_service") == wsta193.CANARY_SERVICE,
        "private_token_env_named": packet.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": packet.get("token_value_included") is False,
        "correct_token_not_supplied": packet.get("correct_wsta161_token_supplied") is False,
        "seccomp_not_loaded": packet.get("seccomp_filter_loaded") is False,
        "seccomp_not_enforced": packet.get("seccomp_enforced") is False,
        "future_command_targets_wsta196": FUTURE_WSTA196_RUNNER in command,
        "future_command_has_all_ack_flags": all(flag in command for flag in ack),
        "shell_fails_closed": "a90_wsta194_decision=blocked-wsta196-not-implemented" in script_text
        and "exit 65" in script_text,
        "markdown_default_off": "Default off" in markdown_text,
        "no_wsta187_reuse": "run_wsta187" not in serialized and "WSTA187" not in serialized,
        "no_wsta190_reuse": "run_wsta190" not in serialized and "WSTA190" not in serialized,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_external_network_inputs": (
            "cloudflared" not in active_surface
            and "tunnel" not in active_surface
            and ("ss" + "id=") not in active_surface.lower()
            and ("ps" + "k=") not in active_surface.lower()
            and "dhcp" not in active_surface.lower()
        ),
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "secret_values_zero": packet.get("secret_values_logged") == 0,
        "public_url_not_logged": packet.get("public_url_value_logged") is False,
    }


def shell_syntax(script_path: Path) -> dict[str, Any]:
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
        ("explicit_gate", "wsta194-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta194-blocked-nonprivate-run-dir"),
        ("wsta193_result_private", "wsta194-blocked-wsta193-result-nonprivate"),
        ("wsta193_result_present", "wsta194-blocked-wsta193-result-missing"),
        ("wsta193_result_valid", "wsta194-blocked-wsta193-result-invalid"),
        ("wsta193_contract_valid", "wsta194-blocked-wsta193-contract-invalid"),
        ("wsta193_source_valid", "wsta194-blocked-wsta193-source-invalid"),
        ("operator_packet_valid", "wsta194-blocked-operator-packet-invalid"),
        ("shell_syntax_ok", "wsta194-blocked-shell-syntax-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta194-seccomp-load-canary-operator-packet-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    wsta193_result_path = resolve_path(args.wsta193_result_json)
    result: dict[str, Any] = {
        "scope": "WSTA194 host-only seccomp-load canary operator packet",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta193_result_json": rel(wsta193_result_path),
        "gate_decision": "not-run",
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.prepare_wsta194_seccomp_load_canary_operator_packet),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta193_result_private": wsta160.is_under(wsta193_result_path, PRIVATE_ROOT),
            "wsta193_result_present": wsta193_result_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("explicit_gate", "wsta193_result_private", "wsta193_result_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["gate_decision"] = result["decision"]
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    wsta193_result = load_json(wsta193_result_path)
    contract_path = resolve_path(wsta193_result.get("contract", {}).get("contract_json", ""))
    contract = load_json(contract_path) if contract_path.is_file() else {}
    source_path = resolve_path(contract.get("canary_source_artifact", ""))
    result["wsta193_checks"] = validate_wsta193_result(wsta193_result)
    result["contract_checks"] = validate_wsta193_contract(contract_path)
    result["source_checks"] = validate_wsta193_source(source_path)
    result["checks"].update({
        "wsta193_result_valid": all(result["wsta193_checks"].values()),
        "wsta193_contract_valid": all(result["contract_checks"].values()),
        "wsta193_source_valid": all(result["source_checks"].values()),
    })
    packet = build_packet(run_dir, wsta193_result_path, contract_path, contract)
    packet_json = run_dir / PACKET_JSON_NAME
    packet_sh = run_dir / PACKET_SH_NAME
    packet_md = run_dir / PACKET_MD_NAME
    script_text = shell_wrapper()
    markdown_text = packet_markdown(packet)
    packet_checks = validate_packet(packet, script_text, markdown_text)
    result["packet_checks"] = packet_checks
    result["operator_packet"] = {
        "packet_json": rel(packet_json),
        "packet_shell": rel(packet_sh),
        "packet_markdown": rel(packet_md),
        "state": packet["state"],
        "canary_service": packet["canary_service"],
        "single_service_canary": True,
        "private_token_env": packet["private_token_env"],
        "token_value_included": False,
        "ready_for_live_execution": False,
        "ready_for_wsta195_readiness": True,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
    }
    result["checks"]["operator_packet_valid"] = all(packet_checks.values())
    write_json(packet_json, {"decision": PASS_DECISION, "operator_packet": packet})
    write_text(packet_sh, script_text)
    packet_sh.chmod(0o700)
    write_text(packet_md, markdown_text)
    syntax = shell_syntax(packet_sh)
    result["shell_syntax"] = syntax
    result["checks"]["shell_syntax_ok"] = syntax.get("ok") is True
    result["decision"] = classify(result)
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta193-result-json", type=Path, default=DEFAULT_WSTA193_RESULT)
    parser.add_argument("--prepare-wsta194-seccomp-load-canary-operator-packet", action="store_true")
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
        payload = {"decision": "wsta194-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
