#!/usr/bin/env python3
"""WSTA201 host-only WSTA200 operator handoff status.

Consumes a private WSTA200 operator handoff packet, validates the default-off
handoff shell wrapper, re-runs WSTA200 from the same WSTA199 status, and reports
whether the handoff remains current for a future attended WSTA198 live canary.
WSTA201 never executes the handoff shell or the WSTA198 live path.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for _path in (SCRIPT_DIR, SCRIPT_DIR.parent / "revalidation"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta161_seccomp_loader_gated_apply_helper as wsta161  # noqa: E402
import run_wsta193_seccomp_correct_token_canary_source as wsta193  # noqa: E402
import run_wsta198_seccomp_load_canary_ssh_adapter as wsta198  # noqa: E402
import run_wsta200_wsta199_operator_handoff as wsta200  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA200_HANDOFF_JSON = (
    DEFAULT_RUN_BASE
    / "wsta200-wsta199-operator-handoff-20260705T174215KST"
    / wsta200.HANDOFF_JSON_NAME
)
PASS_DECISION = "wsta201-wsta200-handoff-status-pass"
SUMMARY_NAME = "wsta201_result.json"
STATUS_JSON_NAME = "wsta201_wsta200_handoff_status.json"
STATUS_MD_NAME = "wsta201_wsta200_handoff_status.md"
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
        "wsta200_recheck_executed": False,
        "wsta200_handoff_shell_executed": False,
        "wsta198_live_command_executed": False,
        "ssh_chroot_transport": False,
        "dropbear_over_ncm": False,
        "fresh_native_health_checked": False,
        "post_run_native_health_checked": False,
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
        "scope": "WSTA201 host-only WSTA200 handoff status",
        "default_mode": "host-only-revalidate-wsta200-handoff",
        "input": "workspace/private/runs/server-distro/<wsta200-run>/wsta200_wsta199_operator_handoff.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta200-handoff-json",
            "workspace/private/runs/server-distro/<wsta200-run>/wsta200_wsta199_operator_handoff.json",
        ],
        "live_execution": "not-run-by-wsta201",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "handoff_status": result.get("handoff_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def private_token_status() -> dict[str, bool]:
    value = os.environ.get(wsta193.PRIVATE_TOKEN_ENV)
    return {
        "private_token_env_present": value is not None,
        "private_token_matches_wsta161": value == wsta161.LOAD_TOKEN,
    }


def no_mutation_safety(safety: dict[str, Any]) -> dict[str, bool]:
    return {
        "device_action_false": safety.get("device_action") is False,
        "boot_flash_false": safety.get("boot_flash") is False,
        "native_reboot_false": safety.get("native_reboot") is False,
        "wifi_connect_false": safety.get("wifi_connect") is False,
        "dhcp_false": safety.get("dhcp") is False,
        "public_tunnel_false": safety.get("public_tunnel") is False,
        "packet_filter_mutation_false": safety.get("packet_filter_mutation") is False,
        "userdata_touch_false": safety.get("userdata_touch") is False,
        "switch_root_false": safety.get("switch_root") is False,
        "live_command_executed_false": safety.get("live_command_executed") is False,
        "correct_token_supplied_false": safety.get("correct_wsta161_token_supplied") is False,
        "seccomp_loaded_false": safety.get("seccomp_filter_loaded") is False,
        "seccomp_enforced_false": safety.get("seccomp_enforced") is False,
        "secret_values_zero": safety.get("secret_values_logged") == 0,
        "public_url_not_logged": safety.get("public_url_value_logged") is False,
    }


def stable_handoff_view(handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": handoff.get("schema"),
        "source_wsta199_status": handoff.get("source_wsta199_status"),
        "wsta198_adapter_json": handoff.get("wsta198_adapter_json"),
        "wsta198_live_command_script": handoff.get("wsta198_live_command_script"),
        "selected_transport": handoff.get("selected_transport"),
        "canary_service": handoff.get("canary_service"),
        "adapter_current": handoff.get("adapter_current"),
        "ready_for_attended_live_handoff": handoff.get("ready_for_attended_live_handoff"),
        "private_token_env": handoff.get("private_token_env"),
        "token_value_included": handoff.get("token_value_included"),
        "correct_wsta161_token_supplied": handoff.get("correct_wsta161_token_supplied"),
        "operator_acknowledgements_required": handoff.get("operator_acknowledgements_required"),
        "operator_preflight_checks": handoff.get("operator_preflight_checks"),
        "abort_conditions": handoff.get("abort_conditions"),
        "cleanup_expectations": handoff.get("cleanup_expectations"),
        "status_stable_view_match": handoff.get("status_stable_view_match"),
        "live_execution_requested": handoff.get("live_execution_requested"),
        "seccomp_filter_loaded": handoff.get("seccomp_filter_loaded"),
        "seccomp_enforced": handoff.get("seccomp_enforced"),
        "public_url_value_logged": handoff.get("public_url_value_logged"),
        "secret_values_logged": handoff.get("secret_values_logged"),
    }


def validate_handoff_payload(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        handoff = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta201-blocked-handoff-unreadable", {"error": str(exc)}
    script_path = resolve_path(handoff.get("handoff_command_script", ""))
    source_status = resolve_path(handoff.get("source_wsta199_status", ""))
    wsta198_script = resolve_path(handoff.get("wsta198_live_command_script", ""))
    script_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    handoff_checks = wsta200.validate_handoff(handoff, script_text)
    serialized = json.dumps(handoff, sort_keys=True) + "\n" + script_text
    checks = {
        "handoff_private": wsta160.is_under(path, PRIVATE_ROOT),
        "schema_ok": handoff.get("schema") == "a90-wsta200-wsta199-operator-handoff-v1",
        "state_ready": handoff.get("state") in (
            "READY_OPERATOR_HANDOFF_WSTA198_ATTENDED_LIVE",
            "READY_OPERATOR_HANDOFF_WSTA198_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "wsta200_handoff_checks_pass": all(handoff_checks.values()),
        "source_status_private": wsta160.is_under(source_status, PRIVATE_ROOT),
        "source_status_present": source_status.is_file(),
        "handoff_script_private": wsta160.is_under(script_path, PRIVATE_ROOT),
        "handoff_script_present": script_path.is_file(),
        "handoff_script_executable": script_path.is_file() and bool(script_path.stat().st_mode & 0o100),
        "wsta198_script_private": wsta160.is_under(wsta198_script, PRIVATE_ROOT),
        "wsta198_script_present": wsta198_script.is_file(),
        "wsta198_script_executable": wsta198_script.is_file() and bool(wsta198_script.stat().st_mode & 0o100),
        "adapter_current": handoff.get("adapter_current") is True,
        "ready_for_attended_live_handoff": handoff.get("ready_for_attended_live_handoff") is True,
        "token_value_not_included": handoff.get("token_value_included") is False,
        "correct_token_not_supplied": handoff.get("correct_wsta161_token_supplied") is False,
        "ack_stack_matches_wsta198": handoff.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "status_stable_view_match": handoff.get("status_stable_view_match") is True,
        "live_not_requested": handoff.get("live_execution_requested") is False,
        "seccomp_not_loaded": handoff.get("seccomp_filter_loaded") is False,
        "seccomp_not_enforced": handoff.get("seccomp_enforced") is False,
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in script_text,
        "script_reruns_wsta199": "run_wsta199_wsta198_adapter_status.py" in script_text,
        "script_execs_wsta198_wrapper": str(handoff.get("wsta198_live_command_script")) in script_text,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": handoff.get("secret_values_logged") == 0,
        "public_url_not_logged": handoff.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta201-blocked-handoff-invalid", {
            "handoff": handoff,
            "handoff_checks": handoff_checks,
            "checks": checks,
        }
    return True, "ok", {
        "handoff": handoff,
        "handoff_checks": handoff_checks,
        "checks": checks,
        "source_status": source_status,
        "script_path": script_path,
        "wsta198_script": wsta198_script,
    }


def wsta200_recheck_args(run_dir: Path, status_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta201-wsta200-recheck",
        run_dir=run_dir,
        wsta199_status_json=status_path,
        prepare_wsta200_operator_handoff=True,
        print_template=False,
        print_full_json=False,
    )


def validate_recheck(recheck: dict[str, Any]) -> dict[str, bool]:
    checks = recheck.get("checks", {}) if isinstance(recheck.get("checks"), dict) else {}
    safety = recheck.get("safety", {}) if isinstance(recheck.get("safety"), dict) else {}
    handoff = recheck.get("operator_handoff", {}) if isinstance(recheck.get("operator_handoff"), dict) else {}
    mutation = no_mutation_safety(safety)
    return {
        "decision_pass": recheck.get("decision") == wsta200.PASS_DECISION,
        "status_valid": checks.get("status_valid") is True,
        "wsta199_recheck_valid": checks.get("wsta199_recheck_valid") is True,
        "status_stable_view_match": checks.get("status_stable_view_match") is True,
        "operator_handoff_valid": checks.get("operator_handoff_valid") is True,
        "handoff_state_ready": handoff.get("state") in (
            "READY_OPERATOR_HANDOFF_WSTA198_ATTENDED_LIVE",
            "READY_OPERATOR_HANDOFF_WSTA198_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "ready_for_attended_live_handoff": handoff.get("ready_for_attended_live_handoff") is True,
        "no_mutation_safety": all(mutation.values()),
    }


def build_status(
    handoff_path: Path,
    old_handoff: dict[str, Any],
    recheck_result: dict[str, Any],
    recheck_path: Path,
    token_checks: dict[str, bool],
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    new_handoff_path = resolve_path(
        recheck_result.get("operator_handoff", {}).get("handoff_json", "")
        if isinstance(recheck_result.get("operator_handoff"), dict)
        else ""
    )
    new_handoff = load_json(new_handoff_path) if new_handoff_path.is_file() else {}
    recheck_pass = recheck_result.get("decision") == wsta200.PASS_DECISION
    handoff_match = bool(
        recheck_pass
        and isinstance(new_handoff, dict)
        and stable_handoff_view(old_handoff) == stable_handoff_view(new_handoff)
    )
    script_match = bool(
        isinstance(new_handoff, dict)
        and old_handoff.get("wsta198_live_command_script") == new_handoff.get("wsta198_live_command_script")
    )
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    current = bool(recheck_pass and handoff_match)
    state = "HANDOFF_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF" if current else "STALE_OR_NOT_READY"
    if current and token_ready:
        state = "HANDOFF_CURRENT_READY_FOR_ATTENDED_LIVE_DEFAULT_OFF"
    elif recheck_pass and not handoff_match:
        state = "DRIFT_RECHECK_REQUIRED"
    return {
        "state": state,
        "handoff_current": current,
        "ready_for_attended_live_handoff": current,
        "ready_for_immediate_live_execute": current and token_ready,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "wsta200_handoff_json": rel(handoff_path),
        "wsta200_recheck_result": rel(recheck_path),
        "wsta200_recheck_decision": recheck_result.get("decision"),
        "handoff_match": handoff_match,
        "script_match": script_match,
        "handoff_command_script": old_handoff.get("handoff_command_script"),
        "wsta198_live_command_script": old_handoff.get("wsta198_live_command_script"),
        "selected_transport": old_handoff.get("selected_transport"),
        "canary_service": old_handoff.get("canary_service"),
        "operator_acknowledgements_required": old_handoff.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": old_handoff.get("operator_preflight_checks") or [],
        "abort_conditions": old_handoff.get("abort_conditions") or [],
        "cleanup_expectations": old_handoff.get("cleanup_expectations") or [],
        "recommended_next_action": (
            "operator-may-run-wsta200-private-handoff-wrapper-after-final-confirmation"
            if current and token_ready
            else "supply-private-token-then-run-wsta200-private-handoff-wrapper"
            if current
            else "rerun-wsta200-before-attended-live"
        ),
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(status: dict[str, Any]) -> str:
    lines = [
        "# WSTA200 Handoff Status",
        "",
        f"- State: `{status.get('state')}`",
        f"- Handoff current: `{str(status.get('handoff_current')).lower()}`",
        f"- Ready for attended handoff: `{str(status.get('ready_for_attended_live_handoff')).lower()}`",
        f"- Ready for immediate live execute: `{str(status.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Handoff match: `{str(status.get('handoff_match')).lower()}`",
        f"- Script match: `{str(status.get('script_match')).lower()}`",
        f"- Token env present: `{str(status.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(status.get('private_token_matches_wsta161')).lower()}`",
        f"- Recommended next action: `{status.get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
        "WSTA201 does not execute the WSTA200 handoff or WSTA198 live canary.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("private_run_dir", "wsta201-blocked-nonprivate-run-dir"),
        ("handoff_private", "wsta201-blocked-handoff-nonprivate"),
        ("handoff_present", "wsta201-blocked-handoff-missing"),
        ("handoff_valid", result.get("handoff_error") or "wsta201-blocked-handoff-invalid"),
        ("wsta200_recheck_valid", "wsta201-blocked-wsta200-recheck-invalid"),
        ("handoff_status_valid", "wsta201-blocked-status-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta201-wsta200-handoff-status-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    handoff_path = resolve_path(args.wsta200_handoff_json)
    result: dict[str, Any] = {
        "scope": "WSTA201 host-only WSTA200 handoff status",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta200_handoff_json": rel(handoff_path),
        "safety": safety_flags(),
        "checks": {
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "handoff_private": wsta160.is_under(handoff_path, PRIVATE_ROOT),
            "handoff_present": handoff_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("handoff_private", "handoff_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    valid, decision, handoff_info = validate_handoff_payload(handoff_path)
    result["handoff_checks"] = handoff_info.get("checks", {})
    result["wsta200_handoff_packet_checks"] = handoff_info.get("handoff_checks", {})
    result["checks"]["handoff_valid"] = valid
    result["handoff_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    recheck_dir = run_dir / "wsta200-recheck"
    recheck_result = wsta200.run(wsta200_recheck_args(recheck_dir, handoff_info["source_status"]))
    result["safety"]["wsta200_recheck_executed"] = True
    result["wsta200_recheck"] = {
        "run_dir": rel(recheck_dir),
        "result_json": rel(recheck_dir / wsta200.SUMMARY_NAME),
        "handoff_json": rel(recheck_dir / wsta200.HANDOFF_JSON_NAME),
        "decision": recheck_result.get("decision"),
    }
    result["wsta200_recheck_checks"] = validate_recheck(recheck_result)
    result["checks"]["wsta200_recheck_valid"] = all(result["wsta200_recheck_checks"].values())
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not result["checks"]["wsta200_recheck_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    status_json = run_dir / STATUS_JSON_NAME
    status_md = run_dir / STATUS_MD_NAME
    status = build_status(
        handoff_path,
        handoff_info["handoff"],
        recheck_result,
        recheck_dir / wsta200.SUMMARY_NAME,
        result["token_checks"],
        status_json,
        status_md,
    )
    result["handoff_status"] = status
    result["checks"]["handoff_status_valid"] = status.get("state") in (
        "HANDOFF_CURRENT_READY_FOR_ATTENDED_LIVE_DEFAULT_OFF",
        "HANDOFF_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF",
        "STALE_OR_NOT_READY",
        "DRIFT_RECHECK_REQUIRED",
    )
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(status_json, result)
    write_text(status_md, markdown(status))
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta200-handoff-json", type=Path, default=DEFAULT_WSTA200_HANDOFF_JSON)
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
        payload = {"decision": "wsta201-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
