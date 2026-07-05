#!/usr/bin/env python3
"""WSTA199 host-only WSTA198 SSH adapter status gate.

Consumes a private WSTA198 adapter packet, re-runs WSTA198 source generation
from the same WSTA197 transport gate, and reports whether the adapter packet is
still current for an attended live run.  WSTA199 never executes the live
canary, never supplies the WSTA161 token to the device, and never performs a
fresh native health check; those remain WSTA198 live responsibilities.
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


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA198_ADAPTER_JSON = (
    DEFAULT_RUN_BASE
    / "wsta198-seccomp-load-canary-ssh-adapter-20260705T172612KST"
    / wsta198.ADAPTER_JSON_NAME
)
PASS_DECISION = "wsta199-wsta198-adapter-status-pass"
SUMMARY_NAME = "wsta199_result.json"
STATUS_JSON_NAME = "wsta199_wsta198_adapter_status.json"
STATUS_MD_NAME = "wsta199_wsta198_adapter_status.md"
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
        "wsta198_recheck_executed": False,
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
        "scope": "WSTA199 host-only WSTA198 adapter status gate",
        "default_mode": "host-only-revalidate-wsta198-adapter-packet",
        "input": "workspace/private/runs/server-distro/<wsta198-run>/wsta198_seccomp_load_canary_ssh_adapter.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta198-adapter-json",
            "workspace/private/runs/server-distro/<wsta198-run>/wsta198_seccomp_load_canary_ssh_adapter.json",
        ],
        "live_execution": "not-run-by-wsta199",
        "private_token_env": wsta193.PRIVATE_TOKEN_ENV,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "adapter_status": result.get("adapter_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def command_text(command: Any) -> str:
    return json.dumps(command, sort_keys=True) if isinstance(command, list) else ""


def no_external_network_inputs(text: str) -> bool:
    return wsta198.no_external_network_inputs(text)


def private_token_status() -> dict[str, bool]:
    value = os.environ.get(wsta193.PRIVATE_TOKEN_ENV)
    return {
        "private_token_env_present": value is not None,
        "private_token_matches_wsta161": value == wsta161.LOAD_TOKEN,
    }


def stable_adapter_view(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": packet.get("schema"),
        "state": packet.get("state"),
        "source_wsta197_transport_gate": packet.get("source_wsta197_transport_gate"),
        "selected_transport": packet.get("selected_transport"),
        "runner": packet.get("runner"),
        "canary_service": packet.get("canary_service"),
        "policy_service": packet.get("policy_service"),
        "launcher_command": packet.get("launcher_command"),
        "single_service_canary": packet.get("single_service_canary"),
        "private_token_env": packet.get("private_token_env"),
        "token_value_included": packet.get("token_value_included"),
        "correct_wsta161_token_supplied": packet.get("correct_wsta161_token_supplied"),
        "token_transport": packet.get("token_transport"),
        "live_command_template": packet.get("live_command_template"),
        "operator_acknowledgements_required": packet.get("operator_acknowledgements_required"),
        "operator_preflight_checks": packet.get("operator_preflight_checks"),
        "abort_conditions": packet.get("abort_conditions"),
        "cleanup_expectations": packet.get("cleanup_expectations"),
        "ready_for_attended_live": packet.get("ready_for_attended_live"),
        "ready_for_unattended_live": packet.get("ready_for_unattended_live"),
        "default_off": packet.get("default_off"),
        "live_execution_requested": packet.get("live_execution_requested"),
        "seccomp_filter_loaded": packet.get("seccomp_filter_loaded"),
        "seccomp_enforced": packet.get("seccomp_enforced"),
        "public_url_value_logged": packet.get("public_url_value_logged"),
        "secret_values_logged": packet.get("secret_values_logged"),
    }


def validate_adapter_payload(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        packet = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta199-blocked-adapter-unreadable", {"error": str(exc)}
    script_path = resolve_path(packet.get("live_command_script", ""))
    script_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
    adapter_checks = wsta198.validate_adapter_packet(packet, script_text)
    transport_gate = resolve_path(packet.get("source_wsta197_transport_gate", ""))
    text = command_text(packet.get("live_command_template")) + "\n" + script_text
    checks = {
        "adapter_private": wsta160.is_under(path, PRIVATE_ROOT),
        "schema_ok": packet.get("schema") == "a90-wsta198-seccomp-load-canary-ssh-adapter-v1",
        "state_default_off": (
            packet.get("state")
            == "READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH"
        ),
        "wsta198_adapter_checks_pass": all(adapter_checks.values()),
        "source_transport_gate_private": wsta160.is_under(transport_gate, PRIVATE_ROOT),
        "source_transport_gate_present": transport_gate.is_file(),
        "live_script_private": wsta160.is_under(script_path, PRIVATE_ROOT),
        "live_script_present": script_path.is_file(),
        "live_script_executable": script_path.is_file() and bool(script_path.stat().st_mode & 0o100),
        "ready_attended_not_unattended": (
            packet.get("ready_for_attended_live") is True
            and packet.get("ready_for_unattended_live") is False
        ),
        "live_not_requested": packet.get("live_execution_requested") is False,
        "command_has_all_ack_flags": all(flag in text for flag in wsta198.ACK_FLAGS),
        "command_targets_wsta198": "run_wsta198_seccomp_load_canary_ssh_adapter.py" in text,
        "script_requires_private_token_env": f"${{{wsta193.PRIVATE_TOKEN_ENV}:?private-token-required}}" in script_text,
        "no_flash_surface": ("native_" + "init_flash.py") not in text,
        "no_token_literal": FORBIDDEN_TOKEN_PREFIX not in text,
        "no_external_network_inputs": no_external_network_inputs(text),
        "secret_values_logged_zero": packet.get("secret_values_logged") == 0,
        "public_url_not_logged": packet.get("public_url_value_logged") is False,
    }
    if not all(checks.values()):
        return False, "wsta199-blocked-adapter-invalid", {
            "packet": packet,
            "adapter_checks": adapter_checks,
            "checks": checks,
            "script_path": rel(script_path) if wsta160.is_under(script_path, REPO_ROOT) else str(script_path),
            "transport_gate": rel(transport_gate) if wsta160.is_under(transport_gate, REPO_ROOT) else str(transport_gate),
        }
    return True, "ok", {
        "packet": packet,
        "adapter_checks": adapter_checks,
        "checks": checks,
        "script_path": script_path,
        "transport_gate": transport_gate,
    }


def wsta198_recheck_args(run_dir: Path, transport_gate: Path) -> argparse.Namespace:
    return argparse.Namespace(
        run_id="wsta199-wsta198-recheck",
        run_dir=run_dir,
        wsta197_transport_gate_json=transport_gate,
        host="127.0.0.1",
        port=31337,
        bridge_host="127.0.0.1",
        bridge_port=31337,
        device_ip="192.168.7.2",
        ssh_port=2222,
        ssh_connect_timeout=8,
        timeout=20.0,
        health_timeout=20.0,
        setup_timeout=120.0,
        cleanup_timeout=90.0,
        execution_timeout=120.0,
        ssh_timeout=30.0,
        sha_timeout=180.0,
        local_image=wsta198.DEFAULT_LOCAL_IMAGE,
        local_image_sha256=wsta198.wsta149.WSTA115_STRACE_IMAGE_SHA256,
        remote_image=wsta198.d1.DEFAULT_REMOTE_IMAGE,
        remote_clean_image=wsta198.DEFAULT_REMOTE_CLEAN_IMAGE,
        mountpoint=wsta198.d1.DEFAULT_MOUNTPOINT,
        emit_wsta198_ssh_adapter_packet=True,
        execute_real_seccomp_load_canary_over_ssh=False,
        allow_correct_wsta161_token=False,
        ack_seccomp_load_risk=False,
        ack_single_service_canary_only=False,
        ack_no_flash_no_reboot=False,
        ack_cleanup_required=False,
        ack_ssh_chroot_transport=False,
        print_template=False,
        print_full_json=False,
    )


def validate_recheck(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {}) if isinstance(result.get("checks"), dict) else {}
    safety = result.get("safety", {}) if isinstance(result.get("safety"), dict) else {}
    adapter = result.get("adapter", {}) if isinstance(result.get("adapter"), dict) else {}
    return {
        "decision_source_pass": result.get("decision") == wsta198.SOURCE_PASS_DECISION,
        "transport_gate_valid": checks.get("wsta197_transport_gate_valid") is True,
        "adapter_packet_valid": checks.get("adapter_packet_valid") is True,
        "adapter_state_default_off": (
            adapter.get("state")
            == "READY_SSH_CHROOT_ADAPTER_DEFAULT_OFF_LIVE_BLOCKED_UNTIL_TOKEN_AND_HEALTH"
        ),
        "no_device_action": safety.get("device_action") is False,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_ssh_transport": safety.get("ssh_chroot_transport") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
    }


def build_status(
    adapter_path: Path,
    old_packet: dict[str, Any],
    recheck_result: dict[str, Any],
    recheck_path: Path,
    token_checks: dict[str, bool],
    out_json: Path,
    out_md: Path,
) -> dict[str, Any]:
    recheck_packet_path = resolve_path(
        recheck_result.get("adapter", {}).get("adapter_json", "")
        if isinstance(recheck_result.get("adapter"), dict)
        else ""
    )
    new_packet = load_json(recheck_packet_path) if recheck_packet_path.is_file() else {}
    recheck_pass = recheck_result.get("decision") == wsta198.SOURCE_PASS_DECISION
    packet_match = bool(
        recheck_pass
        and isinstance(new_packet, dict)
        and stable_adapter_view(old_packet) == stable_adapter_view(new_packet)
    )
    template_match = bool(
        isinstance(new_packet, dict)
        and old_packet.get("live_command_template") == new_packet.get("live_command_template")
    )
    adapter_current = bool(recheck_pass and packet_match)
    token_ready = bool(token_checks.get("private_token_env_present") and token_checks.get("private_token_matches_wsta161"))
    state = "READY_TO_RUN_WSTA198_ATTENDED_LIVE_DEFAULT_OFF" if adapter_current else "STALE_OR_NOT_READY"
    if adapter_current and not token_ready:
        state = "ADAPTER_CURRENT_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF"
    elif recheck_pass and not packet_match:
        state = "DRIFT_RECHECK_REQUIRED"
    return {
        "state": state,
        "adapter_current": adapter_current,
        "ready_for_attended_live_handoff": adapter_current,
        "ready_for_immediate_live_execute": adapter_current and token_ready,
        "private_token_env_present": token_checks.get("private_token_env_present") is True,
        "private_token_matches_wsta161": token_checks.get("private_token_matches_wsta161") is True,
        "wsta198_adapter_json": rel(adapter_path),
        "wsta198_recheck_result": rel(recheck_path),
        "wsta198_recheck_decision": recheck_result.get("decision"),
        "packet_match": packet_match,
        "template_match": template_match,
        "selected_transport": old_packet.get("selected_transport"),
        "canary_service": old_packet.get("canary_service"),
        "live_command_script": old_packet.get("live_command_script"),
        "operator_acknowledgements_required": old_packet.get("operator_acknowledgements_required") or [],
        "operator_preflight_checks": old_packet.get("operator_preflight_checks") or [],
        "abort_conditions": old_packet.get("abort_conditions") or [],
        "cleanup_expectations": old_packet.get("cleanup_expectations") or [],
        "recommended_next_action": (
            "operator-may-run-wsta198-private-shell-wrapper-after-fresh-health"
            if adapter_current and token_ready
            else "supply-private-token-and-run-wsta198-attended-live-wrapper"
            if adapter_current
            else "rerun-wsta198-before-attended-live"
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
        "# WSTA198 SSH Adapter Status",
        "",
        f"- State: `{status.get('state')}`",
        f"- Adapter current: `{str(status.get('adapter_current')).lower()}`",
        f"- Ready for attended live handoff: `{str(status.get('ready_for_attended_live_handoff')).lower()}`",
        f"- Ready for immediate live execute: `{str(status.get('ready_for_immediate_live_execute')).lower()}`",
        f"- Packet match: `{str(status.get('packet_match')).lower()}`",
        f"- Template match: `{str(status.get('template_match')).lower()}`",
        f"- Token env present: `{str(status.get('private_token_env_present')).lower()}`",
        f"- Token matches expected: `{str(status.get('private_token_matches_wsta161')).lower()}`",
        f"- Recommended next action: `{status.get('recommended_next_action')}`",
        "",
        "## Boundary",
        "",
        "WSTA199 does not execute WSTA198 live, does not run native health, and does not pass the token to the device.",
        "",
    ]
    return "\n".join(lines)


def classify(result: dict[str, Any]) -> str:
    checks = result.get("checks", {})
    ordered = (
        ("private_run_dir", "wsta199-blocked-nonprivate-run-dir"),
        ("adapter_private", "wsta199-blocked-adapter-nonprivate"),
        ("adapter_present", "wsta199-blocked-adapter-missing"),
        ("adapter_valid", result.get("adapter_error") or "wsta199-blocked-adapter-invalid"),
        ("wsta198_recheck_valid", "wsta199-blocked-wsta198-recheck-invalid"),
        ("adapter_status_valid", "wsta199-blocked-status-invalid"),
    )
    for key, decision in ordered:
        if not checks.get(key):
            return str(decision)
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta199-wsta198-adapter-status-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    adapter_path = resolve_path(args.wsta198_adapter_json)
    result: dict[str, Any] = {
        "scope": "WSTA199 host-only WSTA198 adapter status gate",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta198_adapter_json": rel(adapter_path),
        "safety": safety_flags(),
        "checks": {
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "adapter_private": wsta160.is_under(adapter_path, PRIVATE_ROOT),
            "adapter_present": adapter_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key in ("adapter_private", "adapter_present"):
        if not result["checks"][key]:
            result["decision"] = classify(result)
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    valid, decision, adapter_info = validate_adapter_payload(adapter_path)
    result["adapter_checks"] = adapter_info.get("checks", {})
    result["wsta198_adapter_packet_checks"] = adapter_info.get("adapter_checks", {})
    result["checks"]["adapter_valid"] = valid
    result["adapter_error"] = None if valid else decision
    write_json(out_path, result)
    if not valid:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    recheck_dir = run_dir / "wsta198-recheck"
    recheck_result = wsta198.run(wsta198_recheck_args(recheck_dir, adapter_info["transport_gate"]))
    result["safety"]["wsta198_recheck_executed"] = True
    result["wsta198_recheck"] = {
        "run_dir": rel(recheck_dir),
        "result_json": rel(recheck_dir / wsta198.SUMMARY_NAME),
        "decision": recheck_result.get("decision"),
    }
    result["wsta198_recheck_checks"] = validate_recheck(recheck_result)
    result["checks"]["wsta198_recheck_valid"] = all(result["wsta198_recheck_checks"].values())
    result["token_checks"] = private_token_status()
    write_json(out_path, result)
    if not result["checks"]["wsta198_recheck_valid"]:
        result["decision"] = classify(result)
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    status_json = run_dir / STATUS_JSON_NAME
    status_md = run_dir / STATUS_MD_NAME
    status = build_status(
        adapter_path,
        adapter_info["packet"],
        recheck_result,
        recheck_dir / wsta198.SUMMARY_NAME,
        result["token_checks"],
        status_json,
        status_md,
    )
    result["adapter_status"] = status
    result["checks"]["adapter_status_valid"] = status.get("state") in (
        "READY_TO_RUN_WSTA198_ATTENDED_LIVE_DEFAULT_OFF",
        "ADAPTER_CURRENT_OPERATOR_TOKEN_REQUIRED_DEFAULT_OFF",
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
    parser.add_argument("--wsta198-adapter-json", type=Path, default=DEFAULT_WSTA198_ADAPTER_JSON)
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
        payload = {"decision": "wsta199-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
