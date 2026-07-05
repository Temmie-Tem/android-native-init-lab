#!/usr/bin/env python3
"""WSTA192 host-only risk charter for a future real seccomp-load rung.

WSTA191 closed the WSTA187/WSTA190 no-load live workflow.  WSTA192 consumes
that live pass plus the WSTA164 load-env contract and writes a separate
higher-risk charter for any future correct-token/seccomp-load work.  It does
not execute a command, contact the device, supply the correct WSTA161 token, or
load/enforce seccomp.
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

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta164_seccomp_load_env_contract_chroot_proof as wsta164  # noqa: E402
import run_wsta190_wsta189_execute_gate as wsta190  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA190_LIVE_RESULT = (
    DEFAULT_RUN_BASE
    / "wsta190-wsta189-execute-gate-live-20260705T162249KST"
    / wsta190.SUMMARY_NAME
)
DEFAULT_WSTA164_CONTRACT = (
    DEFAULT_RUN_BASE
    / "wsta164-seccomp-load-env-contract-chroot-proof-20260705T1329KST"
    / wsta164.SUMMARY_NAME
)
PASS_DECISION = "wsta192-seccomp-load-risk-charter-pass"
SUMMARY_NAME = "wsta192_result.json"
CHARTER_JSON_NAME = "wsta192_seccomp_load_risk_charter.json"
CHARTER_MD_NAME = "wsta192_seccomp_load_risk_charter.md"


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
        "host_charter_only": True,
        "no_load_workflow_mutated": False,
        "live_command_generated": False,
        "live_command_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "correct_wsta161_token_in_artifact": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA192 host-only seccomp-load risk charter",
        "default_mode": "host-only-risk-charter",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-wsta192-seccomp-load-risk-charter",
        ],
        "live_execution": "not-generated-by-wsta192",
        "correct_wsta161_token": "not-supplied",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "charter": result.get("charter", {}),
        "wsta190_checks": result.get("wsta190_checks", {}),
        "wsta164_checks": result.get("wsta164_checks", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def no_mutation_safety(
    safety: dict[str, Any],
    *,
    allow_device_action: bool,
    require_correct_token_key: bool = True,
) -> dict[str, bool]:
    return {
        "boot_flash_false": safety.get("boot_flash") is False,
        "native_reboot_false": safety.get("native_reboot") is False,
        "wifi_connect_false": safety.get("wifi_connect") is False,
        "dhcp_false": safety.get("dhcp") is False,
        "public_tunnel_false": safety.get("public_tunnel") is False,
        "packet_filter_mutation_false": safety.get("packet_filter_mutation") is False,
        "userdata_touch_false": safety.get("userdata_touch") is False,
        "switch_root_false": safety.get("switch_root") is False,
        "seccomp_filter_loaded_false": safety.get("seccomp_filter_loaded") is False,
        "seccomp_enforced_false": safety.get("seccomp_enforced") is False,
        "correct_token_false": (
            safety.get("correct_wsta161_token_supplied") is False
            if require_correct_token_key
            else safety.get("correct_wsta161_token_supplied", False) is False
        ),
        "secret_values_zero": safety.get("secret_values_logged") == 0,
        "device_action_allowed_shape": allow_device_action or safety.get("device_action") is False,
    }


def validate_wsta190_live(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    delegated = payload.get("wsta187_result", {}) if isinstance(payload.get("wsta187_result"), dict) else {}
    delegated_checks = delegated.get("checks", {}) if isinstance(delegated.get("checks"), dict) else {}
    delegated_safety = delegated.get("safety", {}) if isinstance(delegated.get("safety"), dict) else {}
    delegated_no_mutation = no_mutation_safety(delegated_safety, allow_device_action=True)
    top_no_mutation = no_mutation_safety(safety, allow_device_action=True)
    return {
        "decision_live_pass": payload.get("decision") == wsta190.PASS_DECISION,
        "status_valid": checks.get("status_valid") is True,
        "operator_packet_valid": checks.get("operator_packet_valid") is True,
        "execute_gate_valid": checks.get("execute_gate_valid") is True,
        "explicit_live_gate": checks.get("explicit_live_gate") is True,
        "wsta187_result_valid": checks.get("wsta187_result_valid") is True,
        "delegated_decision_pass": delegated.get("decision") == wsta190.wsta189.wsta188.wsta187.PASS_DECISION,
        "delegated_wsta185_execution_valid": delegated_checks.get("wsta185_execution_valid") is True,
        "top_no_mutation": all(top_no_mutation.values()),
        "delegated_no_mutation": all(delegated_no_mutation.values()),
    }


def validate_wsta164_contract(payload: dict[str, Any]) -> dict[str, bool]:
    checks = payload.get("checks", {}) if isinstance(payload.get("checks"), dict) else {}
    proof = payload.get("proof", {}) if isinstance(payload.get("proof"), dict) else {}
    proof_checks = payload.get("proof_checks", {}) if isinstance(payload.get("proof_checks"), dict) else {}
    safety = payload.get("safety", {}) if isinstance(payload.get("safety"), dict) else {}
    no_mutation = no_mutation_safety(safety, allow_device_action=False, require_correct_token_key=False)
    return {
        "decision_pass": payload.get("decision") == wsta164.PASS_DECISION,
        "launcher_has_load_gate": checks.get("launcher_has_wsta164_load_gate") is True,
        "launcher_forwards_load_env": checks.get("launcher_forwards_load_env") is True,
        "launcher_does_not_hardcode_token": checks.get("launcher_does_not_hardcode_wsta161_token") is True,
        "helper_schema_is_wsta161": checks.get("helper_schema_is_wsta161") is True,
        "helper_apply_code_compiled": checks.get("helper_apply_code_compiled") is True,
        "proof_correct_token_not_supplied": proof.get("correct_wsta161_token_supplied") is False,
        "proof_filter_load_disabled": proof.get("filter_load_enabled") is False,
        "proof_seccomp_not_enforced": proof.get("seccomp_enforced") is False,
        "all_proof_checks_true": bool(proof_checks) and all(value is True for value in proof_checks.values()),
        "wrong_token_no_load_attempt": proof_checks.get("wrong_token_no_load_attempt") is True,
        "missing_token_no_load_attempt": proof_checks.get("missing_token_no_load_attempt") is True,
        "no_gate_no_load_attempt": proof_checks.get("no_gate_no_load_attempt") is True,
        "safety_no_mutation": all(no_mutation.values()),
    }


def risk_charter(wsta190_path: Path, wsta164_path: Path, charter_json: Path, charter_md: Path) -> dict[str, Any]:
    return {
        "schema": "a90-wsta192-seccomp-load-risk-charter-v1",
        "state": "READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE",
        "risk_class": "higher-risk-real-seccomp-load",
        "source_wsta190_live_result": rel(wsta190_path),
        "source_wsta164_load_env_contract": rel(wsta164_path),
        "charter_json": rel(charter_json),
        "charter_markdown": rel(charter_md),
        "no_load_workflow": {
            "status": "closed-through-wsta191",
            "must_not_mutate": [
                "WSTA187 no-load orchestrator",
                "WSTA188 no-load operator packet",
                "WSTA189 no-load status",
                "WSTA190 no-load execute gate",
            ],
        },
        "this_unit": {
            "host_only": True,
            "live_command_generated": False,
            "live_command_executed": False,
            "correct_wsta161_token_supplied": False,
            "seccomp_filter_loaded": False,
            "seccomp_enforced": False,
        },
        "required_future_rungs": [
            "WSTA193 host-only correct-token canary source proof with private token injection placeholder only",
            "WSTA194 private operator packet for one-service seccomp-load canary, default-off and not executed",
            "WSTA195 read-only device readiness gate before any load attempt",
            "WSTA196 attended single-service canary load with bounded command and immediate post-run audit",
        ],
        "future_acknowledgements_required": [
            "--execute-real-seccomp-load-canary",
            "--allow-correct-wsta161-token",
            "--ack-seccomp-load-risk",
            "--ack-single-service-canary-only",
            "--ack-no-flash-no-reboot",
            "--ack-cleanup-required",
        ],
        "future_live_guardrails": [
            "separate-script-required-no-wsta190-reuse",
            "fresh-WSTA164-load-env-contract-required",
            "fresh-WSTA191-no-load-live-baseline-required",
            "correct-token-must-stay-private",
            "first-load-must-be-single-service-canary",
            "bounded-timeout-required",
            "post-load-audit-required",
            "stop-on-any-health-regression",
        ],
        "forbidden_in_this_unit": [
            "device contact",
            "boot flash",
            "native reboot",
            "Wi-Fi connect or DHCP",
            "public tunnel",
            "packet-filter mutation",
            "userdata write",
            "switch-root",
            "seccomp load",
            "seccomp enforcement",
            "correct WSTA161 token",
        ],
        "stop_conditions": [
            "WSTA190 live result is not the current pass artifact",
            "WSTA164 load-env contract is not a pass artifact",
            "any input already loaded or enforced seccomp",
            "any input contains a correct-token-supplied marker",
            "future design attempts to reuse the no-load WSTA187/WSTA190 path",
        ],
        "recommended_next_action": "write WSTA193 host-only correct-token canary source proof; do not run live load yet",
        "default_off": True,
        "secret_values_logged": 0,
    }


def validate_charter(charter: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(charter, sort_keys=True)
    return {
        "schema_ok": charter.get("schema") == "a90-wsta192-seccomp-load-risk-charter-v1",
        "state_not_executable": charter.get("state") == "READY_FOR_SEPARATE_SECCOMP_LOAD_DESIGN_NOT_EXECUTABLE",
        "risk_class_real_load": charter.get("risk_class") == "higher-risk-real-seccomp-load",
        "no_load_workflow_closed": charter.get("no_load_workflow", {}).get("status") == "closed-through-wsta191",
        "this_unit_host_only": charter.get("this_unit", {}).get("host_only") is True,
        "this_unit_no_command": charter.get("this_unit", {}).get("live_command_generated") is False,
        "this_unit_no_live": charter.get("this_unit", {}).get("live_command_executed") is False,
        "this_unit_no_correct_token": charter.get("this_unit", {}).get("correct_wsta161_token_supplied") is False,
        "this_unit_no_seccomp_load": charter.get("this_unit", {}).get("seccomp_filter_loaded") is False,
        "this_unit_no_seccomp_enforce": charter.get("this_unit", {}).get("seccomp_enforced") is False,
        "future_rungs_present": len(charter.get("required_future_rungs", [])) == 4,
        "future_requires_correct_token_ack": "--allow-correct-wsta161-token" in charter.get(
            "future_acknowledgements_required", []
        ),
        "guardrail_separate_script": "separate-script-required-no-wsta190-reuse" in charter.get(
            "future_live_guardrails", []
        ),
        "forbids_load_in_this_unit": "seccomp load" in charter.get("forbidden_in_this_unit", []),
        "default_off": charter.get("default_off") is True,
        "secret_values_zero": charter.get("secret_values_logged") == 0,
        "correct_token_literal_absent": "WSTA161-EXPLICIT" not in serialized,
    }


def markdown(charter: dict[str, Any]) -> str:
    lines = [
        "# WSTA192 Seccomp-Load Risk Charter",
        "",
        f"- State: `{charter.get('state')}`",
        f"- Risk class: `{charter.get('risk_class')}`",
        f"- WSTA190 live result: `{charter.get('source_wsta190_live_result')}`",
        f"- WSTA164 contract: `{charter.get('source_wsta164_load_env_contract')}`",
        "- Live command generated: `false`",
        "- Correct WSTA161 token supplied: `false`",
        "- Seccomp loaded/enforced: `false/false`",
        "",
        "## Boundary",
        "",
        "The WSTA187/WSTA190 no-load workflow is closed and must not be reused for a real seccomp-load attempt.",
        "Any correct-token work must be a separate default-off rung with fresh evidence and an attended live gate.",
        "",
        "## Future Rungs",
        "",
    ]
    for item in charter.get("required_future_rungs", []):
        lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## Stop Conditions",
        "",
    ])
    for item in charter.get("stop_conditions", []):
        lines.append(f"- `{item}`")
    lines.extend(["", "This charter is host-only and not executable.", ""])
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta192-seccomp-load-risk-charter-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    wsta190_path = resolve_path(args.wsta190_live_result_json)
    wsta164_path = resolve_path(args.wsta164_load_env_contract_json)
    result: dict[str, Any] = {
        "scope": "WSTA192 host-only seccomp-load risk charter",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.prepare_wsta192_seccomp_load_risk_charter),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta190_live_result_private": wsta160.is_under(wsta190_path, PRIVATE_ROOT),
            "wsta190_live_result_present": wsta190_path.is_file(),
            "wsta164_load_env_contract_private": wsta160.is_under(wsta164_path, PRIVATE_ROOT),
            "wsta164_load_env_contract_present": wsta164_path.is_file(),
        },
    }
    for key, decision in (
        ("explicit_gate", "wsta192-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta192-blocked-nonprivate-run-dir"),
        ("wsta190_live_result_private", "wsta192-blocked-wsta190-live-result-nonprivate"),
        ("wsta190_live_result_present", "wsta192-blocked-wsta190-live-result-missing"),
        ("wsta164_load_env_contract_private", "wsta192-blocked-wsta164-contract-nonprivate"),
        ("wsta164_load_env_contract_present", "wsta192-blocked-wsta164-contract-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if key.endswith("_present"):
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    run_dir.mkdir(parents=True, exist_ok=True)
    wsta190_payload = load_json(wsta190_path)
    wsta164_payload = load_json(wsta164_path)
    wsta190_checks = validate_wsta190_live(wsta190_payload)
    wsta164_checks = validate_wsta164_contract(wsta164_payload)
    charter_json = run_dir / CHARTER_JSON_NAME
    charter_md = run_dir / CHARTER_MD_NAME
    charter = risk_charter(wsta190_path, wsta164_path, charter_json, charter_md)
    charter_checks = validate_charter(charter)
    result["wsta190_live_result_json"] = rel(wsta190_path)
    result["wsta164_load_env_contract_json"] = rel(wsta164_path)
    result["wsta190_checks"] = wsta190_checks
    result["wsta164_checks"] = wsta164_checks
    result["charter_checks"] = charter_checks
    result["charter"] = {
        "charter_json": rel(charter_json),
        "charter_markdown": rel(charter_md),
        "state": charter["state"],
        "risk_class": charter["risk_class"],
        "future_rung_count": len(charter["required_future_rungs"]),
        "live_command_generated": False,
        "correct_wsta161_token_supplied": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "recommended_next_action": charter["recommended_next_action"],
    }
    result["checks"].update({f"wsta190_{key}": value for key, value in wsta190_checks.items()})
    result["checks"].update({f"wsta164_{key}": value for key, value in wsta164_checks.items()})
    result["checks"].update({f"charter_{key}": value for key, value in charter_checks.items()})
    all_ok = all(wsta190_checks.values()) and all(wsta164_checks.values()) and all(charter_checks.values())
    result["decision"] = PASS_DECISION if all_ok else "wsta192-blocked-charter-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    write_json(charter_json, charter)
    write_text(charter_md, markdown(charter))
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta190-live-result-json", type=Path, default=DEFAULT_WSTA190_LIVE_RESULT)
    parser.add_argument("--wsta164-load-env-contract-json", type=Path, default=DEFAULT_WSTA164_CONTRACT)
    parser.add_argument("--prepare-wsta192-seccomp-load-risk-charter", action="store_true")
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
        payload = {"decision": "wsta192-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
