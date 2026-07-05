#!/usr/bin/env python3
"""WSTA179 host-only audit for a WSTA177 one-shot execution result.

Consumes the WSTA178 command packet and the WSTA177 result it should produce.
This runner never executes the packet; it only verifies command provenance and
the nested WSTA177/WSTA175/WSTA170/WSTA167 pass/safety evidence.
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
import run_wsta177_seccomp_one_shot_execute_gate as wsta177  # noqa: E402
import run_wsta178_seccomp_one_shot_execute_preflight as wsta178  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA178_COMMAND_JSON = (
    DEFAULT_RUN_BASE
    / "wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST"
    / wsta178.COMMAND_JSON_NAME
)
DEFAULT_WSTA178_COMMAND_SH = (
    DEFAULT_RUN_BASE
    / "wsta178-seccomp-one-shot-execute-preflight-20260705T144926KST"
    / wsta178.COMMAND_SH_NAME
)
PASS_DECISION = "wsta179-seccomp-one-shot-result-audit-pass"
SUMMARY_NAME = "wsta179_result.json"


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
        "audit_only": True,
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
        "command": result.get("command", {}),
        "wsta177_result_json": result.get("wsta177_result_json"),
        "checks": result.get("checks", {}),
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


def inferred_wsta177_result_path(command_payload: dict[str, Any]) -> Path | None:
    command = command_payload.get("command", [])
    if not (isinstance(command, list) and all(isinstance(item, str) for item in command)):
        return None
    run_dir = command_run_dir(command)
    return run_dir / wsta177.SUMMARY_NAME if run_dir else None


def validate_command_packet(payload: dict[str, Any], script_text: str, command_json: Path, command_sh: Path) -> dict[str, bool]:
    command = payload.get("command", [])
    inferred = inferred_wsta177_result_path(payload)
    return {
        **wsta178.validate_execution_command(payload, script_text),
        "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
        "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
        "inferred_result_path_private": bool(inferred and wsta160.is_under(inferred, PRIVATE_ROOT)),
        "command_run_dir_private": bool(
            isinstance(command, list)
            and all(isinstance(item, str) for item in command)
            and command_run_dir(command)
            and wsta160.is_under(command_run_dir(command), PRIVATE_ROOT)
        ),
    }


def validate_wsta177_result(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    wsta175_result = result.get("wsta175_result", {})
    wsta175_checks = result.get("wsta175_checks", {})
    wsta170_result = wsta175_result.get("wsta170_result", {}) if isinstance(wsta175_result, dict) else {}
    nested_result = wsta170_result.get("nested_result", {}) if isinstance(wsta170_result, dict) else {}
    wsta175_recheck = wsta177.validate_wsta175_result(wsta175_result) if isinstance(wsta175_result, dict) else {}
    return {
        "decision_pass": result.get("decision") == wsta177.PASS_DECISION,
        "gate_ok": result.get("gate_decision") == "ok",
        "explicit_prepare_gate_true": checks.get("explicit_prepare_gate") is True,
        "explicit_execution_gate_true": checks.get("explicit_execution_gate") is True,
        "fresh_preflight_valid": checks.get("fresh_preflight_valid") is True,
        "execution_command_valid": checks.get("execution_command_valid") is True,
        "execution_returncode_ok": checks.get("execution_returncode_ok") is True,
        "wsta175_result_present": checks.get("wsta175_result_present") is True,
        "wsta175_result_valid": checks.get("wsta175_result_valid") is True,
        "wsta175_decision_pass": wsta175_result.get("decision") == wsta177.wsta175.PASS_DECISION,
        "wsta175_checks_true": bool(wsta175_checks) and all(value is True for value in wsta175_checks.values()),
        "wsta175_recheck_true": bool(wsta175_recheck) and all(value is True for value in wsta175_recheck.values()),
        "wsta170_decision_pass": wsta170_result.get("decision") == wsta177.wsta175.wsta170.PASS_DECISION,
        "wsta167_decision_pass": nested_result.get("decision") == wsta177.wsta175.wsta170.wsta167.PASS_DECISION,
        "source_live_executed": safety.get("live_command_executed") is True,
        "source_wsta175_executed": safety.get("wsta175_execute_command_executed") is True,
        "source_wsta170_executed": safety.get("wsta170_execute_command_executed") is True,
        "source_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "source_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "source_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "source_no_flash": safety.get("boot_flash") is False,
        "source_no_reboot": safety.get("native_reboot") is False,
        "source_no_wifi": safety.get("wifi_connect") is False,
        "source_no_dhcp": safety.get("dhcp") is False,
        "source_no_public_tunnel": safety.get("public_tunnel") is False,
        "source_no_packet_filter_mutation": safety.get("packet_filter_mutation") is False,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_audit_gate", "wsta179-blocked-explicit-audit-gate-required"),
        ("command_packet_valid", "wsta179-blocked-command-packet-invalid"),
        ("wsta177_result_present", "wsta179-blocked-wsta177-result-missing"),
        ("wsta177_result_valid", "wsta179-blocked-wsta177-result-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta179-seccomp-one-shot-result-audit-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    command_json = resolve_path(args.wsta178_command_json)
    command_sh = resolve_path(args.wsta178_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA179 host-only WSTA177 one-shot result audit",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta178_command_json": rel(command_json),
        "wsta178_command_sh": rel(command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_audit_gate": bool(args.audit_wsta177_result),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
            "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
            "command_json_present": command_json.is_file(),
            "command_sh_present": command_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta179-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_audit_gate", "wsta179-blocked-explicit-audit-gate-required"),
        ("command_json_private", "wsta179-blocked-command-json-nonprivate"),
        ("command_sh_private", "wsta179-blocked-command-sh-nonprivate"),
        ("command_json_present", "wsta179-blocked-command-json-missing"),
        ("command_sh_present", "wsta179-blocked-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    command_payload = load_json(command_json)
    script_text = command_sh.read_text(encoding="utf-8")
    command_checks = validate_command_packet(command_payload, script_text, command_json, command_sh)
    inferred_result = inferred_wsta177_result_path(command_payload)
    result["command"] = {
        "state": command_payload.get("state"),
        "executed": command_payload.get("executed"),
        "inferred_wsta177_result_json": rel(inferred_result) if inferred_result else None,
    }
    result["command_checks"] = command_checks
    result["checks"]["command_packet_valid"] = all(command_checks.values())
    write_json(out_path, result)
    if not result["checks"]["command_packet_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta177_result_path = resolve_path(args.wsta177_result_json) if args.wsta177_result_json else inferred_result
    result["wsta177_result_json"] = rel(wsta177_result_path) if wsta177_result_path else None
    result["checks"]["wsta177_result_private"] = bool(
        wsta177_result_path and wsta160.is_under(wsta177_result_path, PRIVATE_ROOT)
    )
    result["checks"]["wsta177_result_present"] = bool(wsta177_result_path and wsta177_result_path.is_file())
    write_json(out_path, result)
    if not result["checks"]["wsta177_result_private"] or not result["checks"]["wsta177_result_present"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta177_result = load_json(wsta177_result_path)
    result["wsta177_result"] = {
        "decision": wsta177_result.get("decision"),
        "gate_decision": wsta177_result.get("gate_decision"),
        "run_dir": wsta177_result.get("run_dir"),
    }
    result["wsta177_checks"] = validate_wsta177_result(wsta177_result)
    result["checks"]["wsta177_result_valid"] = all(result["wsta177_checks"].values())
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta178-command-json", type=Path, default=DEFAULT_WSTA178_COMMAND_JSON)
    parser.add_argument("--wsta178-command-sh", type=Path, default=DEFAULT_WSTA178_COMMAND_SH)
    parser.add_argument("--wsta177-result-json", type=Path)
    parser.add_argument("--audit-wsta177-result", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta179-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
