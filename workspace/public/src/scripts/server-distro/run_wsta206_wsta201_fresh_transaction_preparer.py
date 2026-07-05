#!/usr/bin/env python3
"""WSTA206 host-only fresh WSTA205 transaction preparer.

Consumes a private WSTA201 status, replays WSTA202 -> WSTA203 -> WSTA204 ->
WSTA205 in host-only/default-off mode, and emits a private prepare script that
can later regenerate a fresh WSTA205 transaction bundle after the operator
deliberately supplies the private token.  WSTA206 never executes the generated
WSTA205 transaction script.
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
import run_wsta202_wsta201_live_preflight as wsta202  # noqa: E402
import run_wsta203_wsta202_wrapper_manifest_audit as wsta203  # noqa: E402
import run_wsta204_wsta203_live_result_verifier as wsta204  # noqa: E402
import run_wsta205_wsta204_live_transaction_bundle as wsta205  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA201_STATUS_JSON = wsta202.DEFAULT_WSTA201_STATUS_JSON
PASS_DECISION = "wsta206-wsta201-fresh-transaction-preparer-pass"
SUMMARY_NAME = "wsta206_result.json"
PREPARER_JSON_NAME = "wsta206_fresh_transaction_preparer.json"
PREPARER_SH_NAME = "wsta206_prepare_fresh_transaction.sh"
PREPARER_MD_NAME = "wsta206_fresh_transaction_preparer.md"
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
        "wsta202_replay_executed": False,
        "wsta203_replay_executed": False,
        "wsta204_replay_executed": False,
        "wsta205_replay_executed": False,
        "wsta206_prepare_script_generated": False,
        "wsta206_prepare_script_executed": False,
        "wsta205_transaction_script_executed": False,
        "wsta200_handoff_shell_executed": False,
        "wsta198_live_command_executed": False,
        "wsta204_verify_mode_executed": False,
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
        "scope": "WSTA206 host-only fresh WSTA205 transaction preparer",
        "default_mode": "replay-wsta202-through-wsta205-and-emit-fresh-preparer",
        "input": "workspace/private/runs/server-distro/<wsta201-run>/wsta201_wsta200_handoff_status.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta201-status-json",
            "workspace/private/runs/server-distro/<wsta201-run>/wsta201_wsta200_handoff_status.json",
            "--emit-wsta206-fresh-transaction-preparer",
        ],
        "live_execution": "not-run-by-wsta206",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "fresh_transaction_preparer": result.get("fresh_transaction_preparer", {}),
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


def validate_wsta201_status(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta206-blocked-wsta201-status-unreadable", {"error": str(exc)}
    status = payload.get("handoff_status")
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    mutation = no_mutation_safety(safety)
    checks = {
        "status_private": wsta160.is_under(path, PRIVATE_ROOT),
        "decision_pass": payload.get("decision") == wsta202.wsta201.PASS_DECISION,
        "status_present": isinstance(status, dict),
        "status_current": isinstance(status, dict) and status.get("handoff_current") is True,
        "ready_for_attended_live_handoff": isinstance(status, dict) and status.get("ready_for_attended_live_handoff") is True,
        "handoff_match": isinstance(status, dict) and status.get("handoff_match") is True,
        "script_match": isinstance(status, dict) and status.get("script_match") is True,
        "default_off": isinstance(status, dict) and status.get("default_off") is True,
        "live_not_requested": isinstance(status, dict) and status.get("live_execution_requested") is False,
        "ack_stack_matches_wsta198": isinstance(status, dict) and status.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "no_mutation_safety": all(mutation.values()),
        "secret_values_zero": isinstance(status, dict) and status.get("secret_values_logged") == 0,
        "public_url_not_logged": isinstance(status, dict) and status.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta206-blocked-wsta201-status-invalid", {
            "payload": payload,
            "checks": checks,
            "mutation_checks": mutation,
        }
    return True, "ok", {
        "payload": payload,
        "status": status,
        "checks": checks,
    }


def replay_args_wsta202(run_dir: Path, status_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta206-replay-wsta202",
        run_dir=run_dir,
        wsta201_status_json=status_path,
        prepare_wsta202_live_preflight=True,
        print_template=False,
        print_full_json=False,
    )


def replay_args_wsta203(run_dir: Path, preflight_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta206-replay-wsta203",
        run_dir=run_dir,
        wsta202_preflight_json=preflight_path,
        audit_wsta203_wrapper_manifest=True,
        print_template=False,
        print_full_json=False,
    )


def replay_args_wsta204(run_dir: Path, audit_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta206-replay-wsta204",
        run_dir=run_dir,
        source_wsta203_audit_json=audit_path,
        wsta198_live_result_json=None,
        emit_wsta204_live_result_verifier=True,
        verify_wsta204_live_result=False,
        print_template=False,
        print_full_json=False,
    )


def replay_args_wsta205(run_dir: Path, verifier_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta206-replay-wsta205",
        run_dir=run_dir,
        source_wsta204_verifier_json=verifier_path,
        emit_wsta205_live_transaction_bundle=True,
        print_template=False,
        print_full_json=False,
    )


def validate_replay(result: dict[str, Any], pass_decision: str, valid_keys: list[str], safety: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {}) if isinstance(result.get("checks"), dict) else {}
    return {
        "decision_pass": result.get("decision") == pass_decision,
        **{f"{key}_true": checks.get(key) is True for key in valid_keys},
        "no_mutation_safety": all(no_mutation_safety(safety).values()),
    }


def preparer_script(status_path: Path) -> str:
    return "\n".join([
        "#!/bin/sh",
        "set -eu",
        f"cd '{REPO_ROOT}'",
        "ts=$(date +%Y%m%dT%H%M%SKST)",
        'export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/a90_pycache}"',
        f': "${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}"',
        'SELF_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)',
        'OUT="${SELF_DIR}/wsta206_fresh_prepare_${ts}.json"',
        "python3 workspace/public/src/scripts/server-distro/run_wsta206_wsta201_fresh_transaction_preparer.py \\",
        f"  --wsta201-status-json '{rel(status_path)}' \\",
        "  --emit-wsta206-fresh-transaction-preparer \\",
        '  --run-id "wsta206-fresh-transaction-preparer-${ts}" \\',
        '  --print-full-json > "$OUT"',
        "python3 - \"$OUT\" <<'PY'",
        "import json, sys",
        "payload = json.load(open(sys.argv[1], 'r', encoding='utf-8'))",
        "prep = payload.get('fresh_transaction_preparer') or {}",
        "assert payload.get('decision') == 'wsta206-wsta201-fresh-transaction-preparer-pass', payload.get('decision')",
        "assert prep.get('ready_for_immediate_live_execute') is True, prep",
        "assert prep.get('private_token_env_present') is True, prep",
        "assert prep.get('private_token_matches_wsta161') is True, prep",
        "assert payload.get('safety', {}).get('live_command_executed') is False, payload.get('safety')",
        "print(prep.get('fresh_wsta205_transaction_script'))",
        "PY",
        "",
    ])


def build_preparer(
    status_path: Path,
    wsta202_result: dict[str, Any],
    wsta203_result: dict[str, Any],
    wsta204_result: dict[str, Any],
    wsta205_result: dict[str, Any],
    token_checks: dict[str, bool],
    out_json: Path,
    out_sh: Path,
    out_md: Path,
) -> dict[str, Any]:
    wsta205_bundle = wsta205_result.get("live_transaction_bundle", {})
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    current = bool(
        wsta202_result.get("decision") == wsta202.PASS_DECISION
        and wsta203_result.get("decision") == wsta203.PASS_DECISION
        and wsta204_result.get("decision") == wsta204.SOURCE_PASS_DECISION
        and wsta205_result.get("decision") == wsta205.PASS_DECISION
        and isinstance(wsta205_bundle, dict)
        and wsta205_bundle.get("ready_for_transaction_execution") is True
    )
    state = "FRESH_TRANSACTION_PREPARER_NOT_CURRENT"
    if current and token_ready:
        state = "FRESH_TRANSACTION_PREPARER_READY_TOKEN_READY_DEFAULT_OFF"
    elif current:
        state = "FRESH_TRANSACTION_PREPARER_READY_TOKEN_REQUIRED_DEFAULT_OFF"
    return {
        "schema": "a90-wsta206-wsta201-fresh-transaction-preparer-v1",
        "state": state,
        "source_wsta201_status": rel(status_path),
        "fresh_wsta202_preflight_json": wsta202_result.get("live_preflight", {}).get("json_path"),
        "fresh_wsta203_audit_json": wsta203_result.get("wrapper_manifest_audit", {}).get("json_path"),
        "fresh_wsta204_verifier_json": wsta204_result.get("live_result_verifier", {}).get("json_path"),
        "fresh_wsta205_bundle_json": wsta205_bundle.get("json_path"),
        "fresh_wsta205_transaction_script": wsta205_bundle.get("transaction_script"),
        "preparer_script": rel(out_sh),
        "replayed_wsta202_decision": wsta202_result.get("decision"),
        "replayed_wsta203_decision": wsta203_result.get("decision"),
        "replayed_wsta204_decision": wsta204_result.get("decision"),
        "replayed_wsta205_decision": wsta205_result.get("decision"),
        "ready_for_fresh_prepare": current,
        "ready_for_immediate_live_execute": current and token_ready,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "operator_acknowledgements_required": wsta205_bundle.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": [
            "WSTA206-replays-WSTA202-through-WSTA205-from-current-WSTA201-status",
            "WSTA206-emits-token-gated-fresh-prepare-script",
            "operator-must-run-resulting-WSTA205-transaction-script-manually",
            *(wsta205_bundle.get("operator_preflight_checks") or []),
        ],
        "abort_conditions": wsta205_bundle.get("abort_conditions") or [],
        "cleanup_expectations": wsta205_bundle.get("cleanup_expectations") or [],
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_preparer(preparer: dict[str, Any], script_text: str) -> dict[str, bool]:
    serialized = json.dumps(preparer, sort_keys=True) + "\n" + script_text
    return {
        "schema_ok": preparer.get("schema") == "a90-wsta206-wsta201-fresh-transaction-preparer-v1",
        "state_current": preparer.get("state") in (
            "FRESH_TRANSACTION_PREPARER_READY_TOKEN_READY_DEFAULT_OFF",
            "FRESH_TRANSACTION_PREPARER_READY_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "ready_for_fresh_prepare": preparer.get("ready_for_fresh_prepare") is True,
        "fresh_wsta205_transaction_script_present": bool(preparer.get("fresh_wsta205_transaction_script")),
        "script_has_strict_shell": script_text.startswith("#!/bin/sh\nset -eu\n"),
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in script_text,
        "script_invokes_self": "run_wsta206_wsta201_fresh_transaction_preparer.py" in script_text,
        "script_requires_token_ready": "ready_for_immediate_live_execute" in script_text,
        "script_prints_transaction_script": "fresh_wsta205_transaction_script" in script_text,
        "replay_decisions_pass": (
            preparer.get("replayed_wsta202_decision") == wsta202.PASS_DECISION
            and preparer.get("replayed_wsta203_decision") == wsta203.PASS_DECISION
            and preparer.get("replayed_wsta204_decision") == wsta204.SOURCE_PASS_DECISION
            and preparer.get("replayed_wsta205_decision") == wsta205.PASS_DECISION
        ),
        "token_value_not_included": preparer.get("token_value_included") is False,
        "correct_token_not_supplied": preparer.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": preparer.get("correct_wsta161_token_in_artifact") is False,
        "ack_stack_matches_wsta198": preparer.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "default_off": preparer.get("default_off") is True,
        "live_not_requested": preparer.get("live_execution_requested") is False,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": preparer.get("secret_values_logged") == 0,
        "public_url_not_logged": preparer.get("public_url_value_logged") is False,
    }


def markdown(preparer: dict[str, Any]) -> str:
    lines = [
        "# WSTA201 Fresh Transaction Preparer",
        "",
        f"- State: `{preparer.get('state')}`",
        f"- Ready for fresh prepare: `{str(preparer.get('ready_for_fresh_prepare')).lower()}`",
        f"- Ready for immediate live execute: `{str(preparer.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Token env present: `{str(preparer.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(preparer.get('private_token_matches_wsta161')).lower()}`",
        f"- Fresh WSTA205 transaction script: `{preparer.get('fresh_wsta205_transaction_script')}`",
        f"- Preparer script: `{preparer.get('preparer_script')}`",
        "",
        "## Boundary",
        "",
        "WSTA206 replays host-only WSTA202 through WSTA205 and emits a fresh prepare script. It does not run the WSTA205 transaction script.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_emit_gate", "wsta206-blocked-explicit-emit-gate-required"),
        ("private_run_dir", "wsta206-blocked-nonprivate-run-dir"),
        ("wsta201_status_private", "wsta206-blocked-wsta201-status-nonprivate"),
        ("wsta201_status_present", "wsta206-blocked-wsta201-status-missing"),
        ("wsta201_status_valid", result.get("wsta201_status_error") or "wsta206-blocked-wsta201-status-invalid"),
        ("wsta202_replay_valid", "wsta206-blocked-wsta202-replay-invalid"),
        ("wsta203_replay_valid", "wsta206-blocked-wsta203-replay-invalid"),
        ("wsta204_replay_valid", "wsta206-blocked-wsta204-replay-invalid"),
        ("wsta205_replay_valid", "wsta206-blocked-wsta205-replay-invalid"),
        ("fresh_transaction_preparer_valid", "wsta206-blocked-fresh-transaction-preparer-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta206-wsta201-fresh-transaction-preparer-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    status_path = resolve_path(args.wsta201_status_json)
    result: dict[str, Any] = {
        "scope": "WSTA206 host-only fresh WSTA205 transaction preparer",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta201_status_json": rel(status_path),
        "safety": safety_flags(),
        "checks": {
            "explicit_emit_gate": bool(args.emit_wsta206_fresh_transaction_preparer),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta201_status_private": wsta160.is_under(status_path, PRIVATE_ROOT),
            "wsta201_status_present": status_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("explicit_emit_gate", "wsta201_status_private", "wsta201_status_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    valid, decision, status_info = validate_wsta201_status(status_path)
    result["wsta201_status_checks"] = status_info.get("checks", {})
    result["checks"]["wsta201_status_valid"] = valid
    result["wsta201_status_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta202_dir = run_dir / "wsta202-replay"
    wsta202_result = wsta202.run(replay_args_wsta202(wsta202_dir, status_path))
    result["safety"]["wsta202_replay_executed"] = True
    result["wsta202_replay"] = {
        "run_dir": rel(wsta202_dir),
        "result_json": rel(wsta202_dir / wsta202.SUMMARY_NAME),
        "preflight_json": rel(wsta202_dir / wsta202.PREFLIGHT_JSON_NAME),
        "decision": wsta202_result.get("decision"),
    }
    result["wsta202_replay_checks"] = validate_replay(
        wsta202_result,
        wsta202.PASS_DECISION,
        ["status_valid", "wsta201_recheck_valid", "status_stable_view_match", "live_preflight_valid"],
        wsta202_result.get("safety", {}) if isinstance(wsta202_result.get("safety"), dict) else {},
    )
    result["checks"]["wsta202_replay_valid"] = all(result["wsta202_replay_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["wsta202_replay_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta203_dir = run_dir / "wsta203-replay"
    wsta203_result = wsta203.run(replay_args_wsta203(wsta203_dir, wsta202_dir / wsta202.PREFLIGHT_JSON_NAME))
    result["safety"]["wsta203_replay_executed"] = True
    result["wsta203_replay"] = {
        "run_dir": rel(wsta203_dir),
        "result_json": rel(wsta203_dir / wsta203.SUMMARY_NAME),
        "audit_json": rel(wsta203_dir / wsta203.AUDIT_JSON_NAME),
        "decision": wsta203_result.get("decision"),
    }
    result["wsta203_replay_checks"] = validate_replay(
        wsta203_result,
        wsta203.PASS_DECISION,
        [
            "preflight_valid",
            "wsta202_recheck_valid",
            "preflight_stable_view_match",
            "handoff_wrapper_audit_valid",
            "wsta198_wrapper_audit_valid",
            "wrapper_manifest_audit_valid",
        ],
        wsta203_result.get("safety", {}) if isinstance(wsta203_result.get("safety"), dict) else {},
    )
    result["checks"]["wsta203_replay_valid"] = all(result["wsta203_replay_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["wsta203_replay_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta204_dir = run_dir / "wsta204-replay"
    wsta204_result = wsta204.run(replay_args_wsta204(wsta204_dir, wsta203_dir / wsta203.AUDIT_JSON_NAME))
    result["safety"]["wsta204_replay_executed"] = True
    result["wsta204_replay"] = {
        "run_dir": rel(wsta204_dir),
        "result_json": rel(wsta204_dir / wsta204.SUMMARY_NAME),
        "verifier_json": rel(wsta204_dir / wsta204.VERIFIER_JSON_NAME),
        "decision": wsta204_result.get("decision"),
    }
    result["wsta204_replay_checks"] = validate_replay(
        wsta204_result,
        wsta204.SOURCE_PASS_DECISION,
        ["audit_valid", "wsta203_recheck_valid", "audit_stable_view_match", "live_result_verifier_valid"],
        wsta204_result.get("safety", {}) if isinstance(wsta204_result.get("safety"), dict) else {},
    )
    result["checks"]["wsta204_replay_valid"] = all(result["wsta204_replay_checks"].values())
    write_json(out_path, result)
    if not result["checks"]["wsta204_replay_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta205_dir = run_dir / "wsta205-replay"
    wsta205_result = wsta205.run(replay_args_wsta205(wsta205_dir, wsta204_dir / wsta204.VERIFIER_JSON_NAME))
    result["safety"]["wsta205_replay_executed"] = True
    result["wsta205_replay"] = {
        "run_dir": rel(wsta205_dir),
        "result_json": rel(wsta205_dir / wsta205.SUMMARY_NAME),
        "bundle_json": rel(wsta205_dir / wsta205.TRANSACTION_JSON_NAME),
        "transaction_script": rel(wsta205_dir / wsta205.TRANSACTION_SH_NAME),
        "decision": wsta205_result.get("decision"),
    }
    result["wsta205_replay_checks"] = validate_replay(
        wsta205_result,
        wsta205.PASS_DECISION,
        ["verifier_valid", "wsta204_recheck_valid", "verifier_stable_view_match", "live_transaction_bundle_valid"],
        wsta205_result.get("safety", {}) if isinstance(wsta205_result.get("safety"), dict) else {},
    )
    result["checks"]["wsta205_replay_valid"] = all(result["wsta205_replay_checks"].values())
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not result["checks"]["wsta205_replay_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    preparer_json = run_dir / PREPARER_JSON_NAME
    preparer_sh = run_dir / PREPARER_SH_NAME
    preparer_md = run_dir / PREPARER_MD_NAME
    script_text = preparer_script(status_path)
    preparer = build_preparer(
        status_path,
        wsta202_result,
        wsta203_result,
        wsta204_result,
        wsta205_result,
        result["token_checks"],
        preparer_json,
        preparer_sh,
        preparer_md,
    )
    result["fresh_transaction_preparer_checks"] = validate_preparer(preparer, script_text)
    result["checks"]["fresh_transaction_preparer_valid"] = all(result["fresh_transaction_preparer_checks"].values())
    result["fresh_transaction_preparer"] = preparer
    if result["checks"]["fresh_transaction_preparer_valid"]:
        write_json(preparer_json, result)
        write_text(preparer_sh, script_text)
        preparer_sh.chmod(0o700)
        write_text(preparer_md, markdown(preparer))
        result["safety"]["wsta206_prepare_script_generated"] = True
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta201-status-json", type=Path, default=DEFAULT_WSTA201_STATUS_JSON)
    parser.add_argument("--emit-wsta206-fresh-transaction-preparer", action="store_true")
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
        payload = {"decision": "wsta206-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
