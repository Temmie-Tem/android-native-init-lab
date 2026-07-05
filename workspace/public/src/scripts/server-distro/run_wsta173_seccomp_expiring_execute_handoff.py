#!/usr/bin/env python3
"""WSTA173 expiring handoff for the WSTA172 execution command.

Consumes a WSTA172 fresh preflight proof, verifies the generated WSTA171 command
is still fresh and unexecuted, and emits a handoff packet.  This unit does not
execute the command.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for _path in (SCRIPT_DIR, SCRIPT_DIR.parent / "revalidation"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import prepare_wsta3_sta_rootfs as wsta3  # noqa: E402
import run_wsta160_seccomp_full_rootfs_chroot_dry_run as wsta160  # noqa: E402
import run_wsta169_seccomp_live_readiness_readonly as wsta169  # noqa: E402
import run_wsta170_seccomp_live_observation_execute as wsta170  # noqa: E402
import run_wsta171_seccomp_live_observation_execute_preflight as wsta171  # noqa: E402
import run_wsta172_seccomp_fresh_execute_preflight as wsta172  # noqa: E402


REPO_ROOT = wsta3.REPO_ROOT
PRIVATE_ROOT = REPO_ROOT / "workspace/private"
DEFAULT_RUN_BASE = wsta3.DEFAULT_RUN_BASE
DEFAULT_WSTA172_PROOF = (
    DEFAULT_RUN_BASE
    / "wsta172-seccomp-fresh-execute-preflight-20260705T142100KST"
    / "wsta172_result.json"
)
PASS_DECISION = "wsta173-seccomp-expiring-execute-handoff-pass"
SUMMARY_NAME = "wsta173_result.json"
HANDOFF_NAME = "wsta173_expiring_execute_handoff.json"


def rel(path: Path) -> str:
    return wsta3.rel(path)


def utc_stamp() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def parse_utc(value: str | None) -> _dt.datetime | None:
    if not value:
        return None
    try:
        return _dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def format_utc(value: _dt.datetime) -> str:
    return value.astimezone(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path | str) -> Path:
    path_obj = path if isinstance(path, Path) else Path(path)
    return path_obj if path_obj.is_absolute() else REPO_ROOT / path_obj


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
        "handoff_generated": False,
        "wsta170_execute_command_executed": False,
        "live_command_executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "freshness": result.get("freshness", {}),
        "handoff": result.get("handoff", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def path_from_result(result: dict[str, Any], *keys: str) -> Path | None:
    value: Any = result
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    if not isinstance(value, str) or not value:
        return None
    return resolve_path(value)


def validate_wsta172_result(result: dict[str, Any]) -> dict[str, bool]:
    checks = result.get("checks", {})
    safety = result.get("safety", {})
    return {
        "decision_pass": result.get("decision") == wsta172.PASS_DECISION,
        "gate_ok": result.get("gate_decision") == "ok",
        "fresh_readiness_valid": checks.get("fresh_readiness_valid") is True,
        "source_gate_valid": checks.get("source_gate_valid") is True,
        "execute_preflight_valid": checks.get("execute_preflight_valid") is True,
        "no_live_execution": safety.get("live_command_executed") is False,
        "no_seccomp_load": safety.get("seccomp_filter_loaded") is False,
        "no_seccomp_enforce": safety.get("seccomp_enforced") is False,
        "no_correct_token": safety.get("correct_wsta161_token_supplied") is False,
        "command_generated": safety.get("wsta170_execute_command_generated") is True,
        "command_not_executed": safety.get("wsta170_execute_command_executed") is False,
    }


def validate_nested_results(
    readiness: dict[str, Any],
    source_gate: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, bool]:
    readiness_safety = readiness.get("safety", {})
    source_safety = source_gate.get("safety", {})
    preflight_safety = preflight.get("safety", {})
    preflight_command = preflight.get("command", {})
    return {
        "readiness_pass": readiness.get("decision") == wsta169.PASS_DECISION,
        "source_gate_block": source_gate.get("decision") == "wsta170-blocked-explicit-execution-gate-required",
        "preflight_pass": preflight.get("decision") == wsta171.PASS_DECISION,
        "readiness_no_live_execution": readiness_safety.get("live_command_executed") is False,
        "source_no_live_execution": source_safety.get("live_command_executed") is False,
        "preflight_no_live_execution": preflight_safety.get("live_command_executed") is False,
        "readiness_no_seccomp_load": readiness_safety.get("seccomp_filter_loaded") is False,
        "source_no_seccomp_load": source_safety.get("seccomp_filter_loaded") is False,
        "preflight_no_seccomp_load": preflight_safety.get("seccomp_filter_loaded") is False,
        "preflight_command_ready": preflight_command.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "preflight_command_not_executed": preflight_command.get("executed") is False,
    }


def validate_command_payload(payload: dict[str, Any], script_text: str) -> dict[str, bool]:
    command = payload.get("command", [])
    text = " ".join(str(item) for item in command) + script_text
    required = payload.get("required_ack_flags", [])
    expected = payload.get("expected_outcome", {})
    return {
        "schema_ok": payload.get("schema") == "a90-wsta171-wsta170-execute-command-v1",
        "ready_not_executed": payload.get("state") == "READY_TO_RUN_NOT_EXECUTED",
        "not_executed": payload.get("executed") is False,
        "command_is_string_list": isinstance(command, list) and all(isinstance(item, str) for item in command),
        "targets_wsta170": (
            "workspace/public/src/scripts/server-distro/run_wsta170_seccomp_live_observation_execute.py" in command
        ),
        "all_ack_flags_present": all(flag in command and flag in script_text for flag in required),
        "correct_token_absent": "WSTA161-EXPLICIT-ALLOW-SECCOMP-LOAD" not in text,
        "no_external_network_inputs": (
            "cloudflared" not in text and "wifi" not in text.lower() and "dhcp" not in text.lower()
        ),
        "expected_wsta170_pass": expected.get("decision") == wsta170.PASS_DECISION,
        "expected_wsta167_pass": expected.get("nested_decision") == wsta170.wsta167.PASS_DECISION,
        "expected_no_seccomp_load": expected.get("seccomp_filter_loaded") is False,
        "expected_no_seccomp_enforce": expected.get("seccomp_enforced") is False,
        "expected_no_correct_token": expected.get("correct_wsta161_token_supplied") is False,
    }


def validate_freshness(
    wsta172_result: dict[str, Any],
    readiness: dict[str, Any],
    preflight: dict[str, Any],
    max_age_sec: int,
) -> tuple[dict[str, Any], dict[str, bool]]:
    now = now_utc()
    readiness_end = parse_utc(readiness.get("ended_utc"))
    preflight_end = parse_utc(preflight.get("ended_utc"))
    bundle_end = parse_utc(wsta172_result.get("ended_utc"))
    timestamps = [item for item in (readiness_end, preflight_end, bundle_end) if item is not None]
    newest = max(timestamps) if timestamps else None
    oldest = min(timestamps) if timestamps else None
    anchor = readiness_end or bundle_end or preflight_end
    age = int((now - anchor).total_seconds()) if anchor else None
    expires = anchor + _dt.timedelta(seconds=max_age_sec) if anchor else None
    freshness = {
        "now_utc": format_utc(now),
        "readiness_ended_utc": format_utc(readiness_end) if readiness_end else None,
        "preflight_ended_utc": format_utc(preflight_end) if preflight_end else None,
        "bundle_ended_utc": format_utc(bundle_end) if bundle_end else None,
        "age_sec": age,
        "max_age_sec": max_age_sec,
        "expires_utc": format_utc(expires) if expires else None,
        "spread_sec": int((newest - oldest).total_seconds()) if newest and oldest else None,
    }
    checks = {
        "timestamps_present": bool(readiness_end and preflight_end and bundle_end),
        "not_from_future": bool(age is not None and age >= 0),
        "within_max_age": bool(age is not None and age <= max_age_sec),
        "bounded_spread": bool(freshness["spread_sec"] is not None and freshness["spread_sec"] <= 60),
    }
    return freshness, checks


def handoff_payload(
    wsta172_path: Path,
    command_json: Path,
    command_sh: Path,
    command_payload_obj: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "a90-wsta173-expiring-wsta170-execute-handoff-v1",
        "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY",
        "wsta172_result": rel(wsta172_path),
        "command_json": rel(command_json),
        "command_script": rel(command_sh),
        "command": command_payload_obj.get("command", []),
        "required_ack_flags": command_payload_obj.get("required_ack_flags", []),
        "expected_outcome": command_payload_obj.get("expected_outcome", {}),
        "freshness": freshness,
        "executed": False,
        "seccomp_filter_loaded": False,
        "seccomp_enforced": False,
        "correct_wsta161_token_supplied": False,
        "secret_values_logged": 0,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta173-seccomp-expiring-execute-handoff-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    proof_path = resolve_path(args.wsta172_proof_json)
    result: dict[str, Any] = {
        "scope": "WSTA173 expiring WSTA170 execution handoff",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "wsta172_proof_json": rel(proof_path),
        "safety": safety_flags(),
        "checks": {
            "explicit_handoff_gate": bool(args.emit_expiring_handoff),
            "private_run_dir": wsta160.is_under(run_dir, PRIVATE_ROOT),
            "wsta172_proof_private": wsta160.is_under(proof_path, PRIVATE_ROOT),
            "wsta172_proof_present": proof_path.is_file(),
        },
    }
    if not result["checks"]["private_run_dir"]:
        result["decision"] = "wsta173-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / SUMMARY_NAME
    for key, decision in (
        ("explicit_handoff_gate", "wsta173-blocked-explicit-handoff-gate-required"),
        ("wsta172_proof_private", "wsta173-blocked-wsta172-proof-nonprivate"),
        ("wsta172_proof_present", "wsta173-blocked-wsta172-proof-missing"),
    ):
        if not result["checks"][key]:
            result["decision"] = decision
            result["gate_decision"] = decision
            result["ended_utc"] = utc_stamp()
            write_json(out_path, result)
            return result

    wsta172_result = load_json(proof_path)
    readiness_path = path_from_result(wsta172_result, "fresh_readiness", "result_json")
    source_gate_path = path_from_result(wsta172_result, "source_gate", "result_json")
    preflight_path = path_from_result(wsta172_result, "execute_preflight", "result_json")
    command_json = path_from_result(wsta172_result, "execute_preflight", "command_json")
    command_sh = path_from_result(wsta172_result, "execute_preflight", "command_script")
    path_checks = {
        "readiness_path_private": bool(readiness_path and wsta160.is_under(readiness_path, PRIVATE_ROOT)),
        "source_gate_path_private": bool(source_gate_path and wsta160.is_under(source_gate_path, PRIVATE_ROOT)),
        "preflight_path_private": bool(preflight_path and wsta160.is_under(preflight_path, PRIVATE_ROOT)),
        "command_json_private": bool(command_json and wsta160.is_under(command_json, PRIVATE_ROOT)),
        "command_sh_private": bool(command_sh and wsta160.is_under(command_sh, PRIVATE_ROOT)),
        "readiness_present": bool(readiness_path and readiness_path.is_file()),
        "source_gate_present": bool(source_gate_path and source_gate_path.is_file()),
        "preflight_present": bool(preflight_path and preflight_path.is_file()),
        "command_json_present": bool(command_json and command_json.is_file()),
        "command_sh_present": bool(command_sh and command_sh.is_file()),
    }
    result["path_checks"] = path_checks
    result["checks"]["paths_valid"] = all(path_checks.values())
    if not result["checks"]["paths_valid"]:
        result["decision"] = "wsta173-blocked-paths-invalid"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    assert readiness_path is not None
    assert source_gate_path is not None
    assert preflight_path is not None
    assert command_json is not None
    assert command_sh is not None
    readiness = load_json(readiness_path)
    source_gate = load_json(source_gate_path)
    preflight = load_json(preflight_path)
    command_payload_obj = load_json(command_json)
    command_script = command_sh.read_text(encoding="utf-8")
    freshness, freshness_checks = validate_freshness(
        wsta172_result,
        readiness,
        preflight,
        int(args.max_age_sec),
    )
    result["freshness"] = freshness
    result["freshness_checks"] = freshness_checks
    result["wsta172_checks"] = validate_wsta172_result(wsta172_result)
    result["nested_checks"] = validate_nested_results(readiness, source_gate, preflight)
    result["command_checks"] = validate_command_payload(command_payload_obj, command_script)
    result["checks"].update({
        "freshness_valid": all(freshness_checks.values()),
        "wsta172_valid": all(result["wsta172_checks"].values()),
        "nested_valid": all(result["nested_checks"].values()),
        "command_valid": all(result["command_checks"].values()),
    })
    all_ok = all(
        result["checks"][key]
        for key in ("freshness_valid", "wsta172_valid", "nested_valid", "command_valid")
    )
    result["decision"] = PASS_DECISION if all_ok else "wsta173-blocked-handoff-invalid"
    result["gate_decision"] = "ok" if result["decision"] == PASS_DECISION else result["decision"]
    result["handoff"] = {
        "handoff_json": rel(run_dir / HANDOFF_NAME),
        "state": "READY_TO_RUN_NOT_EXECUTED_UNTIL_EXPIRY" if all_ok else "BLOCKED",
        "expires_utc": freshness.get("expires_utc"),
        "command_json": rel(command_json),
        "command_script": rel(command_sh),
        "executed": False,
    }
    if all_ok:
        result["safety"]["handoff_generated"] = True
        write_json(run_dir / HANDOFF_NAME, handoff_payload(proof_path, command_json, command_sh, command_payload_obj, freshness))
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta172-proof-json", type=Path, default=DEFAULT_WSTA172_PROOF)
    parser.add_argument("--max-age-sec", type=int, default=900)
    parser.add_argument("--emit-expiring-handoff", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta173-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
