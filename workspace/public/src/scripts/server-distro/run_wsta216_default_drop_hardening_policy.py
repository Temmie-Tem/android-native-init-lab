#!/usr/bin/env python3
"""WSTA216 host-only legacy-iptables default-drop hardening policy.

Consumes the current WSTA215 operator status plus the WSTA94 packet-filter live
proof and the packet-filter control-plane summary.  Emits a deterministic
D-public hardening policy that selects the already-proven legacy-iptables
loopback default-drop path as the next explicit/default-off containment lever.

This unit is host-only.  It does not touch the device, flash, reboot, connect
Wi-Fi, run DHCP, open a public tunnel, mutate packet filters, write userdata,
switch root, mount a rootfs, or load an LSM profile.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta76_persistent_launch_brief as wsta76  # noqa: E402
import run_wsta79_persistent_operator_packet_status as wsta79  # noqa: E402
import run_wsta108_operator_server_status as wsta108  # noqa: E402
import run_wsta94_packet_filter_live_gate as wsta94  # noqa: E402


REPO_ROOT = wsta108.REPO_ROOT
PRIVATE_ROOT = wsta108.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta108.DEFAULT_RUN_BASE
DEFAULT_WSTA215_OPERATOR_STATUS = (
    DEFAULT_RUN_BASE
    / "wsta215-operator-status-apparmor-feasibility-20260705T2220KST"
    / "wsta108_operator_server_status.json"
)
DEFAULT_WSTA94_PACKET_FILTER_PROOF = (
    DEFAULT_RUN_BASE
    / "wsta94-packet-filter-live-20260704T143227Z"
    / "wsta94_result.json"
)
DEFAULT_PACKET_FILTER_CONTROL_SUMMARY = (
    DEFAULT_RUN_BASE
    / "packet-filter-control-ssh-live-20260704T160025Z"
    / "packet_filter_control_summary.json"
)
DEFAULT_SOURCE_PATHS = (
    SCRIPT_DIR / "run_wsta42_native_uplink_dpublic_tunnel.py",
    SCRIPT_DIR / "run_wsta76_persistent_launch_brief.py",
    SCRIPT_DIR / "run_wsta79_persistent_operator_packet_status.py",
    SCRIPT_DIR / "run_wsta80_persistent_operator_execute_gate.py",
)
PASS_DECISION = "wsta216-default-drop-hardening-policy-source-pass"
POLICY_SCHEMA = "a90-wsta216-legacy-iptables-default-drop-hardening-policy-v1"
POLICY_STATE = "LEGACY_IPTABLES_DEFAULT_DROP_HARDENING_POLICY_DEFINED"
POLICY_NAME = "wsta216_default_drop_hardening_policy.json"
SUMMARY_NAME = "wsta216_result.json"
MARKDOWN_NAME = "wsta216_default_drop_hardening_policy.md"
APPARMOR_STATE = "APPARMOR_NOT_AVAILABLE_UNDER_CURRENT_EVIDENCE"
REQUIRED_NEXT_ACTIONS = (
    "continue-containment-hardening-with-legacy-iptables-default-drop",
    "move-to-legacy-iptables-default-drop-hardening",
)
REQUIRED_SEQUENCE = [
    "preflight-helper",
    "save-existing-rules-before-mutation",
    "local-loopback-smoke-before-apply",
    "apply-loopback-default-drop-before-public-exposure",
    "verify-usb-control-plane-preserved",
    "restore-exact-rules-before-public-off-success",
    "cleanup-runtime-services",
]
RESTORE_ON = ["manual-stop", "retire", "failure-cleanup"]


def rel(path: Path) -> str:
    return wsta108.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta108.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
        "wifi_association": False,
        "dhcp": False,
        "ping": False,
        "public_tunnel": False,
        "public_smoke": False,
        "packet_filter_mutation": False,
        "userdata_touch": False,
        "switch_root": False,
        "rootfs_mutation": False,
        "lsm_profile_load": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "policy": result.get("policy", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def get_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def parsed_probe(result: dict[str, Any]) -> dict[str, Any]:
    probe = get_dict(result, "packet_filter_probe")
    parsed = probe.get("parsed")
    return parsed if isinstance(parsed, dict) else {}


def marker_present(result: dict[str, Any], marker: str) -> bool:
    probe = get_dict(result, "packet_filter_probe")
    return marker in str(probe.get("stdout") or "")


def validate_operator_status(status: dict[str, Any]) -> dict[str, bool]:
    server_status = get_dict(status, "server_status")
    exposure = get_dict(server_status, "exposure")
    packet_filter = get_dict(server_status, "packet_filter")
    hardening = get_dict(server_status, "hardening")
    packet_proof = get_dict(hardening, "packet_filter_proof")
    control = get_dict(packet_proof, "control_proof")
    apparmor = get_dict(hardening, "apparmor_feasibility")
    next_actions = set(str(item) for item in server_status.get("operator_next_actions") or [])
    checks = get_dict(status, "checks")
    return {
        "decision_pass": status.get("decision") == wsta108.PASS_DECISION,
        "public_state_off": exposure.get("public_state") == "PUBLIC_OFF",
        "default_public_off": exposure.get("default_public_off") is True,
        "packet_filter_ready": packet_filter.get("ready") is True,
        "packet_filter_state_ready": packet_filter.get("state") in {
            "READY",
            "PACKET_FILTER_REQUIRED_DEFAULT_OFF",
        },
        "packet_filter_proof_state": (
            packet_proof.get("state") == "PACKET_FILTER_LOOPBACK_AND_CONTROL_PLANE_LIVE_PROVEN"
        ),
        "packet_filter_backend_legacy_iptables": packet_proof.get("backend") == wsta76.PACKET_FILTER_BACKEND,
        "packet_filter_policy_loopback_default_drop": packet_proof.get("policy") == wsta76.PACKET_FILTER_POLICY,
        "packet_filter_loopback_live_proven": packet_proof.get("loopback_live_proven") is True,
        "packet_filter_control_plane_live_proven": control.get("control_plane_live_proven") is True,
        "packet_filter_restore_exact": packet_proof.get("restore_exact") is True,
        "packet_filter_final_selftest_fail_zero": packet_proof.get("final_selftest_fail_zero") is True,
        "control_session_after_apply": control.get("control_session_after_apply") is True,
        "control_cleanup_ok": control.get("cleanup_ok") is True,
        "apparmor_unavailable": apparmor.get("state") == APPARMOR_STATE
        and apparmor.get("apparmor_unavailable_under_current_evidence") is True,
        "apparmor_profile_load_disabled": apparmor.get("profile_load_allowed") is False,
        "preferred_hardening_lever": (
            apparmor.get("preferred_current_hardening_lever")
            == "legacy-iptables-loopback-default-drop"
        ),
        "required_next_actions_present": set(REQUIRED_NEXT_ACTIONS).issubset(next_actions),
        "ambiguous_apparmor_next_actions_retired": not any(
            "nftables-or-apparmor" in str(item) for item in next_actions
        ),
        "status_checks_agree": checks.get("packet_filter_loopback_live_proven") is True
        and checks.get("packet_filter_control_plane_live_proven") is True
        and checks.get("preferred_hardening_lever_legacy_iptables") is True,
        "redaction_clean": not bool(wsta108.redaction_findings(status)),
    }


def validate_wsta94_proof(proof: dict[str, Any]) -> dict[str, bool]:
    checks = get_dict(proof, "checks")
    parsed = parsed_probe(proof)
    return {
        "decision_pass": proof.get("decision") == wsta94.PASS_DECISION,
        "preflight_pass": checks.get("packet_filter_preflight_pass") is True
        and parsed.get("preflight_pass") is True,
        "apply_pass": checks.get("packet_filter_apply_pass") is True
        and parsed.get("apply_pass") is True,
        "default_drop_observed": checks.get("packet_filter_default_drop_observed") is True,
        "loopback_before_after_ok": checks.get("loopback_before_ok") is True
        and checks.get("loopback_after_ok") is True
        and parsed.get("loopback_before_ok") is True
        and parsed.get("loopback_after_ok") is True,
        "v4_v6_default_drop": parsed.get("v4_input_drop") is True
        and parsed.get("v4_forward_drop") is True
        and parsed.get("v6_input_drop") is True,
        "loopback_accept": parsed.get("v4_loopback_accept") is True
        and parsed.get("v6_loopback_accept") is True,
        "restore_exact": checks.get("packet_filter_restore_exact") is True
        and parsed.get("restore_exact_v4") is True
        and parsed.get("restore_exact_v6") is True,
        "restore_pass": checks.get("packet_filter_restore_pass") is True
        and parsed.get("restore_pass") is True,
        "cleanup_and_health": checks.get("chroot_cleanup_ok") is True
        and checks.get("final_selftest_fail_zero") is True,
        "backend_marker": marker_present(proof, "packet_filter_backend=legacy-iptables"),
        "policy_marker": marker_present(proof, "packet_filter_policy_class=loopback-default-drop"),
        "established_related_rule_observed": marker_present(
            proof,
            "-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
        ),
        "no_public_url_or_secrets": checks.get("public_url_value_logged") is False
        and checks.get("secret_values_logged") in (0, "0", None),
    }


def validate_control_summary(summary: dict[str, Any]) -> dict[str, bool]:
    preflight = get_dict(summary, "packet_filter_preflight_parsed")
    apply_result = get_dict(summary, "packet_filter_apply_loopback_default_drop_parsed")
    return {
        "preflight_rc_zero": summary.get("packet_filter_preflight_rc") == 0,
        "preflight_backend_legacy_iptables": preflight.get("packet_filter_backend") == wsta76.PACKET_FILTER_BACKEND,
        "preflight_policy_loopback_default_drop": (
            preflight.get("packet_filter_policy_class") == wsta76.PACKET_FILTER_POLICY
        ),
        "preflight_no_autostart": preflight.get("packet_filter_apply_autostart") == "0",
        "apply_rc_zero": summary.get("packet_filter_apply_loopback_default_drop_rc") == 0,
        "apply_decision": (
            apply_result.get("packet_filter_decision")
            == "packet-filter-loopback-default-drop-applied"
        ),
        "apply_backend_legacy_iptables": apply_result.get("packet_filter_backend") == wsta76.PACKET_FILTER_BACKEND,
        "apply_policy_loopback_default_drop": (
            apply_result.get("packet_filter_policy_class") == wsta76.PACKET_FILTER_POLICY
        ),
        "apply_saved_before": apply_result.get("packet_filter_saved_before") == "1",
        "apply_loopback_accept": apply_result.get("packet_filter_loopback_accept") == "1",
        "apply_default_drop": apply_result.get("packet_filter_input_default") == "DROP"
        and apply_result.get("packet_filter_forward_default") == "DROP"
        and apply_result.get("packet_filter_output_default") == "ACCEPT",
        "control_ssh_accept_rule": apply_result.get("packet_filter_control_ssh_accept") == "1",
        "restore_rc_zero": summary.get("packet_filter_restore_rc") == 0,
        "restore_ok": summary.get("packet_filter_restore_ok") is True,
        "ssh_before_after_apply": summary.get("ssh_before_marker") is True
        and summary.get("ssh_after_apply_marker") is True,
        "cleanup_ok": summary.get("post_mount_absent") is True
        and summary.get("post_loop_absent") is True
        and summary.get("post_dropbear_absent") is True,
        "secret_values_zero": preflight.get("packet_filter_secret_values_logged") == "0"
        and apply_result.get("packet_filter_secret_values_logged") == "0",
        "redaction_clean": not bool(wsta108.redaction_findings(summary)),
    }


def validate_source_wiring(source_paths: list[Path]) -> dict[str, bool]:
    hardening = wsta76.packet_filter_hardening()
    joined = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
    sequence = set(str(item) for item in hardening.get("required_sequence") or [])
    restore_on = set(str(item) for item in hardening.get("restore_on") or [])
    return {
        "source_paths_present": all(path.is_file() for path in source_paths),
        "wsta76_contract_backend": hardening.get("backend") == wsta76.PACKET_FILTER_BACKEND,
        "wsta76_contract_policy": hardening.get("policy") == wsta76.PACKET_FILTER_POLICY,
        "wsta76_contract_helper": hardening.get("helper_remote_path") == wsta76.PACKET_FILTER_HELPER,
        "wsta76_default_public_off": hardening.get("default_public_off") is True,
        "wsta76_live_execution_false": hardening.get("live_execution_requested") is False,
        "wsta76_restore_on_lifecycle": set(RESTORE_ON).issubset(restore_on),
        "wsta76_required_sequence": {
            "preflight-helper",
            "apply-loopback-default-drop-before-public-exposure",
            "restore-exact-rules-before-public-off-success",
        }.issubset(sequence),
        "wsta79_accepts_contract": wsta79.packet_filter_hardening_ready({"packet_filter_hardening": hardening}),
        "wsta42_applies_before_cloudflared": (
            "result[\"packet_filter_apply\"] = run_packet_filter(args, run_dir, \"apply-loopback-default-drop\")"
            in joined
            and "result[\"cloudflared_start\"] = start_cloudflared(args, run_dir)" in joined
            and joined.find("result[\"packet_filter_apply\"] = run_packet_filter")
            < joined.find("result[\"cloudflared_start\"] = start_cloudflared")
        ),
        "wsta42_restores_in_finally": "finally:" in joined and "run_packet_filter(args, run_dir, \"restore\")" in joined,
        "wsta80_requires_packet_filter_ready": "packet_filter_hardening_ready" in joined,
    }


def build_policy(operator_status_path: Path,
                 wsta94_path: Path,
                 control_summary_path: Path,
                 source_paths: list[Path]) -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "state": POLICY_STATE,
        "hardening_lever": "legacy-iptables-loopback-default-drop",
        "backend": wsta76.PACKET_FILTER_BACKEND,
        "policy": wsta76.PACKET_FILTER_POLICY,
        "helper_remote_path": wsta76.PACKET_FILTER_HELPER,
        "activation": "explicit-operator-gated",
        "default_public_off": True,
        "live_execution_requested": False,
        "public_exposure_precondition": "apply-loopback-default-drop-before-public-exposure",
        "source_evidence": {
            "operator_status": rel(operator_status_path),
            "packet_filter_loopback_live_proof": rel(wsta94_path),
            "packet_filter_control_plane_summary": rel(control_summary_path),
            "source_wiring": [rel(path) for path in source_paths],
        },
        "rules_contract": {
            "input_default": "DROP",
            "forward_default": "DROP",
            "output_default": "ACCEPT",
            "loopback_accept": True,
            "established_related_accept": True,
            "control_plane_accept": True,
        },
        "lifecycle": {
            "required_sequence": REQUIRED_SEQUENCE,
            "restore_on": RESTORE_ON,
            "restore_exact_required": True,
            "apply_before_public_exposure": True,
            "restore_before_public_off_success": True,
            "operator_may_run_live": False,
            "live_gate_required_for_apply": True,
        },
        "proof_basis": {
            "loopback_default_drop_live_proven": True,
            "usb_control_plane_live_proven": True,
            "restore_exact_live_proven": True,
            "final_selftest_fail_zero": True,
            "apparmor_parked": True,
        },
        "retired_alternatives": [
            "nftables-or-apparmor-ambiguity",
            "apparmor-immediate-profile-load",
        ],
        "next_live_use": {
            "allowed_only_inside_existing_dpublic_live_gate": True,
            "requires_attended_operator": True,
            "packet_filter_mutation_by_wsta216": False,
        },
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_policy(policy: dict[str, Any]) -> dict[str, bool]:
    rules = get_dict(policy, "rules_contract")
    lifecycle = get_dict(policy, "lifecycle")
    proof = get_dict(policy, "proof_basis")
    next_live = get_dict(policy, "next_live_use")
    return {
        "schema_ok": policy.get("schema") == POLICY_SCHEMA,
        "state_ok": policy.get("state") == POLICY_STATE,
        "backend_ok": policy.get("backend") == wsta76.PACKET_FILTER_BACKEND,
        "policy_ok": policy.get("policy") == wsta76.PACKET_FILTER_POLICY,
        "helper_ok": policy.get("helper_remote_path") == wsta76.PACKET_FILTER_HELPER,
        "activation_explicit": policy.get("activation") == "explicit-operator-gated",
        "default_public_off": policy.get("default_public_off") is True,
        "no_live_execution": policy.get("live_execution_requested") is False,
        "rules_default_drop": rules.get("input_default") == "DROP"
        and rules.get("forward_default") == "DROP"
        and rules.get("output_default") == "ACCEPT",
        "rules_allow_control_survival": rules.get("loopback_accept") is True
        and rules.get("established_related_accept") is True
        and rules.get("control_plane_accept") is True,
        "required_sequence_complete": lifecycle.get("required_sequence") == REQUIRED_SEQUENCE,
        "restore_on_complete": lifecycle.get("restore_on") == RESTORE_ON,
        "restore_exact_required": lifecycle.get("restore_exact_required") is True,
        "apply_before_public_exposure": lifecycle.get("apply_before_public_exposure") is True,
        "restore_before_public_off_success": lifecycle.get("restore_before_public_off_success") is True,
        "live_gate_required_for_apply": lifecycle.get("live_gate_required_for_apply") is True
        and lifecycle.get("operator_may_run_live") is False,
        "proof_basis_all_true": all(value is True for value in proof.values()),
        "wsta216_does_not_mutate_filters": next_live.get("packet_filter_mutation_by_wsta216") is False,
        "attended_gate_required": next_live.get("requires_attended_operator") is True,
        "redaction_clean": not bool(wsta108.redaction_findings(policy)),
    }


def markdown(policy: dict[str, Any], result: dict[str, Any]) -> str:
    lifecycle = policy.get("lifecycle", {})
    lines = [
        "# WSTA216 Default-Drop Hardening Policy",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- State: `{policy.get('state')}`",
        f"- Hardening lever: `{policy.get('hardening_lever')}`",
        f"- Backend: `{policy.get('backend')}`",
        f"- Policy: `{policy.get('policy')}`",
        "- Device action: `false`",
        "- Packet-filter mutation: `false`",
        "",
        "## Lifecycle",
        "",
        f"- Activation: `{policy.get('activation')}`",
        f"- Default public off: `{str(bool(policy.get('default_public_off'))).lower()}`",
        f"- Live execution requested: `{str(bool(policy.get('live_execution_requested'))).lower()}`",
        f"- Restore exact required: `{str(bool(lifecycle.get('restore_exact_required'))).lower()}`",
        "",
        "## Required Sequence",
        "",
    ]
    for item in lifecycle.get("required_sequence") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Evidence", ""])
    for key, value in policy.get("source_evidence", {}).items():
        if isinstance(value, list):
            lines.append(f"- {key}: `{', '.join(value)}`")
        else:
            lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Checks", ""])
    for key, value in result.get("checks", {}).items():
        lines.append(f"- {key}: `{str(bool(value)).lower()}`")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta216-default-drop-hardening-policy-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    operator_status_path = resolve_path(args.wsta215_operator_status_json)
    wsta94_path = resolve_path(args.wsta94_packet_filter_proof_json)
    control_summary_path = resolve_path(args.packet_filter_control_summary_json)
    source_paths = [resolve_path(path) for path in args.source_path]
    result: dict[str, Any] = {
        "scope": "WSTA216 host-only legacy-iptables default-drop hardening policy",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_default_drop_hardening_policy),
            "private_run_dir": is_under(run_dir, PRIVATE_ROOT),
            "wsta215_operator_status_private": is_under(operator_status_path, PRIVATE_ROOT),
            "wsta94_packet_filter_proof_private": is_under(wsta94_path, PRIVATE_ROOT),
            "packet_filter_control_summary_private": is_under(control_summary_path, PRIVATE_ROOT),
            "source_paths_public": all(is_under(path, REPO_ROOT) for path in source_paths),
            "wsta215_operator_status_present": operator_status_path.is_file(),
            "wsta94_packet_filter_proof_present": wsta94_path.is_file(),
            "packet_filter_control_summary_present": control_summary_path.is_file(),
            "source_paths_present": all(path.is_file() for path in source_paths),
        },
    }
    if not result["checks"]["explicit_gate"]:
        result["decision"] = "wsta216-blocked-explicit-gate-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    for key, decision in [
        ("private_run_dir", "wsta216-blocked-nonprivate-run-dir"),
        ("wsta215_operator_status_private", "wsta216-blocked-wsta215-status-nonprivate"),
        ("wsta94_packet_filter_proof_private", "wsta216-blocked-wsta94-proof-nonprivate"),
        ("packet_filter_control_summary_private", "wsta216-blocked-control-summary-nonprivate"),
        ("source_paths_public", "wsta216-blocked-source-path-outside-repo"),
        ("wsta215_operator_status_present", "wsta216-blocked-wsta215-status-missing"),
        ("wsta94_packet_filter_proof_present", "wsta216-blocked-wsta94-proof-missing"),
        ("packet_filter_control_summary_present", "wsta216-blocked-control-summary-missing"),
        ("source_paths_present", "wsta216-blocked-source-path-missing"),
    ]:
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if result["checks"]["private_run_dir"]:
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    operator_status = load_json(operator_status_path)
    wsta94_proof = load_json(wsta94_path)
    control_summary = load_json(control_summary_path)
    validation = {
        "operator_status": validate_operator_status(operator_status),
        "wsta94_packet_filter": validate_wsta94_proof(wsta94_proof),
        "control_summary": validate_control_summary(control_summary),
        "source_wiring": validate_source_wiring(source_paths),
    }
    result["validation"] = validation
    for section, checks in validation.items():
        result["checks"].update({f"{section}_{key}": value for key, value in checks.items()})
    if not all(all(checks.values()) for checks in validation.values()):
        result["decision"] = "wsta216-blocked-source-evidence-incomplete"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        run_dir.mkdir(parents=True, exist_ok=True)
        write_json(run_dir / SUMMARY_NAME, result)
        return result

    policy = build_policy(operator_status_path, wsta94_path, control_summary_path, source_paths)
    policy_checks = validate_policy(policy)
    result["policy_checks"] = policy_checks
    result["checks"].update({f"policy_{key}": value for key, value in policy_checks.items()})
    result["decision"] = PASS_DECISION if all(policy_checks.values()) else "wsta216-blocked-policy-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["policy"] = {
        "schema": policy.get("schema"),
        "state": policy.get("state"),
        "hardening_lever": policy.get("hardening_lever"),
        "backend": policy.get("backend"),
        "policy": policy.get("policy"),
        "activation": policy.get("activation"),
        "default_public_off": policy.get("default_public_off"),
        "live_execution_requested": policy.get("live_execution_requested"),
        "packet_filter_mutation_by_wsta216": policy.get("next_live_use", {}).get(
            "packet_filter_mutation_by_wsta216"
        ),
    }
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / POLICY_NAME, policy)
    write_text(run_dir / MARKDOWN_NAME, markdown(policy, result))
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta215-operator-status-json", type=Path, default=DEFAULT_WSTA215_OPERATOR_STATUS)
    parser.add_argument("--wsta94-packet-filter-proof-json", type=Path, default=DEFAULT_WSTA94_PACKET_FILTER_PROOF)
    parser.add_argument("--packet-filter-control-summary-json", type=Path, default=DEFAULT_PACKET_FILTER_CONTROL_SUMMARY)
    parser.add_argument("--source-path", type=Path, action="append", default=list(DEFAULT_SOURCE_PATHS))
    parser.add_argument("--emit-default-drop-hardening-policy", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    result = run(args)
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 1


if __name__ == "__main__":
    raise SystemExit(main())
