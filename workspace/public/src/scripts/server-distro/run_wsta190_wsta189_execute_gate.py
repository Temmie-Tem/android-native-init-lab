#!/usr/bin/env python3
"""WSTA190 host-only WSTA189 no-load execute gate.

WSTA189 says whether a WSTA188 WSTA187 no-load operator packet is still
current.  WSTA190 is the last default-off gate before a WSTA187 no-load live
run: it consumes a private READY WSTA189 status, validates the referenced
WSTA188 packet and shell wrapper, and writes an execution gate.

Default execution is host-only preflight.  Optional WSTA187 delegation exists
only behind the explicit WSTA187 no-load acknowledgement stack.  WSTA190 never
loads or enforces seccomp and never supplies the correct WSTA161 token.
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
import run_wsta189_wsta188_operator_packet_status as wsta189  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA189_STATUS_JSON = (
    DEFAULT_RUN_BASE
    / "wsta189-wsta188-operator-packet-status-20260705T161330KST"
    / wsta189.STATUS_JSON_NAME
)
PREFLIGHT_DECISION = "wsta190-wsta189-execute-gate-preflight-pass"
PASS_DECISION = "wsta190-wsta189-execute-gate-live-pass"
SUMMARY_NAME = "wsta190_execute_gate.json"
SUMMARY_MD_NAME = "wsta190_execute_gate.md"


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


def live_requested(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "execute_wsta187_from_status", False))


def safety_flags(args: argparse.Namespace, gate_ok: bool = False) -> dict[str, Any]:
    requested = live_requested(args)
    return {
        "device_action": requested and gate_ok,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "wsta187_live_command_executed": requested and gate_ok,
        "wsta185_execute_command_executed": requested and gate_ok,
        "wsta181_execute_command_executed": requested and gate_ok,
        "post_run_audit_executed": requested and gate_ok,
        "live_command_executed": requested and gate_ok,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA190 host-only WSTA189 no-load execute gate",
        "default_mode": "host-only-preflight",
        "input": "workspace/private/runs/server-distro/<wsta189-run>/wsta189_operator_packet_status.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta189-operator-packet-status-json",
            "workspace/private/runs/server-distro/<wsta189-run>/wsta189_operator_packet_status.json",
        ],
        "optional_no_load_live_execution": [
            "--execute-wsta187-from-status",
            "--allow-wsta185-handoff-execution",
            "--ack-fresh-sequence",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ],
        "live_execution": "not-run-by-default",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "execute_gate": result.get("execute_gate", {}),
        "wsta187_result": result.get("wsta187_result", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_status(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta190-blocked-status-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta189.PASS_DECISION:
        return False, "wsta190-blocked-status-not-pass", {"decision": payload.get("decision")}
    status = payload.get("operator_packet_status")
    if not isinstance(status, dict):
        return False, "wsta190-blocked-status-missing", {}
    if status.get("state") != "READY_TO_RUN_NO_LOAD_DEFAULT_OFF" or status.get("ready_for_no_load_live") is not True:
        return False, "wsta190-blocked-status-not-ready", {
            "state": status.get("state"),
            "ready_for_no_load_live": status.get("ready_for_no_load_live"),
        }
    if status.get("wsta188_recheck_decision") != wsta189.wsta188.PASS_DECISION:
        return False, "wsta190-blocked-wsta188-recheck-not-pass", {
            "wsta188_recheck_decision": status.get("wsta188_recheck_decision"),
        }
    if status.get("wsta188_recheck_source_gate_valid") is not True:
        return False, "wsta190-blocked-wsta188-source-gate-not-valid", {}
    if status.get("packet_match") is not True or status.get("template_match") is not True:
        return False, "wsta190-blocked-status-drift", {
            "packet_match": status.get("packet_match"),
            "template_match": status.get("template_match"),
        }
    if status.get("live_execution_requested") is not False:
        return False, "wsta190-blocked-status-live-execution-requested", {}
    if status.get("public_url_value_logged") is not False:
        return False, "wsta190-blocked-status-public-url-logged", {}
    if status.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta190-blocked-status-secret-values-logged", {}
    packet_path = resolve_path(status.get("wsta188_operator_packet", ""))
    if not wsta160.is_under(packet_path, PRIVATE_ROOT):
        return False, "wsta190-blocked-wsta188-operator-packet-nonprivate", {}
    if not packet_path.is_file():
        return False, "wsta190-blocked-wsta188-operator-packet-missing", {}
    return True, "ok", {"payload": payload, "status": status, "packet_path": packet_path}


def validate_packet(path: Path) -> tuple[bool, str, dict[str, Any]]:
    valid, decision, info = wsta189.validate_packet_payload(path)
    if not valid:
        return False, decision, info
    packet = info["packet"]
    script_path = resolve_path(packet.get("live_command_script", ""))
    checks = dict(info.get("checks", {}))
    checks.update({
        "live_script_private": wsta160.is_under(script_path, PRIVATE_ROOT),
        "live_script_present": script_path.is_file(),
        "live_script_executable": script_path.is_file() and bool(script_path.stat().st_mode & 0o100),
        "operator_ack_stack_matches_wsta188": packet.get("operator_acknowledgements_required") == wsta189.wsta188.ACK_FLAGS,
    })
    if not all(checks.values()):
        return False, "wsta190-blocked-operator-packet-invalid", {
            "packet": packet,
            "checks": checks,
        }
    info["script_path"] = script_path
    info["checks"] = checks
    return True, "ok", info


def gate_from_status(
    status_path: Path,
    status: dict[str, Any],
    packet_path: Path,
    packet: dict[str, Any],
    script_path: Path,
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    return {
        "state": "READY_FOR_EXPLICIT_WSTA187_NO_LOAD_LIVE",
        "wsta189_operator_packet_status": rel(status_path),
        "wsta188_operator_packet": rel(packet_path),
        "wsta188_live_command_script": rel(script_path),
        "wsta188_recheck_decision": status.get("wsta188_recheck_decision"),
        "packet_match": status.get("packet_match"),
        "template_match": status.get("template_match"),
        "source_wsta187_decision": status.get("source_wsta187_decision"),
        "fresh_source_wsta187_decision": status.get("fresh_source_wsta187_decision"),
        "wsta187_live_command_template": packet.get("live_command_template"),
        "operator_acknowledgements_required": packet.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": packet.get("operator_preflight_checks") or [],
        "abort_conditions": packet.get("abort_conditions") or [],
        "cleanup_expectations": packet.get("cleanup_expectations") or [],
        "execution_guardrails": [
            "wsta190-does-not-execute-live-by-default",
            "wsta189-status-must-be-current-ready",
            "wsta188-packet-must-match-fresh-recheck",
            "explicit-wsta187-no-load-gate-required",
            "no-seccomp-load-ack-required",
            "no-correct-wsta161-token-required",
            "final-selftest-required-after-live-run",
        ],
        "recommended_next_action": "operator-may-run-explicit-wsta187-no-load-live-from-wsta190",
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(gate: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in gate.get("wsta187_live_command_template") or [])
    lines = [
        "# WSTA187 No-Load Execute Gate",
        "",
        f"- State: `{gate.get('state')}`",
        f"- WSTA189 status: `{gate.get('wsta189_operator_packet_status')}`",
        f"- WSTA188 packet: `{gate.get('wsta188_operator_packet')}`",
        f"- WSTA188 shell: `{gate.get('wsta188_live_command_script')}`",
        f"- Packet match: `{str(bool(gate.get('packet_match'))).lower()}`",
        f"- Template match: `{str(bool(gate.get('template_match'))).lower()}`",
        "- Live execution requested: `false`",
        "",
        "## Execution Guardrails",
        "",
    ]
    for item in gate.get("execution_guardrails", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## WSTA187 Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "This gate does not run WSTA187 unless the explicit WSTA190 no-load flags are supplied.",
        "",
    ])
    return "\n".join(lines)


def explicit_live_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_wsta187_from_status:
        return False, "wsta190-blocked-execute-wsta187-from-status-required"
    if not args.allow_wsta185_handoff_execution:
        return False, "wsta190-blocked-wsta185-handoff-execution-allow-required"
    if not args.ack_fresh_sequence:
        return False, "wsta190-blocked-fresh-sequence-ack-required"
    if not args.ack_no_correct_wsta161_token:
        return False, "wsta190-blocked-no-correct-token-ack-required"
    if not args.ack_no_seccomp_load:
        return False, "wsta190-blocked-no-seccomp-load-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta190-blocked-cleanup-ack-required"
    return True, "ok"


def run_shell_wrapper(script_path: Path, *, timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        [str(script_path)],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )
    parsed: dict[str, Any] = {}
    if completed.stdout.strip():
        try:
            payload = json.loads(completed.stdout)
            if isinstance(payload, dict):
                parsed = payload
        except json.JSONDecodeError:
            parsed = {}
    return {
        "returncode": completed.returncode,
        "stdout_json": parsed,
        "stderr": completed.stderr,
    }


def validate_wsta187_result(execution: dict[str, Any]) -> dict[str, bool]:
    payload = execution.get("stdout_json") if isinstance(execution.get("stdout_json"), dict) else {}
    checks = payload.get("checks", {}) if isinstance(payload, dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload, dict) else {}
    return {
        "returncode_ok": execution.get("returncode") == 0,
        "decision_pass": payload.get("decision") == wsta189.wsta188.wsta187.PASS_DECISION,
        "wsta185_execution_valid": checks.get("wsta185_execution_valid") is True,
        "no_flash": safety.get("boot_flash") is False,
        "no_reboot": safety.get("native_reboot") is False,
        "no_wifi": safety.get("wifi_connect") is False,
        "no_dhcp": safety.get("dhcp") is False,
        "no_public_tunnel": safety.get("public_tunnel") is False,
        "no_packet_filter_mutation": safety.get("packet_filter_mutation") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
    }


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("status_private", "wsta190-blocked-status-nonprivate"),
        ("status_present", "wsta190-blocked-status-missing"),
        ("status_valid", result.get("status_error") or "wsta190-blocked-status-invalid"),
        ("operator_packet_valid", result.get("operator_packet_error") or "wsta190-blocked-operator-packet-invalid"),
        ("execute_gate_valid", "wsta190-blocked-execute-gate-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    if not checks.get("live_execution_requested"):
        return PREFLIGHT_DECISION
    if not checks.get("explicit_live_gate"):
        return str(result.get("gate_decision") or "wsta190-blocked-explicit-live-gate")
    if not checks.get("wsta187_result_valid"):
        return "wsta190-blocked-wsta187-delegation"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta190-wsta189-execute-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    status_path = resolve_path(args.wsta189_operator_packet_status_json)
    result: dict[str, Any] = {
        "scope": "WSTA190 host-only WSTA189 no-load execute gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta189_operator_packet_status_json": rel(status_path),
        "gate_decision": "not-run",
        "safety": safety_flags(args),
        "checks": {
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "status_private": wsta160.is_under(status_path, PRIVATE_ROOT),
            "status_present": status_path.is_file(),
            "live_execution_requested": live_requested(args),
            "explicit_live_gate": False,
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta190-blocked-nonprivate-run-dir"
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / SUMMARY_NAME
    out_md = run_dir / SUMMARY_MD_NAME
    for key in ("status_private", "status_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_json, result)
            return result

    status_ok, status_decision, status_info = validate_status(status_path)
    result["checks"]["status_valid"] = status_ok
    result["status_error"] = None if status_ok else status_decision
    write_json(out_json, result)
    if not status_ok:
        result["decision"] = classify(result)
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = status_info
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    packet_ok, packet_decision, packet_info = validate_packet(status_info["packet_path"])
    result["operator_packet_checks"] = packet_info.get("checks", {})
    result["checks"]["operator_packet_valid"] = packet_ok
    result["operator_packet_error"] = None if packet_ok else packet_decision
    write_json(out_json, result)
    if not packet_ok:
        result["decision"] = classify(result)
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = packet_info
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    gate = gate_from_status(
        status_path,
        status_info["status"],
        status_info["packet_path"],
        packet_info["packet"],
        packet_info["script_path"],
        out_json,
        out_md,
    )
    result["execute_gate"] = gate
    result["checks"].update({
        "execute_gate_valid": True,
        "wsta189_status_ready": True,
        "wsta188_packet_ready": True,
        "live_execution_requested": live_requested(args),
        "default_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    })
    md_text = markdown(gate)
    if not args.execute_wsta187_from_status:
        result["decision"] = classify(result)
        result["gate_decision"] = "preflight-ready"
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        write_text(out_md, md_text)
        return result

    gate_ok, gate_decision = explicit_live_gate(args)
    result["gate_decision"] = gate_decision
    result["checks"]["explicit_live_gate"] = gate_ok
    result["safety"] = safety_flags(args, gate_ok)
    if not gate_ok:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    execution = run_shell_wrapper(packet_info["script_path"], timeout=args.execution_timeout)
    result["wsta187_execution"] = {
        "returncode": execution.get("returncode"),
        "stderr": execution.get("stderr"),
    }
    result["wsta187_result"] = {
        "decision": execution.get("stdout_json", {}).get("decision"),
        "run_dir": execution.get("stdout_json", {}).get("run_dir"),
        "checks": execution.get("stdout_json", {}).get("checks", {}),
        "safety": execution.get("stdout_json", {}).get("safety", {}),
    }
    result["wsta187_result_checks"] = validate_wsta187_result(execution)
    result["checks"]["wsta187_result_valid"] = all(result["wsta187_result_checks"].values())
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta189-operator-packet-status-json", type=Path, default=DEFAULT_WSTA189_STATUS_JSON)
    parser.add_argument("--execution-timeout", type=float, default=1800.0)
    parser.add_argument("--execute-wsta187-from-status", action="store_true")
    parser.add_argument("--allow-wsta185-handoff-execution", action="store_true")
    parser.add_argument("--ack-fresh-sequence", action="store_true")
    parser.add_argument("--ack-no-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-no-seccomp-load", action="store_true")
    parser.add_argument("--ack-cleanup-required", action="store_true")
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
        payload = {"decision": "wsta190-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
