#!/usr/bin/env python3
"""WSTA203 host-only WSTA202 wrapper manifest audit.

Consumes a private WSTA202 live preflight result, re-runs WSTA202 from the same
WSTA201 status, and audits the existing WSTA200 handoff wrapper plus WSTA198
SSH/chroot live wrapper.  WSTA203 is a manifest audit only: it never executes
the handoff shell, never runs WSTA198 live, and never supplies the WSTA161 token
to the device.
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
import run_wsta202_wsta201_live_preflight as wsta202  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA202_PREFLIGHT_JSON = (
    DEFAULT_RUN_BASE
    / "wsta202-wsta201-live-preflight-20260705T175342KST"
    / wsta202.PREFLIGHT_JSON_NAME
)
PASS_DECISION = "wsta203-wsta202-wrapper-manifest-audit-pass"
SUMMARY_NAME = "wsta203_result.json"
AUDIT_JSON_NAME = "wsta203_wsta202_wrapper_manifest_audit.json"
AUDIT_MD_NAME = "wsta203_wsta202_wrapper_manifest_audit.md"
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
        "wsta202_recheck_executed": False,
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
        "scope": "WSTA203 host-only WSTA202 wrapper manifest audit",
        "default_mode": "host-only-audit-existing-wsta200-and-wsta198-wrappers",
        "input": "workspace/private/runs/server-distro/<wsta202-run>/wsta202_wsta201_live_preflight.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta202-preflight-json",
            "workspace/private/runs/server-distro/<wsta202-run>/wsta202_wsta201_live_preflight.json",
            "--audit-wsta203-wrapper-manifest",
        ],
        "live_execution": "not-run-by-wsta203",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "wrapper_manifest_audit": result.get("wrapper_manifest_audit", {}),
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


def stable_preflight_view(preflight: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_wsta201_status": preflight.get("source_wsta201_status"),
        "wsta200_handoff_json": preflight.get("wsta200_handoff_json"),
        "handoff_command_script": preflight.get("handoff_command_script"),
        "wsta198_live_command_script": preflight.get("wsta198_live_command_script"),
        "selected_transport": preflight.get("selected_transport"),
        "canary_service": preflight.get("canary_service"),
        "handoff_current": preflight.get("handoff_current"),
        "status_stable_view_match": preflight.get("status_stable_view_match"),
        "ready_for_attended_live_handoff": preflight.get("ready_for_attended_live_handoff"),
        "operator_acknowledgements_required": preflight.get("operator_acknowledgements_required"),
        "operator_preflight_checks": preflight.get("operator_preflight_checks"),
        "abort_conditions": preflight.get("abort_conditions"),
        "cleanup_expectations": preflight.get("cleanup_expectations"),
        "default_off": preflight.get("default_off"),
        "live_execution_requested": preflight.get("live_execution_requested"),
        "public_url_value_logged": preflight.get("public_url_value_logged"),
        "secret_values_logged": preflight.get("secret_values_logged"),
    }


def unwrap_preflight_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if isinstance(payload.get("live_preflight"), dict):
        return payload["live_preflight"], payload
    if payload.get("schema") == "a90-wsta202-wsta201-live-preflight-v1":
        return payload, {"decision": wsta202.PASS_DECISION, "safety": safety_flags()}
    return None, payload


def validate_preflight_payload(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta203-blocked-preflight-unreadable", {"error": str(exc)}
    preflight, result_payload = unwrap_preflight_payload(payload)
    if not isinstance(preflight, dict):
        return False, "wsta203-blocked-preflight-missing", {"payload_decision": payload.get("decision")}
    source_status = resolve_path(preflight.get("source_wsta201_status", ""))
    handoff_json = resolve_path(preflight.get("wsta200_handoff_json", ""))
    handoff_script = resolve_path(preflight.get("handoff_command_script", ""))
    wsta198_script = resolve_path(preflight.get("wsta198_live_command_script", ""))
    handoff_script_text = handoff_script.read_text(encoding="utf-8") if handoff_script.is_file() else ""
    wsta198_script_text = wsta198_script.read_text(encoding="utf-8") if wsta198_script.is_file() else ""
    safety = result_payload.get("safety", {}) if isinstance(result_payload.get("safety"), dict) else {}
    mutation = no_mutation_safety(safety)
    serialized = json.dumps(payload, sort_keys=True) + "\n" + handoff_script_text + "\n" + wsta198_script_text
    checks = {
        "preflight_private": wsta160.is_under(path, PRIVATE_ROOT),
        "decision_pass": result_payload.get("decision") in (None, wsta202.PASS_DECISION),
        "preflight_state_current": preflight.get("state") in (
            "BLOCKED_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF",
            "READY_FOR_ATTENDED_WSTA200_WRAPPER_EXECUTION_DEFAULT_OFF",
        ),
        "handoff_current": preflight.get("handoff_current") is True,
        "status_stable_view_match": preflight.get("status_stable_view_match") is True,
        "ready_for_attended_live_handoff": preflight.get("ready_for_attended_live_handoff") is True,
        "source_status_private": wsta160.is_under(source_status, PRIVATE_ROOT),
        "source_status_present": source_status.is_file(),
        "handoff_json_private": wsta160.is_under(handoff_json, PRIVATE_ROOT),
        "handoff_json_present": handoff_json.is_file(),
        "handoff_script_private": wsta160.is_under(handoff_script, PRIVATE_ROOT),
        "handoff_script_present": handoff_script.is_file(),
        "handoff_script_executable": handoff_script.is_file() and bool(handoff_script.stat().st_mode & 0o100),
        "wsta198_script_private": wsta160.is_under(wsta198_script, PRIVATE_ROOT),
        "wsta198_script_present": wsta198_script.is_file(),
        "wsta198_script_executable": wsta198_script.is_file() and bool(wsta198_script.stat().st_mode & 0o100),
        "ack_stack_matches_wsta198": preflight.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "token_value_not_included": preflight.get("token_value_included") is False,
        "correct_token_not_supplied": preflight.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": preflight.get("correct_wsta161_token_in_artifact") is False,
        "default_off": preflight.get("default_off") is True,
        "live_not_requested": preflight.get("live_execution_requested") is False,
        "no_mutation_safety": all(mutation.values()),
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": preflight.get("secret_values_logged") == 0,
        "public_url_not_logged": preflight.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta203-blocked-preflight-invalid", {
            "payload": payload,
            "preflight": preflight,
            "checks": checks,
            "mutation_checks": mutation,
        }
    return True, "ok", {
        "payload": payload,
        "preflight": preflight,
        "checks": checks,
        "source_status": source_status,
        "handoff_json": handoff_json,
        "handoff_script": handoff_script,
        "wsta198_script": wsta198_script,
        "handoff_script_text": handoff_script_text,
        "wsta198_script_text": wsta198_script_text,
    }


def wsta202_recheck_args(run_dir: Path, status_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta203-wsta202-recheck",
        run_dir=run_dir,
        wsta201_status_json=status_path,
        prepare_wsta202_live_preflight=True,
        print_template=False,
        print_full_json=False,
    )


def validate_recheck(recheck: dict[str, Any]) -> dict[str, bool]:
    checks = recheck.get("checks", {}) if isinstance(recheck.get("checks"), dict) else {}
    safety = recheck.get("safety", {}) if isinstance(recheck.get("safety"), dict) else {}
    preflight = recheck.get("live_preflight", {}) if isinstance(recheck.get("live_preflight"), dict) else {}
    mutation = no_mutation_safety(safety)
    return {
        "decision_pass": recheck.get("decision") == wsta202.PASS_DECISION,
        "status_valid": checks.get("status_valid") is True,
        "wsta201_recheck_valid": checks.get("wsta201_recheck_valid") is True,
        "status_stable_view_match": checks.get("status_stable_view_match") is True,
        "live_preflight_valid": checks.get("live_preflight_valid") is True,
        "handoff_current": preflight.get("handoff_current") is True,
        "ready_for_attended_live_handoff": preflight.get("ready_for_attended_live_handoff") is True,
        "no_mutation_safety": all(mutation.values()),
    }


def audit_wsta200_handoff(
    handoff_json: Path,
    handoff_script: Path,
    handoff_script_text: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    handoff = load_json(handoff_json)
    handoff_checks = wsta200.validate_handoff(handoff, handoff_script_text)
    serialized = json.dumps(handoff, sort_keys=True) + "\n" + handoff_script_text
    checks = {
        "handoff_json_private": wsta160.is_under(handoff_json, PRIVATE_ROOT),
        "handoff_schema_ok": handoff.get("schema") == "a90-wsta200-wsta199-operator-handoff-v1",
        "handoff_state_ready": handoff.get("state") in (
            "READY_OPERATOR_HANDOFF_WSTA198_ATTENDED_LIVE",
            "READY_OPERATOR_HANDOFF_WSTA198_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "handoff_builtin_checks_pass": all(handoff_checks.values()),
        "handoff_script_path_matches_preflight": rel(handoff_script) == preflight.get("handoff_command_script"),
        "wsta198_script_matches_preflight": handoff.get("wsta198_live_command_script") == preflight.get("wsta198_live_command_script"),
        "adapter_json_private": wsta160.is_under(resolve_path(handoff.get("wsta198_adapter_json", "")), PRIVATE_ROOT),
        "adapter_json_present": resolve_path(handoff.get("wsta198_adapter_json", "")).is_file(),
        "ack_stack_matches_wsta198": handoff.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "token_value_not_included": handoff.get("token_value_included") is False,
        "correct_token_not_supplied": handoff.get("correct_wsta161_token_supplied") is False,
        "script_has_strict_shell": handoff_script_text.startswith("#!/bin/sh\nset -eu\n"),
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in handoff_script_text,
        "script_reruns_wsta199": "run_wsta199_wsta198_adapter_status.py" in handoff_script_text,
        "script_asserts_wsta199_pass": "wsta199-wsta198-adapter-status-pass" in handoff_script_text,
        "script_asserts_adapter_current": "adapter_current" in handoff_script_text,
        "script_execs_wsta198_wrapper": f"exec '{handoff.get('wsta198_live_command_script')}'" in handoff_script_text,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": handoff.get("secret_values_logged") == 0,
        "public_url_not_logged": handoff.get("public_url_value_logged") is False,
    }
    return {
        "handoff_json": rel(handoff_json),
        "handoff_script": rel(handoff_script),
        "wsta198_adapter_json": handoff.get("wsta198_adapter_json"),
        "checks": checks,
        "builtin_handoff_checks": handoff_checks,
        "valid": all(checks.values()),
    }


def audit_wsta198_adapter(
    adapter_json: Path,
    wsta198_script: Path,
    wsta198_script_text: str,
    preflight: dict[str, Any],
) -> dict[str, Any]:
    adapter = load_json(adapter_json)
    adapter_checks = wsta198.validate_adapter_packet(adapter, wsta198_script_text)
    serialized = json.dumps(adapter, sort_keys=True) + "\n" + wsta198_script_text
    source_text = Path(wsta198.__file__).read_text(encoding="utf-8")
    checks = {
        "adapter_json_private": wsta160.is_under(adapter_json, PRIVATE_ROOT),
        "adapter_schema_ok": adapter.get("schema") == "a90-wsta198-seccomp-load-canary-ssh-adapter-v1",
        "adapter_builtin_checks_pass": all(adapter_checks.values()),
        "script_path_matches_adapter": adapter.get("live_command_script") == rel(wsta198_script),
        "script_path_matches_preflight": rel(wsta198_script) == preflight.get("wsta198_live_command_script"),
        "ack_stack_in_script": all(flag in wsta198_script_text for flag in wsta198.ACK_FLAGS),
        "script_has_execute_gate": "--execute-real-seccomp-load-canary-over-ssh" in wsta198_script_text,
        "script_prints_full_json": "--print-full-json" in wsta198_script_text,
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in wsta198_script_text,
        "source_has_fresh_health": "run_readonly_health_checks(args.health_timeout)" in source_text,
        "source_has_post_health_flag": 'post_run_native_health_checked"] = True' in source_text,
        "source_has_cleanup_gate": "chroot_cleanup_ok" in source_text and "wsta94_cleanup_script" in source_text,
        "source_has_redacted_stdin_token": "ssh_exec_token_script" in source_text and "redacted_text" in source_text,
        "source_sets_seccomp_only_after_marker": "result[\"checks\"][\"canary_loaded\"]" in source_text,
        "source_has_no_flash_surface": ("native_" + "init_flash.py") not in source_text,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized + "\n" + source_text,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": adapter.get("secret_values_logged") == 0,
        "public_url_not_logged": adapter.get("public_url_value_logged") is False,
    }
    return {
        "wsta198_adapter_json": rel(adapter_json),
        "wsta198_live_command_script": rel(wsta198_script),
        "checks": checks,
        "builtin_adapter_checks": adapter_checks,
        "valid": all(checks.values()),
    }


def build_audit(
    preflight_path: Path,
    preflight: dict[str, Any],
    recheck_result: dict[str, Any],
    recheck_path: Path,
    handoff_audit: dict[str, Any],
    adapter_audit: dict[str, Any],
    token_checks: dict[str, bool],
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    recheck_preflight = recheck_result.get("live_preflight", {})
    current = bool(
        recheck_result.get("decision") == wsta202.PASS_DECISION
        and isinstance(recheck_preflight, dict)
        and stable_preflight_view(preflight) == stable_preflight_view(recheck_preflight)
    )
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    state = "STALE_WSTA202_PREFLIGHT_RECHECK_REQUIRED"
    if current and token_ready:
        state = "WRAPPER_MANIFEST_CURRENT_TOKEN_READY_DEFAULT_OFF"
    elif current:
        state = "WRAPPER_MANIFEST_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF"
    return {
        "schema": "a90-wsta203-wsta202-wrapper-manifest-audit-v1",
        "state": state,
        "source_wsta202_preflight": rel(preflight_path),
        "fresh_wsta202_recheck_result": rel(recheck_path),
        "wsta200_handoff_json": preflight.get("wsta200_handoff_json"),
        "handoff_command_script": preflight.get("handoff_command_script"),
        "wsta198_live_command_script": preflight.get("wsta198_live_command_script"),
        "selected_transport": preflight.get("selected_transport"),
        "canary_service": preflight.get("canary_service"),
        "handoff_current": current,
        "preflight_stable_view_match": current,
        "ready_for_attended_live_handoff": current,
        "ready_for_immediate_live_execute": current and token_ready,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "handoff_wrapper_audit_valid": handoff_audit.get("valid") is True,
        "wsta198_wrapper_audit_valid": adapter_audit.get("valid") is True,
        "operator_acknowledgements_required": preflight.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": [
            "WSTA203-audited-existing-WSTA200-wrapper-and-WSTA198-wrapper",
            "WSTA203-rechecked-WSTA202-from-current-WSTA201-status",
            "operator-must-run-private-WSTA200-handoff-wrapper-manually",
            "private-token-env-present-at-wrapper-execution-time",
            *(preflight.get("operator_preflight_checks") or []),
        ],
        "abort_conditions": preflight.get("abort_conditions") or [],
        "cleanup_expectations": preflight.get("cleanup_expectations") or [],
        "recommended_next_action": (
            "operator-may-run-wsta200-private-handoff-wrapper-after-final-human-confirmation"
            if current and token_ready
            else "export-private-token-then-rerun-wsta202-and-wsta203"
            if current
            else "rerun-wsta202-from-current-wsta201-status-before-live"
        ),
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_audit(audit: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(audit, sort_keys=True)
    return {
        "schema_ok": audit.get("schema") == "a90-wsta203-wsta202-wrapper-manifest-audit-v1",
        "state_current": audit.get("state") in (
            "WRAPPER_MANIFEST_CURRENT_TOKEN_READY_DEFAULT_OFF",
            "WRAPPER_MANIFEST_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "handoff_current": audit.get("handoff_current") is True,
        "preflight_stable_view_match": audit.get("preflight_stable_view_match") is True,
        "ready_for_attended_live_handoff": audit.get("ready_for_attended_live_handoff") is True,
        "handoff_wrapper_audit_valid": audit.get("handoff_wrapper_audit_valid") is True,
        "wsta198_wrapper_audit_valid": audit.get("wsta198_wrapper_audit_valid") is True,
        "token_value_not_included": audit.get("token_value_included") is False,
        "correct_token_not_supplied": audit.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": audit.get("correct_wsta161_token_in_artifact") is False,
        "ack_stack_matches_wsta198": audit.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "default_off": audit.get("default_off") is True,
        "live_not_requested": audit.get("live_execution_requested") is False,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": audit.get("secret_values_logged") == 0,
        "public_url_not_logged": audit.get("public_url_value_logged") is False,
    }


def markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# WSTA202 Wrapper Manifest Audit",
        "",
        f"- State: `{audit.get('state')}`",
        f"- Handoff current: `{str(audit.get('handoff_current')).lower()}`",
        f"- Preflight stable view match: `{str(audit.get('preflight_stable_view_match')).lower()}`",
        f"- WSTA200 wrapper audit: `{str(audit.get('handoff_wrapper_audit_valid')).lower()}`",
        f"- WSTA198 wrapper audit: `{str(audit.get('wsta198_wrapper_audit_valid')).lower()}`",
        f"- Ready for immediate live execute: `{str(audit.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Token env present: `{str(audit.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(audit.get('private_token_matches_wsta161')).lower()}`",
        f"- Recommended next action: `{audit.get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
        "WSTA203 is a wrapper manifest audit only. It does not execute the WSTA200 handoff or WSTA198 live canary.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_audit_gate", "wsta203-blocked-explicit-audit-gate-required"),
        ("private_run_dir", "wsta203-blocked-nonprivate-run-dir"),
        ("preflight_private", "wsta203-blocked-preflight-nonprivate"),
        ("preflight_present", "wsta203-blocked-preflight-missing"),
        ("preflight_valid", result.get("preflight_error") or "wsta203-blocked-preflight-invalid"),
        ("wsta202_recheck_valid", "wsta203-blocked-wsta202-recheck-invalid"),
        ("preflight_stable_view_match", "wsta203-blocked-preflight-drift"),
        ("handoff_wrapper_audit_valid", "wsta203-blocked-handoff-wrapper-audit-invalid"),
        ("wsta198_wrapper_audit_valid", "wsta203-blocked-wsta198-wrapper-audit-invalid"),
        ("wrapper_manifest_audit_valid", "wsta203-blocked-wrapper-manifest-audit-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta203-wsta202-wrapper-manifest-audit-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    preflight_path = resolve_path(args.wsta202_preflight_json)
    result: dict[str, Any] = {
        "scope": "WSTA203 host-only WSTA202 wrapper manifest audit",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta202_preflight_json": rel(preflight_path),
        "safety": safety_flags(),
        "checks": {
            "explicit_audit_gate": bool(args.audit_wsta203_wrapper_manifest),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "preflight_private": wsta160.is_under(preflight_path, PRIVATE_ROOT),
            "preflight_present": preflight_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("explicit_audit_gate", "preflight_private", "preflight_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    valid, decision, preflight_info = validate_preflight_payload(preflight_path)
    result["preflight_checks"] = preflight_info.get("checks", {})
    result["checks"]["preflight_valid"] = valid
    result["preflight_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    recheck_dir = run_dir / "wsta202-recheck"
    recheck_result = wsta202.run(wsta202_recheck_args(recheck_dir, preflight_info["source_status"]))
    result["safety"]["wsta202_recheck_executed"] = True
    result["wsta202_recheck"] = {
        "run_dir": rel(recheck_dir),
        "result_json": rel(recheck_dir / wsta202.SUMMARY_NAME),
        "preflight_json": rel(recheck_dir / wsta202.PREFLIGHT_JSON_NAME),
        "decision": recheck_result.get("decision"),
    }
    result["wsta202_recheck_checks"] = validate_recheck(recheck_result)
    result["checks"]["wsta202_recheck_valid"] = all(result["wsta202_recheck_checks"].values())
    result["checks"]["preflight_stable_view_match"] = bool(
        result["checks"]["wsta202_recheck_valid"]
        and stable_preflight_view(preflight_info["preflight"]) == stable_preflight_view(recheck_result["live_preflight"])
    )
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not (result["checks"]["wsta202_recheck_valid"] and result["checks"]["preflight_stable_view_match"]):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    handoff_audit = audit_wsta200_handoff(
        preflight_info["handoff_json"],
        preflight_info["handoff_script"],
        preflight_info["handoff_script_text"],
        preflight_info["preflight"],
    )
    result["handoff_wrapper_audit"] = handoff_audit
    result["checks"]["handoff_wrapper_audit_valid"] = handoff_audit.get("valid") is True
    adapter_path = resolve_path(handoff_audit.get("wsta198_adapter_json", ""))
    adapter_audit = audit_wsta198_adapter(
        adapter_path,
        preflight_info["wsta198_script"],
        preflight_info["wsta198_script_text"],
        preflight_info["preflight"],
    )
    result["wsta198_wrapper_audit"] = adapter_audit
    result["checks"]["wsta198_wrapper_audit_valid"] = adapter_audit.get("valid") is True
    write_json(out_path, result)
    if not (result["checks"]["handoff_wrapper_audit_valid"] and result["checks"]["wsta198_wrapper_audit_valid"]):
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    audit_json = run_dir / AUDIT_JSON_NAME
    audit_md = run_dir / AUDIT_MD_NAME
    audit = build_audit(
        preflight_path,
        preflight_info["preflight"],
        recheck_result,
        recheck_dir / wsta202.SUMMARY_NAME,
        handoff_audit,
        adapter_audit,
        result["token_checks"],
        audit_json,
        audit_md,
    )
    result["wrapper_manifest_audit_checks"] = validate_audit(audit)
    result["checks"]["wrapper_manifest_audit_valid"] = all(result["wrapper_manifest_audit_checks"].values())
    result["wrapper_manifest_audit"] = audit
    if result["checks"]["wrapper_manifest_audit_valid"]:
        write_json(audit_json, result)
        write_text(audit_md, markdown(audit))
    result["decision"] = classify(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta202-preflight-json", type=Path, default=DEFAULT_WSTA202_PREFLIGHT_JSON)
    parser.add_argument("--audit-wsta203-wrapper-manifest", action="store_true")
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
        payload = {"decision": "wsta203-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
