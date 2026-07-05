#!/usr/bin/env python3
"""WSTA204 host-only WSTA198 live-result verifier.

Consumes a private WSTA203 wrapper manifest audit, re-runs WSTA203 from the
same WSTA202 preflight, and emits a default-off verifier for the future WSTA198
live result.  WSTA204 can also verify an existing WSTA198 live result JSON, but
it never executes the WSTA200 handoff shell or WSTA198 live canary itself.
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
import run_wsta203_wsta202_wrapper_manifest_audit as wsta203  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA203_AUDIT_JSON = (
    DEFAULT_RUN_BASE
    / "wsta203-wsta202-wrapper-manifest-audit-20260705T180223KST"
    / wsta203.AUDIT_JSON_NAME
)
SOURCE_PASS_DECISION = "wsta204-wsta203-live-result-verifier-source-pass"
VERIFY_PASS_DECISION = "wsta204-wsta198-live-result-verify-pass"
SUMMARY_NAME = "wsta204_result.json"
VERIFIER_JSON_NAME = "wsta204_wsta198_live_result_verifier.json"
VERIFIER_SH_NAME = "wsta204_verify_wsta198_live_result.sh"
VERIFIER_MD_NAME = "wsta204_wsta198_live_result_verifier.md"
FORBIDDEN_TOKEN_PREFIX = "WSTA161-" + "EXPLICIT"


REQUIRED_LIVE_CHECKS = [
    "explicit_live_gate",
    "private_token_env_present",
    "private_token_matches_wsta161",
    "wsta197_transport_gate_valid",
    "adapter_packet_valid",
    "fresh_health_valid",
    "ssh_key_generated",
    "native_stale_cleanup_ok",
    "local_image_present",
    "local_image_expected_sha",
    "remote_image_ready",
    "chroot_mount_ready",
    "dropbear_started",
    "debian_ssh_marker",
    "execution_returncode_bounded",
    "canary_loaded",
    "chroot_cleanup_ok",
    "post_health_valid",
]

REQUIRED_LIVE_SAFETY_TRUE = [
    "fresh_native_health_checked",
    "post_run_native_health_checked",
    "post_run_audit_executed",
    "ssh_chroot_transport",
    "dropbear_over_ncm",
    "live_command_executed",
    "correct_wsta161_token_supplied",
    "token_passed_over_stdin_redacted",
    "seccomp_filter_loaded",
    "seccomp_enforced",
]

REQUIRED_LIVE_SAFETY_FALSE = [
    "boot_flash",
    "native_reboot",
    "wifi_connect",
    "dhcp",
    "public_tunnel",
    "public_smoke",
    "packet_filter_mutation",
    "userdata_touch",
    "switch_root",
    "correct_wsta161_token_in_artifact",
    "public_url_value_logged",
]

REQUIRED_CANARY_MARKERS = [
    "returncode_bounded",
    "load_attempt_marker",
    "loaded_marker",
    "apply_ok_marker",
    "single_service_marker",
    "policy_service_marker",
    "token_literal_absent",
    "no_external_network_inputs",
]


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
        "wsta203_recheck_executed": False,
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
        "scope": "WSTA204 host-only WSTA198 live-result verifier",
        "default_mode": "emit-post-live-verifier-from-wsta203-audit",
        "input": "workspace/private/runs/server-distro/<wsta203-run>/wsta203_wsta202_wrapper_manifest_audit.json",
        "emit_command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--source-wsta203-audit-json",
            "workspace/private/runs/server-distro/<wsta203-run>/wsta203_wsta202_wrapper_manifest_audit.json",
            "--emit-wsta204-live-result-verifier",
        ],
        "verify_command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--source-wsta203-audit-json",
            "workspace/private/runs/server-distro/<wsta203-run>/wsta203_wsta202_wrapper_manifest_audit.json",
            "--verify-wsta204-live-result",
            "--wsta198-live-result-json",
            "workspace/private/runs/server-distro/<wsta198-live-run>/wsta198_result.json",
        ],
        "live_execution": "not-run-by-wsta204",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "live_result_verifier": result.get("live_result_verifier", {}),
        "live_result_verification": result.get("live_result_verification", {}),
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


def bounded_live_safety(safety: dict[str, Any]) -> dict[str, bool]:
    return {
        **{f"{key}_true": safety.get(key) is True for key in REQUIRED_LIVE_SAFETY_TRUE},
        **{f"{key}_false": safety.get(key) is False for key in REQUIRED_LIVE_SAFETY_FALSE},
        "device_action_expected": safety.get("device_action") == "single-service-seccomp-load-canary-over-ssh-chroot",
        "secret_values_zero": safety.get("secret_values_logged") == 0,
    }


def stable_audit_view(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_wsta202_preflight": audit.get("source_wsta202_preflight"),
        "wsta200_handoff_json": audit.get("wsta200_handoff_json"),
        "handoff_command_script": audit.get("handoff_command_script"),
        "wsta198_live_command_script": audit.get("wsta198_live_command_script"),
        "selected_transport": audit.get("selected_transport"),
        "canary_service": audit.get("canary_service"),
        "handoff_current": audit.get("handoff_current"),
        "preflight_stable_view_match": audit.get("preflight_stable_view_match"),
        "ready_for_attended_live_handoff": audit.get("ready_for_attended_live_handoff"),
        "handoff_wrapper_audit_valid": audit.get("handoff_wrapper_audit_valid"),
        "wsta198_wrapper_audit_valid": audit.get("wsta198_wrapper_audit_valid"),
        "operator_acknowledgements_required": audit.get("operator_acknowledgements_required"),
        "operator_preflight_checks": audit.get("operator_preflight_checks"),
        "abort_conditions": audit.get("abort_conditions"),
        "cleanup_expectations": audit.get("cleanup_expectations"),
        "default_off": audit.get("default_off"),
        "live_execution_requested": audit.get("live_execution_requested"),
        "public_url_value_logged": audit.get("public_url_value_logged"),
        "secret_values_logged": audit.get("secret_values_logged"),
    }


def unwrap_audit_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if isinstance(payload.get("wrapper_manifest_audit"), dict):
        return payload["wrapper_manifest_audit"], payload
    if payload.get("schema") == "a90-wsta203-wsta202-wrapper-manifest-audit-v1":
        return payload, {"decision": wsta203.PASS_DECISION, "safety": safety_flags()}
    return None, payload


def validate_audit_payload(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta204-blocked-audit-unreadable", {"error": str(exc)}
    audit, result_payload = unwrap_audit_payload(payload)
    if not isinstance(audit, dict):
        return False, "wsta204-blocked-audit-missing", {"payload_decision": payload.get("decision")}
    source_preflight = resolve_path(audit.get("source_wsta202_preflight", ""))
    handoff_script = resolve_path(audit.get("handoff_command_script", ""))
    wsta198_script = resolve_path(audit.get("wsta198_live_command_script", ""))
    safety = result_payload.get("safety", {}) if isinstance(result_payload.get("safety"), dict) else {}
    mutation = no_mutation_safety(safety)
    serialized = json.dumps(payload, sort_keys=True)
    checks = {
        "audit_private": wsta160.is_under(path, PRIVATE_ROOT),
        "decision_pass": result_payload.get("decision") in (None, wsta203.PASS_DECISION),
        "audit_state_current": audit.get("state") in (
            "WRAPPER_MANIFEST_CURRENT_TOKEN_READY_DEFAULT_OFF",
            "WRAPPER_MANIFEST_CURRENT_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "handoff_current": audit.get("handoff_current") is True,
        "preflight_stable_view_match": audit.get("preflight_stable_view_match") is True,
        "ready_for_attended_live_handoff": audit.get("ready_for_attended_live_handoff") is True,
        "handoff_wrapper_audit_valid": audit.get("handoff_wrapper_audit_valid") is True,
        "wsta198_wrapper_audit_valid": audit.get("wsta198_wrapper_audit_valid") is True,
        "source_preflight_private": wsta160.is_under(source_preflight, PRIVATE_ROOT),
        "source_preflight_present": source_preflight.is_file(),
        "handoff_script_private": wsta160.is_under(handoff_script, PRIVATE_ROOT),
        "handoff_script_present": handoff_script.is_file(),
        "handoff_script_executable": handoff_script.is_file() and bool(handoff_script.stat().st_mode & 0o100),
        "wsta198_script_private": wsta160.is_under(wsta198_script, PRIVATE_ROOT),
        "wsta198_script_present": wsta198_script.is_file(),
        "wsta198_script_executable": wsta198_script.is_file() and bool(wsta198_script.stat().st_mode & 0o100),
        "ack_stack_matches_wsta198": audit.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "token_value_not_included": audit.get("token_value_included") is False,
        "correct_token_not_supplied": audit.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": audit.get("correct_wsta161_token_in_artifact") is False,
        "default_off": audit.get("default_off") is True,
        "live_not_requested": audit.get("live_execution_requested") is False,
        "no_mutation_safety": all(mutation.values()),
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": audit.get("secret_values_logged") == 0,
        "public_url_not_logged": audit.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta204-blocked-audit-invalid", {
            "payload": payload,
            "audit": audit,
            "checks": checks,
            "mutation_checks": mutation,
        }
    return True, "ok", {
        "payload": payload,
        "audit": audit,
        "checks": checks,
        "source_preflight": source_preflight,
        "handoff_script": handoff_script,
        "wsta198_script": wsta198_script,
    }


def wsta203_recheck_args(run_dir: Path, preflight_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta204-wsta203-recheck",
        run_dir=run_dir,
        wsta202_preflight_json=preflight_path,
        audit_wsta203_wrapper_manifest=True,
        print_template=False,
        print_full_json=False,
    )


def validate_recheck(recheck: dict[str, Any]) -> dict[str, bool]:
    checks = recheck.get("checks", {}) if isinstance(recheck.get("checks"), dict) else {}
    safety = recheck.get("safety", {}) if isinstance(recheck.get("safety"), dict) else {}
    audit = recheck.get("wrapper_manifest_audit", {}) if isinstance(recheck.get("wrapper_manifest_audit"), dict) else {}
    mutation = no_mutation_safety(safety)
    return {
        "decision_pass": recheck.get("decision") == wsta203.PASS_DECISION,
        "preflight_valid": checks.get("preflight_valid") is True,
        "wsta202_recheck_valid": checks.get("wsta202_recheck_valid") is True,
        "preflight_stable_view_match": checks.get("preflight_stable_view_match") is True,
        "handoff_wrapper_audit_valid": checks.get("handoff_wrapper_audit_valid") is True,
        "wsta198_wrapper_audit_valid": checks.get("wsta198_wrapper_audit_valid") is True,
        "wrapper_manifest_audit_valid": checks.get("wrapper_manifest_audit_valid") is True,
        "handoff_current": audit.get("handoff_current") is True,
        "ready_for_attended_live_handoff": audit.get("ready_for_attended_live_handoff") is True,
        "no_mutation_safety": all(mutation.values()),
    }


def verifier_script(audit_path: Path) -> str:
    return "\n".join([
        "#!/bin/sh",
        "set -eu",
        f"cd '{REPO_ROOT}'",
        'export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/a90_pycache}"',
        'result_json="${1:?wsta198-live-result-json-required}"',
        "exec python3 workspace/public/src/scripts/server-distro/run_wsta204_wsta203_live_result_verifier.py \\",
        f"  --source-wsta203-audit-json '{rel(audit_path)}' \\",
        '  --wsta198-live-result-json "$result_json" \\',
        "  --verify-wsta204-live-result \\",
        "  --print-full-json",
        "",
    ])


def build_verifier(
    audit_path: Path,
    audit: dict[str, Any],
    recheck_result: dict[str, Any],
    recheck_path: Path,
    token_checks: dict[str, bool],
    out_json: Path,
    out_sh: Path,
    out_md: Path,
) -> dict[str, Any]:
    recheck_audit = recheck_result.get("wrapper_manifest_audit", {})
    current = bool(
        recheck_result.get("decision") == wsta203.PASS_DECISION
        and isinstance(recheck_audit, dict)
        and stable_audit_view(audit) == stable_audit_view(recheck_audit)
    )
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    state = "STALE_WSTA203_AUDIT_RECHECK_REQUIRED"
    if current and token_ready:
        state = "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_READY_DEFAULT_OFF"
    elif current:
        state = "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_REQUIRED_DEFAULT_OFF"
    return {
        "schema": "a90-wsta204-wsta198-live-result-verifier-v1",
        "state": state,
        "source_wsta203_audit": rel(audit_path),
        "fresh_wsta203_recheck_result": rel(recheck_path),
        "verifier_script": rel(out_sh),
        "expected_wsta198_decision": wsta198.LIVE_PASS_DECISION,
        "required_live_checks": REQUIRED_LIVE_CHECKS,
        "required_live_safety_true": REQUIRED_LIVE_SAFETY_TRUE,
        "required_live_safety_false": REQUIRED_LIVE_SAFETY_FALSE,
        "required_canary_markers": REQUIRED_CANARY_MARKERS,
        "wsta200_handoff_json": audit.get("wsta200_handoff_json"),
        "handoff_command_script": audit.get("handoff_command_script"),
        "wsta198_live_command_script": audit.get("wsta198_live_command_script"),
        "selected_transport": audit.get("selected_transport"),
        "canary_service": audit.get("canary_service"),
        "audit_current": current,
        "audit_stable_view_match": current,
        "ready_for_attended_live_handoff": current,
        "ready_for_post_live_verification": current,
        "ready_for_immediate_live_execute": current and token_ready,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "operator_acknowledgements_required": audit.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": [
            "WSTA204-emitted-post-live-result-verifier",
            "WSTA204-rechecked-WSTA203-from-current-WSTA202-preflight",
            "operator-must-run-private-WSTA200-handoff-wrapper-manually-before-verifying",
            "verify-the-resulting-private-WSTA198-result-json-with-this-verifier",
            *(audit.get("operator_preflight_checks") or []),
        ],
        "abort_conditions": audit.get("abort_conditions") or [],
        "cleanup_expectations": audit.get("cleanup_expectations") or [],
        "verification_command_template": [
            "python3",
            rel(Path(__file__).resolve()),
            "--source-wsta203-audit-json",
            rel(audit_path),
            "--verify-wsta204-live-result",
            "--wsta198-live-result-json",
            "workspace/private/runs/server-distro/<wsta198-live-run>/wsta198_result.json",
            "--print-full-json",
        ],
        "recommended_next_action": (
            "run-wsta200-private-handoff-wrapper-then-verify-wsta198-result-json"
            if current and token_ready
            else "export-private-token-rerun-wsta202-wsta203-wsta204-then-run-handoff"
            if current
            else "rerun-wsta203-from-current-wsta202-preflight-before-live"
        ),
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_verifier(verifier: dict[str, Any], script_text: str) -> dict[str, bool]:
    serialized = json.dumps(verifier, sort_keys=True) + "\n" + script_text
    return {
        "schema_ok": verifier.get("schema") == "a90-wsta204-wsta198-live-result-verifier-v1",
        "state_current": verifier.get("state") in (
            "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_READY_DEFAULT_OFF",
            "POST_LIVE_RESULT_VERIFIER_READY_TOKEN_REQUIRED_DEFAULT_OFF",
        ),
        "audit_current": verifier.get("audit_current") is True,
        "audit_stable_view_match": verifier.get("audit_stable_view_match") is True,
        "ready_for_post_live_verification": verifier.get("ready_for_post_live_verification") is True,
        "expected_decision_ok": verifier.get("expected_wsta198_decision") == wsta198.LIVE_PASS_DECISION,
        "required_live_checks_complete": verifier.get("required_live_checks") == REQUIRED_LIVE_CHECKS,
        "required_live_safety_true_complete": verifier.get("required_live_safety_true") == REQUIRED_LIVE_SAFETY_TRUE,
        "required_live_safety_false_complete": verifier.get("required_live_safety_false") == REQUIRED_LIVE_SAFETY_FALSE,
        "required_canary_markers_complete": verifier.get("required_canary_markers") == REQUIRED_CANARY_MARKERS,
        "script_has_strict_shell": script_text.startswith("#!/bin/sh\nset -eu\n"),
        "script_invokes_self_verify": "--verify-wsta204-live-result" in script_text,
        "script_requires_result_arg": "wsta198-live-result-json-required" in script_text,
        "token_value_not_included": verifier.get("token_value_included") is False,
        "correct_token_not_supplied": verifier.get("correct_wsta161_token_supplied") is False,
        "correct_token_not_in_artifact": verifier.get("correct_wsta161_token_in_artifact") is False,
        "ack_stack_matches_wsta198": verifier.get("operator_acknowledgements_required") == wsta198.ACK_FLAGS,
        "default_off": verifier.get("default_off") is True,
        "live_not_requested": verifier.get("live_execution_requested") is False,
        "no_flash_surface": ("native_" + "init_flash.py") not in serialized,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": verifier.get("secret_values_logged") == 0,
        "public_url_not_logged": verifier.get("public_url_value_logged") is False,
    }


def validate_live_result_payload(path: Path, audit: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta204-blocked-live-result-unreadable", {"error": str(exc)}
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    canary = payload.get("canary_parse", {}) if isinstance(payload.get("canary_parse"), dict) else {}
    execution = payload.get("execution", {}) if isinstance(payload.get("execution"), dict) else {}
    adapter = payload.get("adapter", {}) if isinstance(payload.get("adapter"), dict) else {}
    fresh_health = payload.get("fresh_health", {}) if isinstance(payload.get("fresh_health"), dict) else {}
    post_health = payload.get("post_health", {}) if isinstance(payload.get("post_health"), dict) else {}
    execution_text = str(execution.get("stdout") or "") + "\n" + str(execution.get("stderr") or "")
    live_checks = {
        "live_result_private": wsta160.is_under(path, PRIVATE_ROOT),
        "decision_live_pass": payload.get("decision") == wsta198.LIVE_PASS_DECISION,
        "required_checks_true": all(checks.get(key) is True for key in REQUIRED_LIVE_CHECKS),
        "required_safety_true": all(safety.get(key) is True for key in REQUIRED_LIVE_SAFETY_TRUE),
        "required_safety_false": all(safety.get(key) is False for key in REQUIRED_LIVE_SAFETY_FALSE),
        "bounded_device_action": safety.get("device_action") == "single-service-seccomp-load-canary-over-ssh-chroot",
        "secret_values_zero": safety.get("secret_values_logged") == 0,
        "required_canary_markers": all(canary.get(key) is True for key in REQUIRED_CANARY_MARKERS),
        "execution_returncode_zero": execution.get("returncode") == 0,
        "execution_token_redacted": execution.get("input_redacted") is True,
        "execution_no_token_literal": FORBIDDEN_TOKEN_PREFIX not in execution_text,
        "execution_no_external_network_inputs": wsta198.no_external_network_inputs(execution_text),
        "fresh_health_all_checks_true": all((fresh_health.get("checks") or {}).values()) if isinstance(fresh_health.get("checks"), dict) else False,
        "post_health_all_checks_true": all((post_health.get("checks") or {}).values()) if isinstance(post_health.get("checks"), dict) else False,
        "adapter_selected_transport_matches": adapter.get("selected_transport") == audit.get("selected_transport"),
        "adapter_canary_service_matches": adapter.get("canary_service") == audit.get("canary_service"),
        "adapter_live_requested_false": adapter.get("live_execution_requested") is False,
        "adapter_seccomp_initial_false": adapter.get("seccomp_filter_loaded") is False and adapter.get("seccomp_enforced") is False,
        "no_flash_surface": ("native_" + "init_flash.py") not in json.dumps(payload, sort_keys=True),
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in json.dumps(payload, sort_keys=True),
        "no_external_network_inputs": wsta198.no_external_network_inputs(json.dumps(payload, sort_keys=True)),
    }
    if not all(live_checks.values()):
        return False, "wsta204-blocked-live-result-invalid", {
            "payload": payload,
            "checks": live_checks,
            "required_check_values": {key: checks.get(key) for key in REQUIRED_LIVE_CHECKS},
            "required_safety_true_values": {key: safety.get(key) for key in REQUIRED_LIVE_SAFETY_TRUE},
            "required_safety_false_values": {key: safety.get(key) for key in REQUIRED_LIVE_SAFETY_FALSE},
            "required_canary_values": {key: canary.get(key) for key in REQUIRED_CANARY_MARKERS},
        }
    return True, "ok", {
        "payload": payload,
        "checks": live_checks,
    }


def build_live_verification(path: Path, audit: dict[str, Any], live_info: dict[str, Any], out_json: Path) -> dict[str, Any]:
    payload = live_info["payload"]
    return {
        "schema": "a90-wsta204-wsta198-live-result-verification-v1",
        "state": "WSTA198_LIVE_RESULT_ACCEPTED",
        "wsta198_live_result_json": rel(path),
        "expected_wsta198_decision": wsta198.LIVE_PASS_DECISION,
        "actual_wsta198_decision": payload.get("decision"),
        "source_wsta203_audit": audit.get("json_path") or audit.get("source_wsta203_audit"),
        "selected_transport": audit.get("selected_transport"),
        "canary_service": audit.get("canary_service"),
        "required_live_checks": REQUIRED_LIVE_CHECKS,
        "required_live_safety_true": REQUIRED_LIVE_SAFETY_TRUE,
        "required_live_safety_false": REQUIRED_LIVE_SAFETY_FALSE,
        "required_canary_markers": REQUIRED_CANARY_MARKERS,
        "seccomp_filter_loaded": True,
        "seccomp_enforced": True,
        "fresh_native_health_checked": True,
        "post_run_native_health_checked": True,
        "post_run_cleanup_checked": True,
        "token_value_included": False,
        "correct_wsta161_token_in_artifact": False,
        "json_path": rel(out_json),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_live_verification(verification: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(verification, sort_keys=True)
    return {
        "schema_ok": verification.get("schema") == "a90-wsta204-wsta198-live-result-verification-v1",
        "state_accepted": verification.get("state") == "WSTA198_LIVE_RESULT_ACCEPTED",
        "decision_match": verification.get("actual_wsta198_decision") == verification.get("expected_wsta198_decision") == wsta198.LIVE_PASS_DECISION,
        "seccomp_loaded": verification.get("seccomp_filter_loaded") is True,
        "seccomp_enforced": verification.get("seccomp_enforced") is True,
        "fresh_health_checked": verification.get("fresh_native_health_checked") is True,
        "post_health_checked": verification.get("post_run_native_health_checked") is True,
        "cleanup_checked": verification.get("post_run_cleanup_checked") is True,
        "token_value_not_included": verification.get("token_value_included") is False,
        "correct_token_not_in_artifact": verification.get("correct_wsta161_token_in_artifact") is False,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": wsta198.no_external_network_inputs(serialized),
        "secret_values_zero": verification.get("secret_values_logged") == 0,
        "public_url_not_logged": verification.get("public_url_value_logged") is False,
    }


def verifier_markdown(verifier: dict[str, Any]) -> str:
    lines = [
        "# WSTA198 Live Result Verifier",
        "",
        f"- State: `{verifier.get('state')}`",
        f"- Audit current: `{str(verifier.get('audit_current')).lower()}`",
        f"- Ready for post-live verification: `{str(verifier.get('ready_for_post_live_verification')).lower()}`",
        f"- Ready for immediate live execute: `{str(verifier.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Token env present: `{str(verifier.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(verifier.get('private_token_matches_wsta161')).lower()}`",
        f"- Verifier script: `{verifier.get('verifier_script')}`",
        f"- Recommended next action: `{verifier.get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
        "WSTA204 emits and runs only host-side verification logic. It does not execute the WSTA200 handoff or WSTA198 live canary.",
        "",
    ]
    return "\n".join(lines)


def classify_source(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_emit_gate", "wsta204-blocked-explicit-emit-gate-required"),
        ("private_run_dir", "wsta204-blocked-nonprivate-run-dir"),
        ("audit_private", "wsta204-blocked-audit-nonprivate"),
        ("audit_present", "wsta204-blocked-audit-missing"),
        ("audit_valid", result.get("audit_error") or "wsta204-blocked-audit-invalid"),
        ("wsta203_recheck_valid", "wsta204-blocked-wsta203-recheck-invalid"),
        ("audit_stable_view_match", "wsta204-blocked-audit-drift"),
        ("live_result_verifier_valid", "wsta204-blocked-live-result-verifier-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return SOURCE_PASS_DECISION


def classify_verify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("explicit_verify_gate", "wsta204-blocked-explicit-verify-gate-required"),
        ("private_run_dir", "wsta204-blocked-nonprivate-run-dir"),
        ("audit_private", "wsta204-blocked-audit-nonprivate"),
        ("audit_present", "wsta204-blocked-audit-missing"),
        ("audit_valid", result.get("audit_error") or "wsta204-blocked-audit-invalid"),
        ("wsta198_live_result_private", "wsta204-blocked-live-result-nonprivate"),
        ("wsta198_live_result_present", "wsta204-blocked-live-result-missing"),
        ("wsta198_live_result_valid", result.get("live_result_error") or "wsta204-blocked-live-result-invalid"),
        ("live_result_verification_valid", "wsta204-blocked-live-result-verification-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return VERIFY_PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta204-wsta198-live-result-verifier-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    audit_path = resolve_path(args.source_wsta203_audit_json)
    verifying = bool(args.verify_wsta204_live_result)
    result: dict[str, Any] = {
        "scope": "WSTA204 host-only WSTA198 live-result verifier",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "source_wsta203_audit_json": rel(audit_path),
        "wsta198_live_result_json": rel(resolve_path(args.wsta198_live_result_json)) if args.wsta198_live_result_json else None,
        "safety": safety_flags(),
        "checks": {
            "explicit_emit_gate": bool(args.emit_wsta204_live_result_verifier),
            "explicit_verify_gate": verifying,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "audit_private": wsta160.is_under(audit_path, PRIVATE_ROOT),
            "audit_present": audit_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify_verify(result) if verifying else classify_source(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    if verifying:
        live_path = resolve_path(args.wsta198_live_result_json or "")
        result["checks"]["wsta198_live_result_private"] = wsta160.is_under(live_path, PRIVATE_ROOT)
        result["checks"]["wsta198_live_result_present"] = live_path.is_file()
    for key in ("audit_private", "audit_present"):
        if not result["checks"][key]:
            result["decision"] = classify_verify(result) if verifying else classify_source(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result
    if not verifying and not result["checks"]["explicit_emit_gate"]:
        result["decision"] = classify_source(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if verifying and not result["checks"]["explicit_verify_gate"]:
        result["decision"] = classify_verify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    valid, decision, audit_info = validate_audit_payload(audit_path)
    result["audit_checks"] = audit_info.get("checks", {})
    result["checks"]["audit_valid"] = valid
    result["audit_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify_verify(result) if verifying else classify_source(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    if verifying:
        live_path = resolve_path(args.wsta198_live_result_json or "")
        if not (result["checks"]["wsta198_live_result_private"] and result["checks"]["wsta198_live_result_present"]):
            result["decision"] = classify_verify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result
        live_valid, live_decision, live_info = validate_live_result_payload(live_path, audit_info["audit"])
        result["live_result_checks"] = live_info.get("checks", {})
        result["checks"]["wsta198_live_result_valid"] = live_valid
        result["live_result_error"] = None if live_valid else live_decision
        if not live_valid:
            result["decision"] = classify_verify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result
        verification_json = run_dir / "wsta204_wsta198_live_result_verification.json"
        verification = build_live_verification(live_path, audit_info["audit"], live_info, verification_json)
        result["live_result_verification_checks"] = validate_live_verification(verification)
        result["checks"]["live_result_verification_valid"] = all(result["live_result_verification_checks"].values())
        result["live_result_verification"] = verification
        if result["checks"]["live_result_verification_valid"]:
            write_json(verification_json, result)
        result["decision"] = classify_verify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    recheck_dir = run_dir / "wsta203-recheck"
    recheck_result = wsta203.run(wsta203_recheck_args(recheck_dir, audit_info["source_preflight"]))
    result["safety"]["wsta203_recheck_executed"] = True
    result["wsta203_recheck"] = {
        "run_dir": rel(recheck_dir),
        "result_json": rel(recheck_dir / wsta203.SUMMARY_NAME),
        "audit_json": rel(recheck_dir / wsta203.AUDIT_JSON_NAME),
        "decision": recheck_result.get("decision"),
    }
    result["wsta203_recheck_checks"] = validate_recheck(recheck_result)
    result["checks"]["wsta203_recheck_valid"] = all(result["wsta203_recheck_checks"].values())
    result["checks"]["audit_stable_view_match"] = bool(
        result["checks"]["wsta203_recheck_valid"]
        and stable_audit_view(audit_info["audit"]) == stable_audit_view(recheck_result["wrapper_manifest_audit"])
    )
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not (result["checks"]["wsta203_recheck_valid"] and result["checks"]["audit_stable_view_match"]):
        result["decision"] = classify_source(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    verifier_json = run_dir / VERIFIER_JSON_NAME
    verifier_sh = run_dir / VERIFIER_SH_NAME
    verifier_md = run_dir / VERIFIER_MD_NAME
    script_text = verifier_script(audit_path)
    verifier = build_verifier(
        audit_path,
        audit_info["audit"],
        recheck_result,
        recheck_dir / wsta203.SUMMARY_NAME,
        result["token_checks"],
        verifier_json,
        verifier_sh,
        verifier_md,
    )
    result["live_result_verifier_checks"] = validate_verifier(verifier, script_text)
    result["checks"]["live_result_verifier_valid"] = all(result["live_result_verifier_checks"].values())
    result["live_result_verifier"] = verifier
    if result["checks"]["live_result_verifier_valid"]:
        write_json(verifier_json, result)
        write_text(verifier_sh, script_text)
        verifier_sh.chmod(0o700)
        write_text(verifier_md, verifier_markdown(verifier))
    result["decision"] = classify_source(result)
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--source-wsta203-audit-json", type=Path, default=DEFAULT_WSTA203_AUDIT_JSON)
    parser.add_argument("--wsta198-live-result-json", type=Path)
    parser.add_argument("--emit-wsta204-live-result-verifier", action="store_true")
    parser.add_argument("--verify-wsta204-live-result", action="store_true")
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
        payload = {"decision": "wsta204-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") in (SOURCE_PASS_DECISION, VERIFY_PASS_DECISION) else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
