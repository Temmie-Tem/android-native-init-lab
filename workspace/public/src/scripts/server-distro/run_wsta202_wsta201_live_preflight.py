#!/usr/bin/env python3
"""WSTA202 host-only WSTA201 attended-live preflight.

Consumes a private WSTA201 handoff status result, re-runs WSTA201 from the
same WSTA200 handoff, and emits a final default-off preflight status for a
future attended WSTA200/WSTA198 live canary.  WSTA202 never executes the
handoff shell, never runs WSTA198 live, and never supplies the WSTA161 token to
the device.
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
import run_wsta201_wsta200_handoff_status as wsta201  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA201_STATUS_JSON = (
    DEFAULT_RUN_BASE
    / "wsta201-wsta200-handoff-status-20260705T175021KST"
    / wsta201.STATUS_JSON_NAME
)
PASS_DECISION = "wsta202-wsta201-live-preflight-pass"
SUMMARY_NAME = "wsta202_result.json"
PREFLIGHT_JSON_NAME = "wsta202_wsta201_live_preflight.json"
PREFLIGHT_MD_NAME = "wsta202_wsta201_live_preflight.md"
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
        "wsta201_recheck_executed": False,
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
        "scope": "WSTA202 host-only WSTA201 attended-live preflight",
        "default_mode": "host-only-revalidate-wsta201-before-attended-live",
        "input": "workspace/private/runs/server-distro/<wsta201-run>/wsta201_wsta200_handoff_status.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta201-status-json",
            "workspace/private/runs/server-distro/<wsta201-run>/wsta201_wsta200_handoff_status.json",
            "--prepare-wsta202-live-preflight",
        ],
        "live_execution": "not-run-by-wsta202",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "live_preflight": result.get("live_preflight", {}),
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
        "wsta200_handoff_shell_executed_false": safety.get("wsta200_handoff_shell_executed") is False,
        "wsta198_live_command_executed_false": safety.get("wsta198_live_command_executed") is False,
        "live_command_executed_false": safety.get("live_command_executed") is False,
        "correct_token_supplied_false": safety.get("correct_wsta161_token_supplied") is False,
        "seccomp_loaded_false": safety.get("seccomp_filter_loaded") is False,
        "seccomp_enforced_false": safety.get("seccomp_enforced") is False,
        "secret_values_zero": safety.get("secret_values_logged") == 0,
        "public_url_not_logged": safety.get("public_url_value_logged") is False,
    }


def stable_status_view(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "wsta200_handoff_json": status.get("wsta200_handoff_json"),
        "handoff_current": status.get("handoff_current"),
        "ready_for_attended_live_handoff": status.get("ready_for_attended_live_handoff"),
        "handoff_match": status.get("handoff_match"),
        "script_match": status.get("script_match"),
        "handoff_command_script": status.get("handoff_command_script"),
        "wsta198_live_command_script": status.get("wsta198_live_command_script"),
        "selected_transport": status.get("selected_transport"),
        "canary_service": status.get("canary_service"),
        "operator_acknowledgements_required": status.get("operator_acknowledgements_required"),
        "operator_preflight_checks": status.get("operator_preflight_checks"),
        "abort_conditions": status.get("abort_conditions"),
        "cleanup_expectations": status.get("cleanup_expectations"),
        "default_off": status.get("default_off"),
        "live_execution_requested": status.get("live_execution_requested"),
        "public_url_value_logged": status.get("public_url_value_logged"),
        "secret_values_logged": status.get("secret_values_logged"),
    }


def validate_status_payload(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta202-blocked-status-unreadable", {"error": str(exc)}
    status = payload.get("handoff_status")
    if not isinstance(status, dict):
        return False, "wsta202-blocked-status-missing", {"payload_decision": payload.get("decision")}
    handoff_path = resolve_path(status.get("wsta200_handoff_json", ""))
    recheck_path = resolve_path(status.get("wsta200_recheck_result", ""))
    handoff_script = resolve_path(status.get("handoff_command_script", ""))
    wsta198_script = resolve_path(status.get("wsta198_live_command_script", ""))
    handoff_script_text = handoff_script.read_text(encoding="utf-8") if handoff_script.is_file() else ""
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    mutation = no_mutation_safety(safety)
    serialized = json.dumps(payload, sort_keys=True) + "\n" + handoff_script_text
    checks = {
        "status_private": wsta160.is_under(path, PRIVATE_ROOT),
        "decision_pass": payload.get("decision") == wsta201.PASS_DECISION,
        "wsta201_checks_pass": all(
            payload.get("checks", {}).get(key) is True
            for key in ("handoff_valid", "wsta200_recheck_valid", "handoff_status_valid")
        ),
        "status_state_current": status.get("state") in (
            "HANDOFF_CURRENT_READY_FOR_ATTENDED_LIVE_DEFAULT_OFF",
            "HANDOFF_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "handoff_current": status.get("handoff_current") is True,
        "ready_for_attended_live_handoff": status.get("ready_for_attended_live_handoff") is True,
        "handoff_match": status.get("handoff_match") is True,
        "script_match": status.get("script_match") is True,
        "default_off": status.get("default_off") is True,
        "live_not_requested": status.get("live_execution_requested") is False,
        "wsta200_handoff_private": wsta160.is_under(handoff_path, PRIVATE_ROOT),
        "wsta200_handoff_present": handoff_path.is_file(),
        "wsta200_recheck_private": wsta160.is_under(recheck_path, PRIVATE_ROOT),
        "wsta200_recheck_present": recheck_path.is_file(),
        "handoff_script_private": wsta160.is_under(handoff_script, PRIVATE_ROOT),
        "handoff_script_present": handoff_script.is_file(),
        "handoff_script_executable": handoff_script.is_file() and bool(handoff_script.stat().st_mode & 0o100),
        "wsta198_script_private": wsta160.is_under(wsta198_script, PRIVATE_ROOT),
        "wsta198_script_present": wsta198_script.is_file(),
        "wsta198_script_executable": wsta198_script.is_file() and bool(wsta198_script.stat().st_mode & 0o100),
        "ack_stack_matches_wsta198": status.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "no_mutation_safety": all(mutation.values()),
        "handoff_script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in handoff_script_text,
        "handoff_script_reruns_wsta199": "run_wsta199_wsta198_adapter_status.py" in handoff_script_text,
        "handoff_script_execs_wsta198_wrapper": str(status.get("wsta198_live_command_script")) in handoff_script_text,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": status.get("secret_values_logged") == 0,
        "public_url_not_logged": status.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta202-blocked-status-invalid", {
            "payload": payload,
            "status": status,
            "checks": checks,
            "mutation_checks": mutation,
        }
    return True, "ok", {
        "payload": payload,
        "status": status,
        "checks": checks,
        "handoff_path": handoff_path,
        "recheck_path": recheck_path,
        "handoff_script": handoff_script,
        "wsta198_script": wsta198_script,
    }


def wsta201_recheck_args(run_dir: Path, handoff_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta202-wsta201-recheck",
        run_dir=run_dir,
        wsta200_handoff_json=handoff_path,
        print_template=False,
        print_full_json=False,
    )


def validate_recheck(recheck: dict[str, Any]) -> dict[str, bool]:
    checks = recheck.get("checks", {}) if isinstance(recheck.get("checks"), dict) else {}
    safety = recheck.get("safety", {}) if isinstance(recheck.get("safety"), dict) else {}
    status = recheck.get("handoff_status", {}) if isinstance(recheck.get("handoff_status"), dict) else {}
    mutation = no_mutation_safety(safety)
    return {
        "decision_pass": recheck.get("decision") == wsta201.PASS_DECISION,
        "handoff_valid": checks.get("handoff_valid") is True,
        "wsta200_recheck_valid": checks.get("wsta200_recheck_valid") is True,
        "handoff_status_valid": checks.get("handoff_status_valid") is True,
        "handoff_current": status.get("handoff_current") is True,
        "ready_for_attended_live_handoff": status.get("ready_for_attended_live_handoff") is True,
        "handoff_match": status.get("handoff_match") is True,
        "script_match": status.get("script_match") is True,
        "no_mutation_safety": all(mutation.values()),
    }


def build_preflight(
    status_path: Path,
    old_status: dict[str, Any],
    recheck_result: dict[str, Any],
    recheck_path: Path,
    token_checks: dict[str, bool],
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    recheck_status = recheck_result.get("handoff_status", {})
    current = bool(
        recheck_result.get("decision") == wsta201.PASS_DECISION
        and isinstance(recheck_status, dict)
        and stable_status_view(old_status) == stable_status_view(recheck_status)
    )
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    state = "STALE_WSTA201_STATUS_RECHECK_REQUIRED"
    if current and token_ready:
        state = "READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF"
    elif current:
        state = "BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF"
    return {
        "schema": "a90-wsta202-wsta201-live-preflight-v1",
        "state": state,
        "source_wsta201_status": rel(status_path),
        "fresh_wsta201_recheck_result": rel(recheck_path),
        "wsta200_handoff_json": old_status.get("wsta200_handoff_json"),
        "handoff_command_script": old_status.get("handoff_command_script"),
        "wsta198_live_command_script": old_status.get("wsta198_live_command_script"),
        "selected_transport": old_status.get("selected_transport"),
        "canary_service": old_status.get("canary_service"),
        "handoff_current": current,
        "status_stable_view_match": current,
        "ready_for_attended_live_handoff": current,
        "ready_for_immediate_live_execute": current and token_ready,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "operator_acknowledgements_required": old_status.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": [
            "WSTA202-rechecked-WSTA201-from-current-WSTA200-handoff",
            "operator-must-run-private-WSTA200-handoff-wrapper-manually",
            "private-token-env-present-at-wrapper-execution-time",
            *(old_status.get("operator_preflight_checks") or []),
        ],
        "abort_conditions": old_status.get("abort_conditions") or [],
        "cleanup_expectations": old_status.get("cleanup_expectations") or [],
        "recommended_next_action": (
            "operator-may-run-wsta200-private-handoff-wrapper-after-final-human-confirmation"
            if current and token_ready
            else "export-private-token-then-rerun-wsta202-preflight"
            if current
            else "rerun-wsta201-from-current-wsta200-handoff-before-live"
        ),
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_preflight(preflight: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(preflight, sort_keys=True)
    return {
        "schema_ok": preflight.get("schema") == "a90-wsta202-wsta201-live-preflight-v1",
        "state_current": preflight.get("state") in (
            "BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF",
            "READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF",
        ),
        "handoff_current": preflight.get("handoff_current") is True,
        "status_stable_view_match": preflight.get("status_stable_view_match") is True,
        "ready_for_attended_live_handoff": preflight.get("ready_for_attended_live_handoff") is True,
        "token_value_not_included": preflight.get("token_value_included") is False,
        "correct_token_not_supplied": preflight.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": preflight.get("correct_wsta161_token_in_artifact") is False,
        "ack_stack_matches_wsta198": preflight.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "default_off": preflight.get("default_off") is True,
        "live_not_requested": preflight.get("live_execution_requested") is False,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": preflight.get("secret_values_logged") == 0,
        "public_url_not_logged": preflight.get("public_url_value_logged") is False,
    }


def markdown(preflight: dict[str, Any]) -> str:
    lines = [
        "# WSTA201 Live Preflight",
        "",
        f"- State: `{preflight.get('state')}`",
        f"- Handoff current: `{str(preflight.get('handoff_current')).lower()}`",
        f"- Status stable view match: `{str(preflight.get('status_stable_view_match')).lower()}`",
        f"- Ready for attended handoff: `{str(preflight.get('ready_for_attended_live_handoff')).lower()}`",
        f"- Ready for immediate live execute: `{str(preflight.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Token env present: `{str(preflight.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(preflight.get('private_token_matches_wsta161')).lower()}`",
        f"- Recommended next action: `{preflight.get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
        "WSTA202 is a preflight only. It does not execute the WSTA200 handoff or WSTA198 live canary.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_prepare_gate", "wsta202-blocked-explicit-preflight-gate-required"),
        ("private_run_dir", "wsta202-blocked-nonprivate-run-dir"),
        ("status_private", "wsta202-blocked-status-nonprivate"),
        ("status_present", "wsta202-blocked-status-missing"),
        ("status_valid", result.get("status_error") or "wsta202-blocked-status-invalid"),
        ("wsta201_recheck_valid", "wsta202-blocked-wsta201-recheck-invalid"),
        ("status_stable_view_match", "wsta202-blocked-status-drift"),
        ("live_preflight_valid", "wsta202-blocked-live-preflight-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta202-wsta201-live-preflight-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    status_path = resolve_path(args.wsta201_status_json)
    result: dict[str, Any] = {
        "scope": "WSTA202 host-only WSTA201 attended-live preflight",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta201_status_json": rel(status_path),
        "safety": safety_flags(),
        "checks": {
            "explicit_prepare_gate": bool(args.prepare_wsta202_live_preflight),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "status_private": wsta160.is_under(status_path, PRIVATE_ROOT),
            "status_present": status_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("explicit_prepare_gate", "status_private", "status_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    valid, decision, status_info = validate_status_payload(status_path)
    result["status_checks"] = status_info.get("checks", {})
    result["checks"]["status_valid"] = valid
    result["status_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    recheck_dir = run_dir / "wsta201-recheck"
    recheck_result = wsta201.run(wsta201_recheck_args(recheck_dir, status_info["handoff_path"]))
    result["safety"]["wsta201_recheck_executed"] = True
    result["wsta201_recheck"] = {
        "run_dir": rel(recheck_dir),
        "result_json": rel(recheck_dir / wsta201.SUMMARY_NAME),
        "status_json": rel(recheck_dir / wsta201.STATUS_JSON_NAME),
        "decision": recheck_result.get("decision"),
    }
    result["wsta201_recheck_checks"] = validate_recheck(recheck_result)
    result["checks"]["wsta201_recheck_valid"] = all(result["wsta201_recheck_checks"].values())
    result["checks"]["status_stable_view_match"] = bool(
        result["checks"]["wsta201_recheck_valid"]
        and stable_status_view(status_info["status"]) == stable_status_view(recheck_result["handoff_status"])
    )
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not (result["checks"]["wsta201_recheck_valid"] and result["checks"]["status_stable_view_match"]):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    preflight_json = run_dir / PREFLIGHT_JSON_NAME
    preflight_md = run_dir / PREFLIGHT_MD_NAME
    preflight = build_preflight(
        status_path,
        status_info["status"],
        recheck_result,
        recheck_dir / wsta201.SUMMARY_NAME,
        result["token_checks"],
        preflight_json,
        preflight_md,
    )
    result["live_preflight_checks"] = validate_preflight(preflight)
    result["checks"]["live_preflight_valid"] = all(result["live_preflight_checks"].values())
    result["live_preflight"] = preflight
    if result["checks"]["live_preflight_valid"]:
        write_json(preflight_json, result)
        write_text(preflight_md, markdown(preflight))
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta201-status-json", type=Path, default=DEFAULT_WSTA201_STATUS_JSON)
    parser.add_argument("--prepare-wsta202-live-preflight", action="store_true")
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
        payload = {"decision": "wsta202-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
