#!/usr/bin/env python3
"""WSTA180 operator handoff bundle for the no-load live observation.

Packages the WSTA178 execution packet and WSTA179 post-run audit command into a
single operator-facing handoff artifact.  It does not execute WSTA177/WSTA178;
it only proves the command packet is valid and that the expected WSTA177 result
is still absent before handing the execution surface to the operator.
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
import run_wsta179_seccomp_one_shot_result_audit as wsta179  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA178_COMMAND_JSON = wsta179.DEFAULT_WSTA178_COMMAND_JSON
DEFAULT_WSTA178_COMMAND_SH = wsta179.DEFAULT_WSTA178_COMMAND_SH
PASS_DECISION = "wsta180-seccomp-live-handoff-bundle-pass"
SUMMARY_NAME = "wsta180_result.json"
BUNDLE_JSON_NAME = "wsta180_operator_handoff.json"
BUNDLE_SH_NAME = "wsta180_operator_handoff_commands.sh"


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
        "handoff_bundle_generated": False,
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
        "bundle": result.get("bundle", {}),
        "wsta179": result.get("wsta179", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def wsta179_args(run_dir: Path, command_json: Path, command_sh: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta180-wsta179-result-audit",
        run_dir=run_dir,
        wsta178_command_json=command_json,
        wsta178_command_sh=command_sh,
        wsta177_result_json=None,
        audit_wsta177_result=True,
        print_full_json=False,
    )


def audit_command(run_dir: Path, command_json: Path, command_sh: Path, result_json: Path) -> list[str]:
    return [
        "python3",
        "workspace/public/src/scripts/server-distro/run_wsta179_seccomp_one_shot_result_audit.py",
        "--run-id",
        "wsta180-post-run-audit",
        "--run-dir",
        rel(run_dir / "post-run-wsta179-audit"),
        "--wsta178-command-json",
        rel(command_json),
        "--wsta178-command-sh",
        rel(command_sh),
        "--wsta177-result-json",
        rel(result_json),
        "--audit-wsta177-result",
    ]


def validate_audit_command(command: list[str], script_text: str) -> dict[str, bool]:
    text = " ".join(command) + script_text
    return {
        "command_is_string_list": all(isinstance(item, str) for item in command),
        "command_targets_wsta179": (
            "workspace/public/src/scripts/server-distro/run_wsta179_seccomp_one_shot_result_audit.py" in command
        ),
        "audit_gate_present": "--audit-wsta177-result" in command and "--audit-wsta177-result" in script_text,
        "no_execute_wsta177_gate": "--execute-wsta177-one-shot" not in command,
        "no_wsta175_execute_gate": "--execute-wsta175-handoff" not in command,
        "no_wsta170_execute_gate": "--execute-wsta170-no-load-live-observation" not in command,
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
    }


def bundle_payload(
    *,
    command_packet: dict[str, Any],
    command_json: Path,
    command_sh: Path,
    wsta177_result_json: Path,
    wsta179_result_json: Path,
    post_run_audit_command: list[str],
) -> dict[str, Any]:
    return {
        "schema": "a90-wsta180-seccomp-live-handoff-bundle-v1",
        "state": "READY_FOR_OPERATOR_APPROVAL_NOT_EXECUTED",
        "execute_packet": {
            "command_json": rel(command_json),
            "command_script": rel(command_sh),
            "command": command_packet.get("command", []),
            "required_ack_flags": command_packet.get("required_ack_flags", []),
            "expected_outcome": command_packet.get("expected_outcome", {}),
            "executed": command_packet.get("executed"),
        },
        "expected_result": {
            "wsta177_result_json": rel(wsta177_result_json),
            "pre_run_audit_json": rel(wsta179_result_json),
        },
        "post_run_audit": {
            "command": post_run_audit_command,
            "expected_pass_decision": wsta179.PASS_DECISION,
        },
        "safety": {
            "boot_flash": False,
            "native_reboot": False,
            "wifi_connect": False,
            "dhcp": False,
            "public_tunnel": False,
            "packet_filter_mutation": False,
            "seccomp_filter_load_expected": False,
            "seccomp_enforcement_expected": False,
            "correct_wsta161_token_supplied": False,
            "secret_values_logged": 0,
        },
        "executed": False,
        "secret_values_logged": 0,
    }


def validate_bundle(payload: dict[str, Any], script_text: str) -> dict[str, bool]:
    execute_packet = payload.get("execute_packet", {})
    post_run = payload.get("post_run_audit", {})
    command = execute_packet.get("command", [])
    audit = post_run.get("command", [])
    command_text = " ".join(str(item) for item in command)
    audit_text = " ".join(str(item) for item in audit)
    text = command_text + audit_text + script_text
    return {
        "schema_ok": payload.get("schema") == "a90-wsta180-seccomp-live-handoff-bundle-v1",
        "state_ready": payload.get("state") == "READY_FOR_OPERATOR_APPROVAL_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "execute_command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "execute_targets_wsta177": (
            "workspace/public/src/scripts/server-distro/run_wsta177_seccomp_one_shot_execute_gate.py" in command
        ),
        "execute_ack_count_7": len(execute_packet.get("required_ack_flags", [])) == 7,
        "post_audit_command_is_string_list": isinstance(audit, list) and all(isinstance(item, str) for item in audit),
        "post_audit_targets_wsta179": (
            "workspace/public/src/scripts/server-distro/run_wsta179_seccomp_one_shot_result_audit.py" in audit
        ),
        "correct_token_literal_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "secret_values_logged_zero": payload.get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta180-seccomp-live-handoff-bundle-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    command_json = resolve_path(args.wsta178_command_json)
    command_sh = resolve_path(args.wsta178_command_sh)
    result: dict[str, Any] = {
        "scope": "WSTA180 operator handoff bundle for no-load live observation",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta178_command_json": rel(command_json),
        "wsta178_command_sh": rel(command_sh),
        "safety": safety_flags(),
        "checks": {
            "explicit_bundle_gate": bool(args.emit_wsta180_handoff_bundle),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "command_json_private": wsta160.is_under(command_json, PRIVATE_ROOT),
            "command_sh_private": wsta160.is_under(command_sh, PRIVATE_ROOT),
            "command_json_present": command_json.is_file(),
            "command_sh_present": command_sh.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta180-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_bundle_gate", "wsta180-blocked-explicit-bundle-gate-required"),
        ("command_json_private", "wsta180-blocked-command-json-nonprivate"),
        ("command_sh_private", "wsta180-blocked-command-sh-nonprivate"),
        ("command_json_present", "wsta180-blocked-command-json-missing"),
        ("command_sh_present", "wsta180-blocked-command-sh-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    audit_dir = run_dir / "pre-run-wsta179-result-audit"
    audit_result = wsta179.run(wsta179_args(audit_dir, command_json, command_sh))
    result["wsta179"] = {
        "run_dir": rel(audit_dir),
        "result_json": rel(audit_dir / wsta179.SUMMARY_NAME),
        "decision": audit_result.get("decision"),
        "wsta177_result_json": audit_result.get("wsta177_result_json"),
    }
    result["checks"]["pre_run_audit_missing_result"] = (
        audit_result.get("decision") == "wsta179-blocked-wsta177-result-missing"
    )
    result["checks"]["pre_run_command_packet_valid"] = audit_result.get("checks", {}).get("command_packet_valid") is True
    result["checks"]["pre_run_no_live_execution"] = audit_result.get("safety", {}).get("live_command_executed") is False
    write_json(out_path, result)
    if not (
        result["checks"]["pre_run_audit_missing_result"]
        and result["checks"]["pre_run_command_packet_valid"]
        and result["checks"]["pre_run_no_live_execution"]
    ):
        result["decision"] = "wsta180-blocked-pre-run-audit-not-ready"
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    command_packet = load_json(command_json)
    command_script_text = command_sh.read_text(encoding="utf-8")
    command_checks = wsta179.validate_command_packet(command_packet, command_script_text, command_json, command_sh)
    wsta177_result_json = wsta179.inferred_wsta177_result_path(command_packet)
    if wsta177_result_json is None:
        result["decision"] = "wsta180-blocked-wsta177-result-path-missing"
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    post_run_command = audit_command(run_dir, command_json, command_sh, wsta177_result_json)
    audit_script_text = "#!/bin/sh\nset -eu\ncd " + shlex.quote(str(REPO_ROOT)) + "\n" + "\n".join(
        [
            "# Execute the WSTA178 command packet only after explicit operator approval:",
            "printf '%s\\n' " + shlex.quote("EXECUTE: " + rel(command_sh)),
            "# Then run the post-run audit command:",
            "exec " + " ".join(shlex.quote(item) for item in post_run_command),
        ]
    ) + "\n"
    audit_command_checks = validate_audit_command(post_run_command, audit_script_text)
    result["execution_packet_checks"] = command_checks
    result["post_run_audit_command_checks"] = audit_command_checks
    result["checks"]["execution_packet_valid"] = all(command_checks.values())
    result["checks"]["post_run_audit_command_valid"] = all(audit_command_checks.values())
    if not (result["checks"]["execution_packet_valid"] and result["checks"]["post_run_audit_command_valid"]):
        result["decision"] = "wsta180-blocked-handoff-command-invalid"
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    payload = bundle_payload(
        command_packet=command_packet,
        command_json=command_json,
        command_sh=command_sh,
        wsta177_result_json=wsta177_result_json,
        wsta179_result_json=audit_dir / wsta179.SUMMARY_NAME,
        post_run_audit_command=post_run_command,
    )
    bundle_checks = validate_bundle(payload, audit_script_text)
    result["bundle_checks"] = bundle_checks
    result["checks"]["bundle_valid"] = all(bundle_checks.values())
    result["bundle"] = {
        "bundle_json": rel(run_dir / BUNDLE_JSON_NAME),
        "operator_commands_script": rel(run_dir / BUNDLE_SH_NAME),
        "state": payload["state"],
        "execute_packet_json": rel(command_json),
        "execute_packet_script": rel(command_sh),
        "expected_wsta177_result_json": rel(wsta177_result_json),
        "post_run_audit_command_len": len(post_run_command),
    }
    result["safety"]["handoff_bundle_generated"] = result["checks"]["bundle_valid"]
    result["decision"] = PASS_DECISION if result["checks"]["bundle_valid"] else "wsta180-blocked-bundle-invalid"
    result["ended_utc"] = utc_stamp()
    if result["decision"] == PASS_DECISION:
        write_json(run_dir / BUNDLE_JSON_NAME, payload)
        (run_dir / BUNDLE_SH_NAME).write_text(audit_script_text, encoding="utf-8")
        (run_dir / BUNDLE_SH_NAME).chmod(0o755)
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta178-command-json", type=Path, default=DEFAULT_WSTA178_COMMAND_JSON)
    parser.add_argument("--wsta178-command-sh", type=Path, default=DEFAULT_WSTA178_COMMAND_SH)
    parser.add_argument("--emit-wsta180-handoff-bundle", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta180-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
