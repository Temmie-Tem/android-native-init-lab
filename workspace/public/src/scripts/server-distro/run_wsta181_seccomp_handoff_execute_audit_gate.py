#!/usr/bin/env python3
"""WSTA181 execution/audit gate for the WSTA180 live handoff bundle.

Consumes a WSTA180 operator handoff bundle.  By default it validates the
handoff, command packet, expected result path, and post-run audit command, then
stops before execution.  Only the full WSTA181 acknowledgement set executes the
WSTA178 command and immediately runs the WSTA179 audit.
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
import run_wsta179_seccomp_one_shot_result_audit as wsta179  # noqa: E402
import run_wsta180_seccomp_live_handoff_bundle as wsta180  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA180_BUNDLE_JSON = (
    DEFAULT_RUN_BASE
    / "wsta180-seccomp-live-handoff-bundle-20260705T145906KST"
    / wsta180.BUNDLE_JSON_NAME
)
DEFAULT_WSTA180_BUNDLE_SH = (
    DEFAULT_RUN_BASE
    / "wsta180-seccomp-live-handoff-bundle-20260705T145906KST"
    / wsta180.BUNDLE_SH_NAME
)
PASS_DECISION = "wsta181-seccomp-handoff-execute-audit-pass"
SUMMARY_NAME = "wsta181_result.json"


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


def explicit_execution_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_wsta181_handoff:
        return False, "wsta181-blocked-explicit-execution-gate-required"
    if not args.allow_wsta178_command_execution:
        return False, "wsta181-blocked-wsta178-command-execution-allow-required"
    if not args.ack_handoff_ready:
        return False, "wsta181-blocked-handoff-ready-ack-required"
    if not args.ack_no_correct_wsta161_token:
        return False, "wsta181-blocked-no-correct-token-ack-required"
    if not args.ack_no_seccomp_load:
        return False, "wsta181-blocked-no-seccomp-load-ack-required"
    if not args.ack_post_run_audit_required:
        return False, "wsta181-blocked-post-run-audit-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta181-blocked-cleanup-ack-required"
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
        "bundle": result.get("bundle", {}),
        "checks": result.get("checks", {}),
        "execution": {
            "returncode": result.get("execution", {}).get("returncode"),
            "audit_returncode": result.get("post_run_audit_execution", {}).get("returncode"),
            "audit_decision": result.get("post_run_audit_result", {}).get("decision"),
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


def validate_handoff_bundle(bundle: dict[str, Any], bundle_json: Path, bundle_sh: Path) -> dict[str, bool]:
    execute_packet = bundle.get("execute_packet", {})
    post_run = bundle.get("post_run_audit", {})
    expected = bundle.get("expected_result", {})
    command_json = resolve_path(execute_packet.get("command_json", ""))
    command_sh = resolve_path(execute_packet.get("command_script", ""))
    result_json = resolve_path(expected.get("wsta177_result_json", ""))
    audit_command = post_run.get("command", [])
    audit_run_dir = command_run_dir(audit_command) if isinstance(audit_command, list) else None
    return {
        "bundle_private": wsta160.is_under(bundle_json, PRIVATE_ROOT),
        "bundle_script_private": wsta160.is_under(bundle_sh, PRIVATE_ROOT),
        "schema_ok": bundle.get("schema") == "a90-wsta180-seccomp-live-handoff-bundle-v1",
        "state_ready": bundle.get("state") == "READY_FOR_OPERATOR_APPROVAL_NOT_EXECUTED",
        "bundle_not_executed": bundle.get("executed") is False,
        "execute_packet_not_executed": execute_packet.get("executed") is False,
        "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
        "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
        "command_json_present": command_json.is_file(),
        "command_sh_present": command_sh.is_file(),
        "expected_result_private": wsta160.is_under(result_json, PRIVATE_ROOT),
        "expected_result_missing": not result_json.exists(),
        "post_run_audit_expected_pass": post_run.get("expected_pass_decision") == wsta179.PASS_DECISION,
        "post_run_audit_command_is_string_list": (
            isinstance(audit_command, list) and all(isinstance(item, str) for item in audit_command)
        ),
        "post_run_audit_run_dir_private": bool(audit_run_dir and wsta160.is_under(audit_run_dir, PRIVATE_ROOT)),
    }


def validate_execution_packet(bundle: dict[str, Any]) -> dict[str, bool]:
    execute_packet = bundle.get("execute_packet", {})
    command_json = resolve_path(execute_packet.get("command_json", ""))
    command_sh = resolve_path(execute_packet.get("command_script", ""))
    payload = load_json(command_json) if command_json.is_file() else {}
    script_text = command_sh.read_text(encoding="utf-8") if command_sh.is_file() else ""
    return wsta179.validate_command_packet(payload, script_text, command_json, command_sh)


def validate_post_run_audit_command(bundle: dict[str, Any], bundle_script_text: str) -> dict[str, bool]:
    post_run = bundle.get("post_run_audit", {})
    command = post_run.get("command", [])
    return wsta180.validate_audit_command(command, bundle_script_text) if isinstance(command, list) else {
        "command_is_string_list": False
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


def validate_post_run_audit_result(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    deep = result.get("wsta177_checks", {})
    return {
        "decision_pass": result.get("decision") == wsta179.PASS_DECISION,
        "command_packet_valid": checks.get("command_packet_valid") is True,
        "wsta177_result_present": checks.get("wsta177_result_present") is True,
        "wsta177_result_valid": checks.get("wsta177_result_valid") is True,
        "deep_source_wsta175_executed": deep.get("source_wsta175_executed") is True,
        "deep_source_wsta170_executed": deep.get("source_wsta170_executed") is True,
        "deep_wsta175_decision_pass": deep.get("wsta175_decision_pass") is True,
        "deep_wsta170_decision_pass": deep.get("wsta170_decision_pass") is True,
        "deep_wsta167_decision_pass": deep.get("wsta167_decision_pass") is True,
        "deep_source_no_seccomp_load": deep.get("source_no_seccomp_load") is True,
        "deep_source_no_seccomp_enforce": deep.get("source_no_seccomp_enforce") is True,
        "deep_source_no_correct_token": deep.get("source_no_correct_token") is True,
        "deep_source_no_flash": deep.get("source_no_flash") is True,
        "deep_source_no_reboot": deep.get("source_no_reboot") is True,
        "deep_source_no_wifi": deep.get("source_no_wifi") is True,
        "deep_source_no_dhcp": deep.get("source_no_dhcp") is True,
        "deep_source_no_public_tunnel": deep.get("source_no_public_tunnel") is True,
        "deep_source_no_packet_filter_mutation": deep.get("source_no_packet_filter_mutation") is True,
        "audit_only": safety.get("audit_only") is True,
        "audit_no_flash": safety.get("boot_flash") is False,
        "audit_no_reboot": safety.get("native_reboot") is False,
        "audit_no_wifi": safety.get("wifi_connect") is False,
        "audit_no_dhcp": safety.get("dhcp") is False,
        "audit_no_public_tunnel": safety.get("public_tunnel") is False,
        "audit_no_packet_filter_mutation": safety.get("packet_filter_mutation") is False,
        "audit_no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "audit_no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "audit_no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def post_run_deep_audit_summary(audit_result: dict[str, Any]) -> dict[str, Any]:
    deep = audit_result.get("wsta177_checks", {})
    keys = (
        "source_wsta175_executed",
        "source_wsta170_executed",
        "wsta175_decision_pass",
        "wsta170_decision_pass",
        "wsta167_decision_pass",
        "source_no_seccomp_load",
        "source_no_seccomp_enforce",
        "source_no_correct_token",
        "source_no_flash",
        "source_no_reboot",
        "source_no_wifi",
        "source_no_dhcp",
        "source_no_public_tunnel",
        "source_no_packet_filter_mutation",
    )
    return {key: deep.get(key) is True for key in keys}


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_execution_gate", "wsta181-blocked-explicit-execution-gate-required"),
        ("handoff_bundle_valid", "wsta181-blocked-handoff-bundle-invalid"),
        ("execution_packet_valid", "wsta181-blocked-execution-packet-invalid"),
        ("post_run_audit_command_valid", "wsta181-blocked-post-run-audit-command-invalid"),
        ("execution_returncode_ok", "wsta181-blocked-execution-returncode"),
        ("post_run_audit_returncode_ok", "wsta181-blocked-post-run-audit-returncode"),
        ("post_run_audit_result_present", "wsta181-blocked-post-run-audit-result-missing"),
        ("post_run_audit_result_valid", "wsta181-blocked-post-run-audit-result-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return decision
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta181-seccomp-handoff-execute-audit-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    bundle_json = resolve_path(args.wsta180_bundle_json)
    bundle_sh = resolve_path(args.wsta180_bundle_sh)
    gate_ok, gate_decision = explicit_execution_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA181 WSTA180 handoff execute-and-audit gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta180_bundle_json": rel(bundle_json),
        "wsta180_bundle_sh": rel(bundle_sh),
        "gate_decision": gate_decision,
        "safety": safety_flags(gate_ok),
        "checks": {
            "explicit_execution_gate": gate_ok,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "bundle_json_private": wsta160.is_under(bundle_json, PRIVATE_ROOT),
            "bundle_sh_private": wsta160.is_under(bundle_sh, PRIVATE_ROOT),
            "bundle_json_present": bundle_json.is_file(),
            "bundle_sh_present": bundle_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta181-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("bundle_json_private", "wsta181-blocked-bundle-json-nonprivate"),
        ("bundle_sh_private", "wsta181-blocked-bundle-sh-nonprivate"),
        ("bundle_json_present", "wsta181-blocked-bundle-json-missing"),
        ("bundle_sh_present", "wsta181-blocked-bundle-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    bundle = load_json(bundle_json)
    bundle_script_text = bundle_sh.read_text(encoding="utf-8")
    result["bundle"] = {
        "state": bundle.get("state"),
        "execute_packet_json": bundle.get("execute_packet", {}).get("command_json"),
        "execute_packet_script": bundle.get("execute_packet", {}).get("command_script"),
        "expected_wsta177_result_json": bundle.get("expected_result", {}).get("wsta177_result_json"),
    }
    result["handoff_bundle_checks"] = validate_handoff_bundle(bundle, bundle_json, bundle_sh)
    result["execution_packet_checks"] = validate_execution_packet(bundle)
    result["post_run_audit_command_checks"] = validate_post_run_audit_command(bundle, bundle_script_text)
    result["checks"]["handoff_bundle_valid"] = all(result["handoff_bundle_checks"].values())
    result["checks"]["execution_packet_valid"] = all(result["execution_packet_checks"].values())
    result["checks"]["post_run_audit_command_valid"] = all(result["post_run_audit_command_checks"].values())
    write_json(out_path, result)
    if (
        not gate_ok
        or not result["checks"]["handoff_bundle_valid"]
        or not result["checks"]["execution_packet_valid"]
        or not result["checks"]["post_run_audit_command_valid"]
    ):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    execute_command = bundle["execute_packet"]["command"]
    post_run_audit_command = bundle["post_run_audit"]["command"]
    audit_run_dir = command_run_dir(post_run_audit_command)
    audit_result_path = audit_run_dir / wsta179.SUMMARY_NAME if audit_run_dir else None
    result["post_run_audit_result_json"] = rel(audit_result_path) if audit_result_path else None
    result["safety"]["device_action"] = "wsta181-wsta178-one-shot-no-load-live-observation"
    result["safety"]["handoff_consumed"] = True
    result["safety"]["wsta178_execute_command_executed"] = True
    result["safety"]["wsta177_execute_command_executed"] = True
    result["safety"]["live_command_executed"] = True
    result["execution"] = run_generated_command(execute_command, timeout=args.execution_timeout)
    result["checks"]["execution_returncode_ok"] = result["execution"].get("returncode") == 0
    result["safety"]["post_run_audit_executed"] = True
    result["post_run_audit_execution"] = run_generated_command(post_run_audit_command, timeout=args.audit_timeout)
    result["checks"]["post_run_audit_returncode_ok"] = (
        result["post_run_audit_execution"].get("returncode") == 0
    )
    result["checks"]["post_run_audit_result_present"] = bool(audit_result_path and audit_result_path.is_file())
    if result["checks"]["post_run_audit_result_present"] and audit_result_path is not None:
        audit_result = load_json(audit_result_path)
        result["post_run_audit_result"] = {
            "decision": audit_result.get("decision"),
            "wsta177_result_json": audit_result.get("wsta177_result_json"),
        }
        result["post_run_deep_audit_checks"] = post_run_deep_audit_summary(audit_result)
        result["safety"]["wsta175_execute_command_executed"] = (
            result["post_run_deep_audit_checks"]["source_wsta175_executed"]
        )
        result["safety"]["wsta170_execute_command_executed"] = (
            result["post_run_deep_audit_checks"]["source_wsta170_executed"]
        )
        result["post_run_audit_checks"] = validate_post_run_audit_result(audit_result)
        result["checks"]["post_run_audit_result_valid"] = all(result["post_run_audit_checks"].values())
    else:
        result["post_run_audit_result"] = {}
        result["post_run_audit_checks"] = {}
        result["post_run_deep_audit_checks"] = {}
        result["checks"]["post_run_audit_result_valid"] = False
    result["decision"] = classify(result)
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
    parser.add_argument("--execute-wsta181-handoff", action="store_true")
    parser.add_argument("--allow-wsta178-command-execution", action="store_true")
    parser.add_argument("--ack-handoff-ready", action="store_true")
    parser.add_argument("--ack-no-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-no-seccomp-load", action="store_true")
    parser.add_argument("--ack-post-run-audit-required", action="store_true")
    parser.add_argument("--ack-cleanup-required", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta181-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
