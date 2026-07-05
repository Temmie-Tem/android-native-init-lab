#!/usr/bin/env python3
"""WSTA196 attended runner source for the seccomp-load canary.

Consumes WSTA195 readiness and the WSTA194 private/default-off packet.  The
source-gate mode validates the live-runner shape without contacting the device
or supplying the correct WSTA161 token.  The execution mode remains attended:
it requires explicit acknowledgements, a private token environment variable,
fresh read-only native health checks, single-service scope, and a post-run
health check.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta161_seccomp_loader_gated_apply_helper as wsta161  # noqa: E402
import run_wsta169_seccomp_live_readiness_readonly as wsta169  # noqa: E402
import run_wsta193_seccomp_correct_token_canary_source as wsta193  # noqa: E402
import run_wsta194_seccomp_load_canary_operator_packet as wsta194  # noqa: E402
import run_wsta195_seccomp_load_canary_readiness as wsta195  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA194_OPERATOR_PACKET_JSON = wsta195.DEFAULT_WSTA194_OPERATOR_PACKET_JSON
DEFAULT_WSTA195_READINESS_JSON = (
    DEFAULT_RUN_BASE
    / "wsta195-seccomp-load-canary-readiness-20260705T165710KST"
    / wsta195.READINESS_JSON_NAME
)
SOURCE_GATE_PASS_DECISION = "wsta196-seccomp-load-canary-source-gate-pass"
EXECUTE_PASS_DECISION = "wsta196-seccomp-load-canary-execute-pass"
SUMMARY_NAME = "wsta196_result.json"
SOURCE_GATE_JSON_NAME = "wsta196_seccomp_load_canary_source_gate.json"
SOURCE_GATE_MD_NAME = "wsta196_seccomp_load_canary_source_gate.md"
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


def safety_flags(*, execute_requested: bool) -> dict[str, Any]:
    return {
        "device_action_requested": execute_requested,
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
        "host_source_gate_only": not execute_requested,
        "fresh_native_health_checked": False,
        "post_run_native_health_checked": False,
        "operator_packet_executed": False,
        "live_command_generated": False,
        "live_command_executed": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "post_run_audit_executed": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA196 attended seccomp-load canary runner",
        "default_mode": "blocked-unless-source-gate-or-attended-execute",
        "source_gate_command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-wsta196-seccomp-load-canary-source-gate",
        ],
        "attended_execute_command_shape": [
            "python3",
            rel(Path(__file__).resolve()),
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
        ],
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "correct_wsta161_token": "operator-env-only",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "source_gate": result.get("source_gate", {}),
        "execution": {
            "returncode": result.get("execution", {}).get("returncode"),
            "canary_loaded": result.get("canary_parse", {}).get("loaded_marker"),
            "post_health_ok": result.get("checks", {}).get("post_health_valid"),
        },
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def no_external_network_inputs(text: str) -> bool:
    lowered = text.lower()
    return (
        "cloudflared" not in lowered
        and ("ss" + "id=") not in lowered
        and ("ps" + "k=") not in lowered
        and "try" + "cloudflare.com" not in lowered
        and "http" + "://" not in lowered
        and "https" + "://" not in lowered
    )


def validate_wsta195_readiness(readiness: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(readiness, sort_keys=True)
    return {
        "schema_ok": readiness.get("schema") == "a90-wsta195-seccomp-load-canary-readiness-v1",
        "state_ready_for_design": (
            readiness.get("state") == "READY_FOR_WSTA196_DESIGN_READONLY_NOT_EXECUTABLE"
        ),
        "scope_host_only_packet_readiness": (
            readiness.get("readiness_scope") == "host-only-packet-readiness-not-device-readiness"
        ),
        "canary_service_hud": readiness.get("canary_service") == wsta193.CANARY_SERVICE,
        "policy_service_hud_intent": readiness.get("policy_service") == "dpublic-hud-intent",
        "single_service_canary": readiness.get("single_service_canary") is True,
        "private_token_env_named": readiness.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": readiness.get("token_value_included") is False,
        "correct_token_not_supplied": readiness.get("correct_wsta161_token_supplied") is False,
        "seccomp_not_loaded": readiness.get("seccomp_filter_loaded") is False,
        "seccomp_not_enforced": readiness.get("seccomp_enforced") is False,
        "device_readiness_not_checked": readiness.get("device_readiness_checked") is False,
        "health_check_required_in_wsta196": (
            readiness.get("read_only_native_health_check_required_in_wsta196") is True
        ),
        "ready_for_wsta196_design": readiness.get("ready_for_wsta196_design") is True,
        "not_ready_for_live_execution": readiness.get("ready_for_live_execution") is False,
        "future_runner_self": readiness.get("future_wsta196_runner") == wsta194.FUTURE_WSTA196_RUNNER,
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": no_external_network_inputs(serialized),
        "secret_values_zero": readiness.get("secret_values_logged") == 0,
    }


def validate_wsta194_packet(payload: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any]]:
    payload_checks, packet = wsta195.validate_packet_payload(payload)
    payload_valid = {
        "payload_decision_pass": payload_checks.pop("payload_decision_pass"),
        "operator_packet_object": payload_checks.pop("operator_packet_object"),
    }
    checks = {
        **{f"payload_{key}": value for key, value in payload_valid.items()},
        **payload_checks,
        "launcher_command_is_string_list": (
            isinstance(packet.get("launcher_command"), list)
            and all(isinstance(item, str) for item in packet.get("launcher_command", []))
        ),
        "launcher_command_single_service_hud": packet.get("launcher_command", [])[:2]
        == ["/usr/local/bin/a90-service-launch", wsta193.CANARY_SERVICE],
        "launcher_command_canary_true": packet.get("launcher_command", [None])[-1] == wsta193.CANARY_COMMAND,
    }
    return checks, packet


def explicit_execution_gate(args: argparse.Namespace) -> tuple[bool, str]:
    if not args.execute_real_seccomp_load_canary:
        return False, "wsta196-blocked-explicit-execution-gate-required"
    if not args.allow_correct_wsta161_token:
        return False, "wsta196-blocked-correct-token-allow-required"
    if not args.ack_seccomp_load_risk:
        return False, "wsta196-blocked-seccomp-load-risk-ack-required"
    if not args.ack_single_service_canary_only:
        return False, "wsta196-blocked-single-service-ack-required"
    if not args.ack_no_flash_no_reboot:
        return False, "wsta196-blocked-no-flash-no-reboot-ack-required"
    if not args.ack_cleanup_required:
        return False, "wsta196-blocked-cleanup-ack-required"
    return True, "ok"


def private_token_status() -> dict[str, bool]:
    value = os.environ.get(wsta193.PRIVATE_TOKEN_ENV)
    return {
        "private_token_env_present": value is not None,
        "private_token_matches_wsta161": value == wsta161.LOAD_TOKEN,
    }


def run_readonly_health_checks(timeout: float) -> dict[str, Any]:
    bridge_record = wsta169.run_bridge_status(timeout)
    version_record = wsta169.run_a90ctl("version", timeout)
    status_record = wsta169.run_a90ctl("status", timeout)
    selftest_record = wsta169.run_a90ctl("selftest", timeout)
    bridge_parse = wsta169.parse_bridge(bridge_record)
    version_parse = wsta169.parse_a90ctl_text(str(version_record.get("stdout") or ""))
    status_parse = wsta169.parse_a90ctl_text(str(status_record.get("stdout") or ""))
    selftest_parse = wsta169.parse_a90ctl_text(str(selftest_record.get("stdout") or ""))
    checks = {
        "bridge_ready": (
            bridge_record.get("returncode") == 0
            and bridge_parse["bridge_process_running"]
            and bridge_parse["port_listening"]
            and bridge_parse["probe_connected"]
            and bridge_parse["selected_device_present"]
            and bridge_parse["selected_realpath_present"]
        ),
        "version_ok": version_record.get("returncode") == 0 and version_parse["version_present"],
        "status_ok": (
            status_record.get("returncode") == 0
            and status_parse["selftest_fail_zero"]
            and status_parse["transport_ncm_ready"]
            and status_parse["storage_sd_mounted"]
            and status_parse["runtime_sd"]
        ),
        "selftest_fail_zero": selftest_record.get("returncode") == 0 and selftest_parse["selftest_fail_zero"],
    }
    return {
        "bridge_status": bridge_record,
        "version": version_record,
        "status": status_record,
        "selftest": selftest_record,
        "readiness": {
            "bridge": bridge_parse,
            "version": version_parse,
            "status": status_parse,
            "selftest": selftest_parse,
        },
        "checks": checks,
    }


def canary_environment(token: str) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "A90_SERVICE_LAUNCH_SECCOMP_DRY_RUN": "1",
        "A90_SERVICE_LAUNCH_SECCOMP_ENFORCE": "1",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_MODE": "apply",
        "A90_SERVICE_LAUNCH_SECCOMP_HELPER_APPLY_GATE": "WSTA163-ALLOW-HELPER-APPLY",
        "A90_SERVICE_LAUNCH_SECCOMP_LOAD_GATE": "WSTA164-ALLOW-SECCOMP-LOAD-ENV",
        "A90_SERVICE_LAUNCH_SECCOMP_LOAD_TOKEN": token,
    })
    return env


def run_canary_command(command: list[str], *, env: dict[str, str], timeout: float) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
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


def parse_canary_output(record: dict[str, Any]) -> dict[str, bool]:
    text = str(record.get("stdout") or "") + "\n" + str(record.get("stderr") or "")
    return {
        "returncode_bounded": record.get("returncode") in (0, 65),
        "load_attempt_marker": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" in text,
        "loaded_marker": "a90_seccomp_loader_decision=loaded" in text
        or "A90WSTA161_SECCOMP_LOAD=1" in text,
        "apply_ok_marker": "A90WSTA163_SECCOMP_HELPER_APPLY_OK=1" in text
        or "a90_seccomp_loader_decision=loaded" in text,
        "single_service_marker": "A90WSTA154_SECCOMP_SERVICE=dpublic-hud" in text,
        "policy_service_marker": "A90WSTA154_SECCOMP_POLICY_SERVICE=dpublic-hud-intent" in text,
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in text,
        "no_external_network_inputs": no_external_network_inputs(text),
    }


def build_source_gate(run_dir: Path, readiness_json: Path, packet_json: Path, packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "a90-wsta196-seccomp-load-canary-source-gate-v1",
        "state": "LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED",
        "source_wsta195_readiness": rel(readiness_json),
        "source_wsta194_operator_packet": rel(packet_json),
        "source_gate_json": rel(run_dir / SOURCE_GATE_JSON_NAME),
        "source_gate_markdown": rel(run_dir / SOURCE_GATE_MD_NAME),
        "canary_service": packet.get("canary_service"),
        "policy_service": packet.get("policy_service"),
        "launcher_command": packet.get("launcher_command"),
        "single_service_canary": True,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "token_value_included": False,
        "correct_wsta161_token_supplied": False,
        "fresh_native_health_check_required": True,
        "post_run_native_health_check_required": True,
        "ready_for_attended_execution": True,
        "ready_for_unattended_execution": False,
        "execution_path_default_off": True,
        "live_command_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "expected_success_markers": [
            "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1",
            "a90_seccomp_loader_decision=loaded",
        ],
        "required_execute_flags": [
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
        ],
        "post_run_audit": [
            "fresh-native-health-after-canary",
            "verify-single-service-output-markers",
            "stop-on-any-health-regression",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_source_gate(source_gate: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(source_gate, sort_keys=True)
    return {
        "schema_ok": source_gate.get("schema") == "a90-wsta196-seccomp-load-canary-source-gate-v1",
        "state_default_off": source_gate.get("state") == "LIVE_RUNNER_SOURCE_READY_DEFAULT_OFF_NOT_EXECUTED",
        "single_service_canary": source_gate.get("single_service_canary") is True,
        "canary_service_hud": source_gate.get("canary_service") == wsta193.CANARY_SERVICE,
        "policy_service_hud_intent": source_gate.get("policy_service") == "dpublic-hud-intent",
        "private_token_env_named": source_gate.get("private_token_env") == wsta193.PRIVATE_TOKEN_ENV,
        "token_value_not_included": source_gate.get("token_value_included") is False,
        "correct_token_not_supplied": source_gate.get("correct_wsta161_token_supplied") is False,
        "fresh_health_required": source_gate.get("fresh_native_health_check_required") is True,
        "post_health_required": source_gate.get("post_run_native_health_check_required") is True,
        "ready_for_attended_execution": source_gate.get("ready_for_attended_execution") is True,
        "not_unattended": source_gate.get("ready_for_unattended_execution") is False,
        "default_off": source_gate.get("execution_path_default_off") is True,
        "live_not_executed": source_gate.get("live_command_executed") is False,
        "seccomp_not_loaded": source_gate.get("seccomp_filter_loaded") is False,
        "seccomp_not_enforced": source_gate.get("seccomp_enforced") is False,
        "execute_flags_complete": all(
            flag in source_gate.get("required_execute_flags", [])
            for flag in (
                "--execute-real-seccomp-load-canary",
                "--allow-correct-wsta161-token",
                "--ack-seccomp-load-risk",
                "--ack-single-service-canary-only",
                "--ack-no-flash-no-reboot",
                "--ack-cleanup-required",
            )
        ),
        "load_markers_present": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" in source_gate.get(
            "expected_success_markers", []
        ),
        "token_literal_absent": FORBIDDEN_TOKEN_PREFIX not in serialized,
        "no_external_network_inputs": no_external_network_inputs(serialized),
        "secret_values_zero": source_gate.get("secret_values_logged") == 0,
        "public_url_not_logged": source_gate.get("public_url_value_logged") is False,
    }


def source_gate_markdown(source_gate: dict[str, Any]) -> str:
    lines = [
        "# WSTA196 Seccomp-Load Canary Source Gate",
        "",
        f"- State: `{source_gate.get('state')}`",
        f"- Canary service: `{source_gate.get('canary_service')}`",
        f"- Private token env: `{source_gate.get('private_token_env')}`",
        f"- Ready for attended execution: `{str(source_gate.get('ready_for_attended_execution')).lower()}`",
        f"- Ready for unattended execution: `{str(source_gate.get('ready_for_unattended_execution')).lower()}`",
        f"- Live command executed: `{str(source_gate.get('live_command_executed')).lower()}`",
        "",
        "## Boundary",
        "",
        "- Source-gate mode does not contact the device.",
        "- Source-gate mode does not supply the correct WSTA161 token.",
        "- Execution mode requires fresh native health before and after the canary.",
        "- Execution mode remains single-service only.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any], *, executing: bool) -> str:
    checks = result.get("checks", {})
    base_order = (
        ("private_run_dir", "wsta196-blocked-nonprivate-run-dir"),
        ("wsta195_readiness_private", "wsta196-blocked-wsta195-readiness-nonprivate"),
        ("wsta194_packet_private", "wsta196-blocked-wsta194-packet-nonprivate"),
        ("wsta195_readiness_present", "wsta196-blocked-wsta195-readiness-missing"),
        ("wsta194_packet_present", "wsta196-blocked-wsta194-packet-missing"),
        ("wsta195_readiness_valid", "wsta196-blocked-wsta195-readiness-invalid"),
        ("wsta194_packet_valid", "wsta196-blocked-wsta194-packet-invalid"),
    )
    for key, decision in base_order:
        if not checks.get(key):
            return decision
    if not executing:
        if not checks.get("explicit_source_gate"):
            return "wsta196-blocked-explicit-source-gate-required"
        if not checks.get("source_gate_valid"):
            return "wsta196-blocked-source-gate-invalid"
        return SOURCE_GATE_PASS_DECISION
    execute_order = (
        ("explicit_execution_gate", "wsta196-blocked-explicit-execution-gate-required"),
        ("private_token_env_present", "wsta196-blocked-private-token-env-missing"),
        ("private_token_matches_wsta161", "wsta196-blocked-private-token-invalid"),
        ("fresh_health_valid", "wsta196-blocked-fresh-health-invalid"),
        ("execution_returncode_bounded", "wsta196-blocked-canary-returncode"),
        ("canary_loaded", "wsta196-blocked-canary-load-not-observed"),
        ("post_health_valid", "wsta196-blocked-post-health-invalid"),
    )
    for key, decision in execute_order:
        if not checks.get(key):
            return decision
    return EXECUTE_PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta196-seccomp-load-canary-source-gate-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    readiness_json = resolve_path(args.wsta195_readiness_json)
    packet_json = resolve_path(args.wsta194_operator_packet_json)
    executing = bool(args.execute_real_seccomp_load_canary)
    execution_gate_ok, execution_gate_decision = explicit_execution_gate(args)
    result: dict[str, Any] = {
        "scope": "WSTA196 attended seccomp-load canary runner",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta195_readiness_json": rel(readiness_json),
        "wsta194_operator_packet_json": rel(packet_json),
        "gate_decision": "source-gate" if args.emit_wsta196_seccomp_load_canary_source_gate else execution_gate_decision,
        "safety": safety_flags(execute_requested=executing),
        "checks": {
            "explicit_source_gate": bool(args.emit_wsta196_seccomp_load_canary_source_gate),
            "explicit_execution_gate": execution_gate_ok,
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta195_readiness_private": wsta160.is_under(readiness_json, PRIVATE_ROOT),
            "wsta194_packet_private": wsta160.is_under(packet_json, PRIVATE_ROOT),
            "wsta195_readiness_present": readiness_json.is_file(),
            "wsta194_packet_present": packet_json.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result, executing=executing)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in (
        "wsta195_readiness_private",
        "wsta194_packet_private",
        "wsta195_readiness_present",
        "wsta194_packet_present",
    ):
        if not result["checks"][key]:
            result["decision"] = classify(result, executing=executing)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    readiness = load_json(readiness_json)
    packet_payload = load_json(packet_json)
    readiness_checks = validate_wsta195_readiness(readiness)
    packet_checks, packet = validate_wsta194_packet(packet_payload)
    result["wsta195_readiness_checks"] = readiness_checks
    result["wsta194_packet_checks"] = packet_checks
    result["checks"]["wsta195_readiness_valid"] = all(readiness_checks.values())
    result["checks"]["wsta194_packet_valid"] = all(packet_checks.values())
    source_gate = build_source_gate(run_dir, readiness_json, packet_json, packet)
    source_gate_checks = validate_source_gate(source_gate)
    result["source_gate_checks"] = source_gate_checks
    result["checks"]["source_gate_valid"] = all(source_gate_checks.values())
    result["source_gate"] = {
        "source_gate_json": rel(run_dir / SOURCE_GATE_JSON_NAME),
        "source_gate_markdown": rel(run_dir / SOURCE_GATE_MD_NAME),
        "state": source_gate["state"],
        "canary_service": source_gate["canary_service"],
        "single_service_canary": True,
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "ready_for_attended_execution": True,
        "ready_for_unattended_execution": False,
        "live_command_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
    }
    if args.emit_wsta196_seccomp_load_canary_source_gate and not executing:
        if result["checks"]["wsta195_readiness_valid"] and result["checks"]["wsta194_packet_valid"]:
            write_json(run_dir / SOURCE_GATE_JSON_NAME, source_gate)
            write_text(run_dir / SOURCE_GATE_MD_NAME, source_gate_markdown(source_gate))
        result["decision"] = classify(result, executing=False)
        result["gate_decision"] = "ok" if result["decision"] == SOURCE_GATE_PASS_DECISION else result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    if not executing:
        result["decision"] = classify(result, executing=False)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    token_checks = private_token_status()
    result["token_checks"] = token_checks
    result["checks"].update(token_checks)
    write_json(out_path, result)
    if (
        not execution_gate_ok
        or not result["checks"]["wsta195_readiness_valid"]
        or not result["checks"]["wsta194_packet_valid"]
        or not result["checks"]["private_token_env_present"]
        or not result["checks"]["private_token_matches_wsta161"]
    ):
        result["decision"] = classify(result, executing=True)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    result["fresh_health"] = run_readonly_health_checks(args.health_timeout)
    result["checks"]["fresh_health_valid"] = all(result["fresh_health"]["checks"].values())
    result["safety"]["fresh_native_health_checked"] = True
    write_json(out_path, result)
    if not result["checks"]["fresh_health_valid"]:
        result["decision"] = classify(result, executing=True)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    token = os.environ[wsta193.PRIVATE_TOKEN_ENV]
    command = packet["launcher_command"]
    result["safety"]["device_action"] = "single-service-seccomp-load-canary"
    result["safety"]["operator_packet_executed"] = True
    result["safety"]["live_command_executed"] = True
    result["safety"]["correct_wsta161_token_supplied"] = True
    result["execution"] = run_canary_command(command, env=canary_environment(token), timeout=args.execution_timeout)
    canary_parse = parse_canary_output(result["execution"])
    result["canary_parse"] = canary_parse
    result["checks"]["execution_returncode_bounded"] = canary_parse["returncode_bounded"]
    result["checks"]["canary_loaded"] = (
        canary_parse["load_attempt_marker"]
        and canary_parse["loaded_marker"]
        and canary_parse["apply_ok_marker"]
        and canary_parse["single_service_marker"]
        and canary_parse["policy_service_marker"]
        and canary_parse["token_literal_absent"]
        and canary_parse["no_external_network_inputs"]
    )
    if result["checks"]["canary_loaded"]:
        result["safety"]["seccomp_filter_loaded"] = True
        result["safety"]["seccomp_enforced"] = True
    result["post_health"] = run_readonly_health_checks(args.health_timeout)
    result["checks"]["post_health_valid"] = all(result["post_health"]["checks"].values())
    result["safety"]["post_run_native_health_checked"] = True
    result["safety"]["post_run_audit_executed"] = True
    result["decision"] = classify(result, executing=True)
    result["gate_decision"] = "ok" if result["decision"] == EXECUTE_PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta195-readiness-json", type=Path, default=DEFAULT_WSTA195_READINESS_JSON)
    parser.add_argument("--wsta194-operator-packet-json", type=Path, default=DEFAULT_WSTA194_OPERATOR_PACKET_JSON)
    parser.add_argument("--health-timeout", type=float, default=20.0)
    parser.add_argument("--execution-timeout", type=float, default=120.0)
    parser.add_argument("--emit-wsta196-seccomp-load-canary-source-gate", action="store_true")
    parser.add_argument("--execute-real-seccomp-load-canary", action="store_true")
    parser.add_argument("--allow-correct-wsta161-token", action="store_true")
    parser.add_argument("--ack-seccomp-load-risk", action="store_true")
    parser.add_argument("--ack-single-service-canary-only", action="store_true")
    parser.add_argument("--ack-no-flash-no-reboot", action="store_true")
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
        payload = {"decision": "wsta196-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") in (SOURCE_GATE_PASS_DECISION, EXECUTE_PASS_DECISION) else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
