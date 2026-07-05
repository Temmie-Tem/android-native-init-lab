#!/usr/bin/env python3
"""WSTA223 host-only cloudflared egress allowlist live-gate plan.

WSTA222 made the selected egress allowlist hardening layer visible in operator
status.  This unit turns that visible state into a concrete attended-live gate
plan without mutating packet filters.  It consumes the WSTA222 operator status
and WSTA221 policy, then emits the helper operations, live phases, and
acknowledgements that the next runner must implement before any egress
allowlist live attempt.

This unit is host-only.  It does not touch the device, flash, reboot, connect
Wi-Fi, run DHCP, open a public tunnel, run public smoke, mutate packet filters,
write userdata, switch root, mount a rootfs, or load an LSM profile.
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

import run_wsta88_persistent_operator_workflow as wsta88  # noqa: E402
import run_wsta221_cloudflared_egress_allowlist_policy as wsta221  # noqa: E402


REPO_ROOT = wsta88.REPO_ROOT
PRIVATE_ROOT = wsta88.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta88.DEFAULT_RUN_BASE
DEFAULT_WSTA222_OPERATOR_STATUS = (
    DEFAULT_RUN_BASE
    / "wsta222-operator-status-cloudflared-egress-allowlist-20260705T221905KST"
    / "wsta108_operator_server_status.json"
)
DEFAULT_WSTA221_POLICY = (
    DEFAULT_RUN_BASE
    / "wsta221-cloudflared-egress-allowlist-policy-20260705T221840KST"
    / "wsta221_result.json"
)

PASS_DECISION = "wsta223-cloudflared-egress-allowlist-live-gate-plan-source-pass"
PLAN_SCHEMA = "a90-wsta223-cloudflared-egress-allowlist-live-gate-plan-v1"
PLAN_STATE = "CLOUDFLARED_EGRESS_ALLOWLIST_LIVE_GATE_PLANNED"
PLAN_NAME = "wsta223_cloudflared_egress_allowlist_live_gate_plan.json"
SUMMARY_NAME = "wsta223_result.json"
MARKDOWN_NAME = "wsta223_cloudflared_egress_allowlist_live_gate_plan.md"
WSTA108_PASS_DECISION = "wsta108-operator-server-status-source-pass"
REQUIRED_STATUS_ACTIONS = (
    "prepare-attended-cloudflared-egress-allowlist-live-gate",
    "move-to-cloudflared-egress-allowlist-live-gate",
)
REQUIRED_POLICY_REQUIREMENTS = (
    "preflight iptables owner match and rule restore support",
    "derive redacted DNS/TLS egress route in live session",
    "apply egress allowlist only after loopback default-drop is active",
    "prove cloudflared public smoke still works",
    "prove non-cloudflared service traffic is not accidentally opened",
    "prove USB/NCM control plane survives apply",
    "restore exact rules before PUBLIC_OFF success",
)
HELPER_REQUIRED_OPS = (
    "preflight-cloudflared-egress-allowlist",
    "apply-cloudflared-egress-allowlist",
    "status-cloudflared-egress-allowlist",
    "restore",
)
OPERATOR_ACKS = (
    "--ack-packet-filter-mutation",
    "--force-packet-filter-restore-proof",
    "--force-cloudflared-egress-allowlist-proof",
    "--force-control-plane-proof",
    "--force-public-off-proof",
)


def rel(path: Path) -> str:
    return wsta88.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta88.is_under(path, root)


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


def get_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


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
        "live_gate_plan": result.get("live_gate_plan", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_operator_status(status: dict[str, Any]) -> dict[str, bool]:
    server_status = get_dict(status, "server_status")
    exposure = get_dict(server_status, "exposure")
    hardening = get_dict(server_status, "hardening")
    policy = get_dict(hardening, "cloudflared_egress_allowlist_policy")
    checks = get_dict(status, "checks")
    actions = set(str(item) for item in server_status.get("operator_next_actions") or [])
    return {
        "decision_pass": status.get("decision") == WSTA108_PASS_DECISION,
        "public_state_off": exposure.get("public_state") == "PUBLIC_OFF",
        "default_public_off": exposure.get("default_public_off") is True,
        "required_actions_present": set(REQUIRED_STATUS_ACTIONS).issubset(actions),
        "abstract_next_action_retired": (
            "move-to-next-hardening-layer-after-attended-default-drop-live" not in actions
        ),
        "policy_state_visible": policy.get("state") == wsta221.POLICY_STATE,
        "policy_defined_visible": (
            policy.get("cloudflared_egress_allowlist_policy_defined") is True
        ),
        "hardening_lever_visible": policy.get("hardening_lever") == wsta221.HARDENING_LEVER,
        "target_identity_visible": (
            policy.get("target_user") == wsta221.SERVICE_USER
            and policy.get("target_uid") == wsta221.SERVICE_UID
        ),
        "no_live_execution_in_status": policy.get("live_execution_requested") is False,
        "no_packet_filter_mutation_in_status": (
            policy.get("packet_filter_mutation_by_wsta221") is False
        ),
        "owner_match_fail_closed": policy.get("owner_match_fail_closed") is True,
        "preserves_default_drop": policy.get("preserve_existing_default_drop") is True,
        "restore_exact_required": policy.get("restore_exact_required") is True,
        "control_plane_required": policy.get("control_plane_must_survive_apply") is True,
        "checks_agree": (
            checks.get("wsta221_cloudflared_egress_allowlist_policy_supplied") is True
            and checks.get("cloudflared_egress_allowlist_policy_defined") is True
            and checks.get("cloudflared_egress_allowlist_no_live_execution") is True
            and checks.get("cloudflared_egress_allowlist_no_mutation_here") is True
            and checks.get("cloudflared_egress_allowlist_owner_match_fail_closed") is True
            and checks.get("cloudflared_egress_allowlist_preserves_default_drop") is True
        ),
        "redaction_clean": not bool(wsta88.redaction_findings(status)),
    }


def validate_policy(policy_result: dict[str, Any]) -> dict[str, bool]:
    policy = get_dict(policy_result, "policy")
    contract = get_dict(policy, "policy_contract")
    shape = get_dict(policy, "candidate_rule_shape")
    owner = get_dict(shape, "owner_match")
    recomputed = wsta221.validate_policy(policy)
    return {
        "decision_pass": policy_result.get("decision") == wsta221.PASS_DECISION,
        "wsta221_policy_checks_all_true": bool(recomputed)
        and all(value is True for value in recomputed.values()),
        "state_ok": policy.get("state") == wsta221.POLICY_STATE,
        "hardening_lever_ok": policy.get("hardening_lever") == wsta221.HARDENING_LEVER,
        "service_ok": policy.get("service") == wsta221.SERVICE,
        "target_uid_owner_ok": (
            owner.get("uid_owner") == wsta221.SERVICE_UID
            and owner.get("user") == wsta221.SERVICE_USER
        ),
        "output_chain_scoped": shape.get("chain") == "OUTPUT",
        "global_output_unchanged_until_live": (
            shape.get("global_output_default") == "unchanged-until-live-proof"
        ),
        "dns_tls_live_preflight_required": (
            shape.get("allow_dns") == "route-resolved-live-preflight-required"
            and shape.get("allow_tls") == "route-resolved-live-preflight-required"
        ),
        "fail_closed_contract": (
            contract.get("fail_closed_if_owner_match_unavailable") is True
            and contract.get("fail_closed_if_dns_or_tls_route_unresolved") is True
        ),
        "preserve_default_drop_contract": (
            contract.get("preserve_existing_input_default_drop") is True
            and contract.get("apply_after_loopback_default_drop") is True
        ),
        "restore_and_control_plane_contract": (
            contract.get("save_existing_rules_before_mutation") is True
            and contract.get("restore_exact_rules_before_public_off_success") is True
            and contract.get("control_plane_must_survive_apply") is True
        ),
        "requirements_complete": set(REQUIRED_POLICY_REQUIREMENTS).issubset(
            set(str(item) for item in policy.get("next_live_gate_requirements") or [])
        ),
        "no_live_execution_in_policy": policy.get("live_execution_requested") is False,
        "no_packet_filter_mutation_in_policy": (
            policy.get("packet_filter_mutation_by_wsta221") is False
        ),
        "redaction_clean": (
            policy.get("public_url_value_logged") is False
            and policy.get("secret_values_logged") == 0
            and not bool(wsta88.redaction_findings(wsta221.public_summary(policy_result)))
        ),
    }


def build_live_gate_plan(
    operator_status: dict[str, Any],
    policy_result: dict[str, Any],
) -> dict[str, Any]:
    policy = get_dict(policy_result, "policy")
    return {
        "schema": PLAN_SCHEMA,
        "state": PLAN_STATE,
        "source_status": {
            "operator_status_run_dir": operator_status.get("run_dir"),
            "wsta221_policy_run_dir": policy_result.get("run_dir"),
        },
        "service": wsta221.SERVICE,
        "target_identity": {
            "user": wsta221.SERVICE_USER,
            "uid": wsta221.SERVICE_UID,
            "gid": wsta221.SERVICE_GID,
        },
        "backend": "legacy-iptables",
        "hardening_lever": wsta221.HARDENING_LEVER,
        "activation": "attended-explicit-live-gate-after-default-drop",
        "default_public_off": True,
        "live_execution_requested": False,
        "packet_filter_mutation_by_wsta223": False,
        "required_helper_ops": list(HELPER_REQUIRED_OPS),
        "required_operator_acknowledgements": list(OPERATOR_ACKS),
        "required_live_phases": [
            {
                "name": "preflight",
                "must_prove": [
                    "helper version supports cloudflared egress allowlist ops",
                    "legacy iptables owner match is available for uid 3902",
                    "existing default-drop helper preflight still passes",
                    "exact restore snapshot can be created before mutation",
                ],
            },
            {
                "name": "derive-redacted-egress-route",
                "must_prove": [
                    "DNS resolver route exists without logging resolver values",
                    "TLS tunnel egress route is resolved without logging endpoint values",
                    "fail closed when DNS or TLS route cannot be derived",
                ],
            },
            {
                "name": "apply-after-default-drop",
                "must_prove": [
                    "loopback default-drop is active before egress allowlist",
                    "OUTPUT jump is scoped to uid 3902 only",
                    "global OUTPUT default is not widened by this gate",
                    "control-plane SSH/NCM survives apply",
                ],
            },
            {
                "name": "prove-service-and-nonwidening",
                "must_prove": [
                    "cloudflared public smoke still passes",
                    "rules do not add ACCEPT paths for unrelated uid traffic",
                    "public URL values remain private and redacted",
                ],
            },
            {
                "name": "restore-and-public-off",
                "must_prove": [
                    "exact packet-filter rules are restored",
                    "public state returns to PUBLIC_OFF",
                    "final native health remains clean",
                ],
            },
        ],
        "candidate_rule_shape": {
            "entry_chain": "OUTPUT",
            "dedicated_chain": "A90_CLOUDFLARED_EGRESS",
            "owner_match": {"uid_owner": wsta221.SERVICE_UID, "user": wsta221.SERVICE_USER},
            "allow_loopback": True,
            "allow_established_related": True,
            "allow_dns": "route-resolved-live-preflight-required",
            "allow_tls": "route-resolved-live-preflight-required",
            "terminal_for_uid": "REJECT-or-DROP-after-live-preflight",
            "global_output_default": "unchanged-until-live-proof",
        },
        "implementation_targets": [
            "workspace/public/src/scripts/server-distro/a90_dpublic_packet_filter.sh",
            "workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py",
            "workspace/public/src/scripts/server-distro/run_wsta88_persistent_operator_workflow.py",
            "workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py",
        ],
        "blocked_until_source_exists": True,
        "next_source_unit": "add-helper-and-runner-support-for-cloudflared-egress-allowlist-live-gate",
        "policy_requirements": list(policy.get("next_live_gate_requirements") or []),
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_plan(plan: dict[str, Any]) -> dict[str, bool]:
    shape = get_dict(plan, "candidate_rule_shape")
    owner = get_dict(shape, "owner_match")
    phases = plan.get("required_live_phases") if isinstance(plan.get("required_live_phases"), list) else []
    phase_names = {item.get("name") for item in phases if isinstance(item, dict)}
    return {
        "schema_ok": plan.get("schema") == PLAN_SCHEMA,
        "state_ok": plan.get("state") == PLAN_STATE,
        "service_ok": plan.get("service") == wsta221.SERVICE,
        "hardening_lever_ok": plan.get("hardening_lever") == wsta221.HARDENING_LEVER,
        "activation_attended": (
            plan.get("activation") == "attended-explicit-live-gate-after-default-drop"
        ),
        "default_public_off": plan.get("default_public_off") is True,
        "no_live_execution": plan.get("live_execution_requested") is False,
        "no_mutation_here": plan.get("packet_filter_mutation_by_wsta223") is False,
        "helper_ops_complete": set(HELPER_REQUIRED_OPS).issubset(
            set(str(item) for item in plan.get("required_helper_ops") or [])
        ),
        "operator_acks_complete": set(OPERATOR_ACKS).issubset(
            set(str(item) for item in plan.get("required_operator_acknowledgements") or [])
        ),
        "phase_order_complete": {
            "preflight",
            "derive-redacted-egress-route",
            "apply-after-default-drop",
            "prove-service-and-nonwidening",
            "restore-and-public-off",
        }.issubset(phase_names),
        "owner_scoped_output": (
            shape.get("entry_chain") == "OUTPUT"
            and owner.get("uid_owner") == wsta221.SERVICE_UID
            and shape.get("dedicated_chain") == "A90_CLOUDFLARED_EGRESS"
        ),
        "route_fail_closed": (
            shape.get("allow_dns") == "route-resolved-live-preflight-required"
            and shape.get("allow_tls") == "route-resolved-live-preflight-required"
        ),
        "global_output_not_widened": (
            shape.get("global_output_default") == "unchanged-until-live-proof"
        ),
        "blocked_until_source_exists": plan.get("blocked_until_source_exists") is True,
        "redaction_clean": (
            plan.get("public_url_value_logged") is False
            and plan.get("secret_values_logged") == 0
        ),
    }


def markdown(result: dict[str, Any]) -> str:
    plan = get_dict(result, "live_gate_plan")
    checks = get_dict(result, "checks")
    lines = [
        "# WSTA223 Cloudflared Egress Allowlist Live Gate Plan",
        "",
        f"- Decision: `{result.get('decision')}`",
        f"- State: `{plan.get('state')}`",
        f"- Service: `{plan.get('service')}`",
        f"- Hardening lever: `{plan.get('hardening_lever')}`",
        f"- Live execution requested: `{str(bool(plan.get('live_execution_requested'))).lower()}`",
        f"- Packet-filter mutation here: `{str(bool(plan.get('packet_filter_mutation_by_wsta223'))).lower()}`",
        f"- Operator status ready: `{str(bool(checks.get('operator_status_ready'))).lower()}`",
        f"- WSTA221 policy ready: `{str(bool(checks.get('wsta221_policy_ready'))).lower()}`",
        f"- Plan ready: `{str(bool(checks.get('plan_ready'))).lower()}`",
        "",
        "## Required Helper Ops",
        "",
        *[f"- `{item}`" for item in plan.get("required_helper_ops", [])],
        "",
        "## Required Live Phases",
        "",
    ]
    for phase in plan.get("required_live_phases", []):
        if not isinstance(phase, dict):
            continue
        lines.append(f"- `{phase.get('name')}`")
    lines.extend([
        "",
        "This unit is a plan only.  The next source unit must add the helper and runner support before any live packet-filter mutation.",
        "",
    ])
    return "\n".join(lines)


def fail_result(result: dict[str, Any], out_path: Path, decision: str) -> dict[str, Any]:
    result["decision"] = decision
    result["gate_decision"] = decision
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def require_private_file(path_arg: Path, label: str) -> tuple[Path | None, str | None]:
    path = resolve_path(path_arg)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta223-blocked-{label}-nonprivate"
    if not path.is_file():
        return None, f"wsta223-blocked-{label}-missing"
    return path, None


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta223-cloudflared-egress-allowlist-live-gate-plan-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    if not run_dir.is_absolute():
        run_dir = REPO_ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    result: dict[str, Any] = {
        "scope": "WSTA223 host-only cloudflared egress allowlist live-gate plan",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "gate_decision": "source-gate" if args.emit_live_gate_plan else "blocked",
        "safety": safety_flags(),
        "checks": {},
    }

    if not args.emit_live_gate_plan:
        return fail_result(result, out_path, "wsta223-blocked-explicit-gate-required")
    if not is_under(run_dir, PRIVATE_ROOT):
        return fail_result(result, out_path, "wsta223-blocked-nonprivate-run-dir")

    status_path, status_error = require_private_file(args.wsta222_operator_status_json, "wsta222-operator-status")
    policy_path, policy_error = require_private_file(args.wsta221_policy_json, "wsta221-policy")
    for error in (status_error, policy_error):
        if error:
            return fail_result(result, out_path, error)
    assert status_path is not None
    assert policy_path is not None

    operator_status = load_json(status_path)
    policy_result = load_json(policy_path)
    operator_checks = validate_operator_status(operator_status)
    policy_checks = validate_policy(policy_result)
    plan = build_live_gate_plan(operator_status, policy_result)
    plan_checks = validate_plan(plan)
    result["live_gate_plan"] = plan
    result["checks"] = {
        **{f"operator_{key}": value for key, value in operator_checks.items()},
        **{f"policy_{key}": value for key, value in policy_checks.items()},
        **{f"plan_{key}": value for key, value in plan_checks.items()},
        "operator_status_ready": all(operator_checks.values()),
        "wsta221_policy_ready": all(policy_checks.values()),
        "plan_ready": all(plan_checks.values()),
    }
    if not result["checks"]["operator_status_ready"]:
        return fail_result(result, out_path, "wsta223-blocked-operator-status-incomplete")
    if not result["checks"]["wsta221_policy_ready"]:
        return fail_result(result, out_path, "wsta223-blocked-wsta221-policy-incomplete")
    if not result["checks"]["plan_ready"]:
        return fail_result(result, out_path, "wsta223-blocked-plan-incomplete")

    findings = wsta88.redaction_findings(public_summary(result)) + wsta88.redaction_findings(markdown(result))
    if findings:
        result["gate_detail"] = {"findings": sorted(set(findings))}
        return fail_result(result, out_path, "wsta223-blocked-redaction-finding")

    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"
    result["ended_utc"] = utc_stamp()
    write_json(run_dir / PLAN_NAME, plan)
    write_json(out_path, result)
    write_text(run_dir / MARKDOWN_NAME, markdown(result))
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--emit-live-gate-plan", action="store_true")
    parser.add_argument("--wsta222-operator-status-json", type=Path, default=DEFAULT_WSTA222_OPERATOR_STATUS)
    parser.add_argument("--wsta221-policy-json", type=Path, default=DEFAULT_WSTA221_POLICY)
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    result = run(args)
    if args.print_full_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(public_summary(result), indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


if __name__ == "__main__":
    raise SystemExit(main_with_args())
