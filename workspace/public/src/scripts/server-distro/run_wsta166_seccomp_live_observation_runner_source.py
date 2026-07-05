#!/usr/bin/env python3
"""WSTA166 host-only source proof for the seccomp live-observation runner.

Consumes the WSTA165 no-load observation plan and emits the exact remote shell
script shape a later live unit can run inside Debian.  This unit does not
contact the device.  The generated script intentionally covers only no-load
scenarios and must not contain the correct WSTA161 load token.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import shlex
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta165_seccomp_live_observation_plan as wsta165  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA165_PLAN = (
    DEFAULT_RUN_BASE
    / "wsta165-seccomp-live-observation-plan-20260705T1335KST"
    / "wsta165_live_observation_plan.json"
)
PASS_DECISION = "wsta166-seccomp-live-observation-runner-source-pass"
SUMMARY_NAME = "wsta166_result.json"
REMOTE_SCRIPT_NAME = "wsta166_remote_seccomp_observation.sh"
CONTRACT_NAME = "wsta166_live_runner_contract.json"
CORRECT_WSTA161_TOKEN = "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def write_json(path: Path, payload: Any) -> None:
    wsta3.write_json(path, payload)


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
        "host_source_proof_only": True,
        "remote_script_generated": True,
        "remote_script_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_in_script": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "contract": result.get("contract", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def validate_plan(plan: dict[str, Any]) -> dict[str, bool]:
    serialized = json.dumps(plan, sort_keys=True)
    scenarios = plan.get("scenarios", [])
    scenario_names = [item.get("name") for item in scenarios if isinstance(item, dict)]
    return {
        "schema_ok": plan.get("schema") == "a90-wsta165-seccomp-live-observation-plan-v1",
        "host_only_state": plan.get("state") == "HOST_ONLY_PLAN_NOT_EXECUTED",
        "three_scenarios": scenario_names == [
            "no-load-env-gate",
            "load-env-gate-missing-token",
            "load-env-gate-wrong-token",
        ],
        "correct_token_not_supplied": plan.get("correct_wsta161_token_supplied") is False,
        "filter_load_not_expected": plan.get("seccomp_filter_load_expected") is False,
        "enforcement_not_expected": plan.get("seccomp_enforcement_expected") is False,
        "correct_token_literal_absent": CORRECT_WSTA161_TOKEN not in serialized,
        "forbidden_load_attempt_present": "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1" in serialized,
        "wrong_token_placeholder_present": "intentionally-wrong-token" in serialized,
        "secret_values_logged_zero": plan.get("secret_values_logged") == 0,
    }


def env_tokens(env: dict[str, Any]) -> list[str]:
    tokens = []
    for key, value in sorted(env.items()):
        tokens.append(f"{key}={value}")
    return tokens


def remote_script(plan: dict[str, Any]) -> str:
    lines = [
        "#!/bin/sh",
        "set +e",
        "echo A90WSTA166_REMOTE_BEGIN",
        "run_scenario() {",
        "  name=\"$1\"",
        "  shift",
        "  echo \"A90WSTA166_SCENARIO_BEGIN name=$name\"",
        "  /usr/bin/env -i \"$@\" /usr/local/bin/a90-service-launch dpublic-hud /bin/true",
        "  rc=$?",
        "  echo \"A90WSTA166_SCENARIO_RC name=$name rc=$rc\"",
        "  echo \"A90WSTA166_SCENARIO_END name=$name\"",
        "}",
    ]
    for scenario in plan.get("scenarios", []):
        if not isinstance(scenario, dict):
            continue
        name = str(scenario.get("name"))
        env = scenario.get("env", {})
        if not isinstance(env, dict):
            env = {}
        quoted_env = " ".join(shlex.quote(item) for item in env_tokens(env))
        lines.append(f"run_scenario {shlex.quote(name)} {quoted_env}")
    lines.extend([
        "echo A90WSTA166_REMOTE_DONE",
        "",
    ])
    return "\n".join(lines)


def live_runner_contract(plan: dict[str, Any], script_path: Path) -> dict[str, Any]:
    scenarios = [str(item.get("name")) for item in plan.get("scenarios", []) if isinstance(item, dict)]
    return {
        "schema": "a90-wsta166-seccomp-live-observation-runner-source-v1",
        "state": "SOURCE_ONLY_REMOTE_SCRIPT_NOT_EXECUTED",
        "remote_script_artifact": rel(script_path),
        "scenario_names": scenarios,
        "expected_scenario_returncode": 65,
        "correct_wsta161_token_included": False,
        "seccomp_filter_load_expected": False,
        "seccomp_enforcement_expected": False,
        "future_live_gate_flags": [
            "--execute-seccomp-live-observation",
            "--allow-seccomp-live-observation",
            "--ack-no-correct-wsta161-token",
            "--ack-no-seccomp-load",
            "--ack-cleanup-required",
        ],
        "must_validate_for_each_scenario": [
            "expected markers are present",
            "forbidden markers are absent",
            "returncode is 65",
            "A90WSTA161_SECCOMP_LOAD_ATTEMPT=1 is absent",
            "a90_service_launcher_decision=exec is absent",
        ],
        "secret_values_logged": 0,
    }


def validate_script_and_contract(script_text: str, contract: dict[str, Any], plan: dict[str, Any]) -> dict[str, bool]:
    scenario_names = [str(item.get("name")) for item in plan.get("scenarios", []) if isinstance(item, dict)]
    return {
        "script_has_remote_begin": "A90WSTA166_REMOTE_BEGIN" in script_text,
        "script_has_remote_done": "A90WSTA166_REMOTE_DONE" in script_text,
        "script_has_all_scenarios": all(name in script_text for name in scenario_names),
        "script_uses_env_i": "/usr/bin/env -i" in script_text,
        "script_calls_service_launcher": "/usr/local/bin/a90-service-launch dpublic-hud /bin/true" in script_text,
        "script_has_apply_gate": "WSTA163-ALLOW-HELPER-APPLY" in script_text,
        "script_has_load_env_gate": "WSTA164-ALLOW-SECCOMP-LOAD-ENV" in script_text,
        "script_has_wrong_token_placeholder": "intentionally-wrong-token" in script_text,
        "script_correct_token_literal_absent": CORRECT_WSTA161_TOKEN not in script_text,
        "script_no_external_network_inputs": (
            "cloudflared" not in script_text
            and "tunnel" not in script_text
            and "wifi" not in script_text.lower()
            and "dhcp" not in script_text.lower()
        ),
        "contract_schema_ok": contract.get("schema") == "a90-wsta166-seccomp-live-observation-runner-source-v1",
        "contract_source_only": contract.get("state") == "SOURCE_ONLY_REMOTE_SCRIPT_NOT_EXECUTED",
        "contract_correct_token_false": contract.get("correct_wsta161_token_included") is False,
        "contract_load_expected_false": contract.get("seccomp_filter_load_expected") is False,
        "contract_enforcement_expected_false": contract.get("seccomp_enforcement_expected") is False,
        "contract_scenario_count_three": len(contract.get("scenario_names", [])) == 3,
        "contract_secret_values_zero": contract.get("secret_values_logged") == 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta166-seccomp-live-observation-runner-source-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    plan_path = resolve_path(args.wsta165_plan_json)
    result: dict[str, Any] = {
        "scope": "WSTA166 host-only seccomp live-observation runner source proof",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "safety": safety_flags(),
        "checks": {
            "explicit_gate": bool(args.emit_seccomp_live_runner_source_proof),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta165_plan_private": wsta160.is_under(plan_path, PRIVATE_ROOT),
            "wsta165_plan_present": plan_path.is_file(),
        },
    }
    for key, decision in (
        ("explicit_gate", "wsta166-blocked-explicit-gate-required"),
        ("private_run_dir", "wsta166-blocked-nonprivate-run-dir"),
        ("wsta165_plan_private", "wsta166-blocked-wsta165-plan-nonprivate"),
        ("wsta165_plan_present", "wsta166-blocked-wsta165-plan-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            if key.endswith("_present"):
                run_dir.mkdir(parents=True, exist_ok=True)
                write_json(run_dir / SUMMARY_NAME, result)
            return result

    plan = load_json(plan_path)
    plan_checks = validate_plan(plan)
    script_path = run_dir / REMOTE_SCRIPT_NAME
    contract_path = run_dir / CONTRACT_NAME
    script_text = remote_script(plan)
    contract = live_runner_contract(plan, script_path)
    source_checks = validate_script_and_contract(script_text, contract, plan)
    result["wsta165_plan"] = rel(plan_path)
    result["plan_checks"] = plan_checks
    result["source_checks"] = source_checks
    result["contract"] = {
        "contract_artifact": rel(contract_path),
        "remote_script_artifact": rel(script_path),
        "scenario_count": len(contract["scenario_names"]),
        "state": contract["state"],
        "correct_wsta161_token_included": contract["correct_wsta161_token_included"],
        "seccomp_filter_load_expected": contract["seccomp_filter_load_expected"],
        "seccomp_enforcement_expected": contract["seccomp_enforcement_expected"],
    }
    result["checks"].update({f"plan_{key}": value for key, value in plan_checks.items()})
    result["checks"].update({f"source_{key}": value for key, value in source_checks.items()})
    all_ok = all(plan_checks.values()) and all(source_checks.values())
    result["decision"] = PASS_DECISION if all_ok else "wsta166-blocked-source-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["ended_utc"] = utc_stamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_text, encoding="utf-8")
    script_path.chmod(0o755)
    write_json(contract_path, contract)
    write_json(run_dir / SUMMARY_NAME, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta165-plan-json", type=Path, default=DEFAULT_WSTA165_PLAN)
    parser.add_argument("--emit-seccomp-live-runner-source-proof", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta166-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
