#!/usr/bin/env python3
"""WSTA64 host-only persistent session readiness audit.

WSTA63 prepares a private persistent-exposure session.  WSTA64 is the last
host-only audit before an operator may choose to run the WSTA58 live template:
it verifies that the WSTA63 result is still fresh, that the initial private
lease has not expired, that renewal is represented by a WSTA53 source rather
than a pre-minted stale lease, and that the live command template contains only
token placeholders.

This script performs no device action, native reboot, Wi-Fi association, DHCP,
public tunnel, public smoke, userdata action, switch-root, or flash.
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

import run_wsta58_renewal_manual_stop_proof as wsta58  # noqa: E402
import run_wsta63_persistent_session_controller as wsta63  # noqa: E402


REPO_ROOT = wsta63.REPO_ROOT
PRIVATE_ROOT = wsta63.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta63.DEFAULT_RUN_BASE
PASS_DECISION = "wsta64-persistent-session-readiness-pass"
DEFAULT_MIN_INITIAL_SECONDS_REMAINING = 30


def rel(path: Path) -> str:
    return wsta63.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def parse_utc_stamp(value: Any) -> _dt.datetime | None:
    return wsta58.wsta55.parse_utc_stamp(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta63.is_under(path, root)


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA64 host-only persistent session readiness audit",
        "default_mode": "fail-closed-host-only",
        "input": "workspace/private/runs/server-distro/<wsta63-run>/wsta63_result.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta63-result-json",
            "workspace/private/runs/server-distro/<wsta63-run>/wsta63_result.json",
            "--min-initial-seconds-remaining",
            str(DEFAULT_MIN_INITIAL_SECONDS_REMAINING),
        ],
        "live_execution": "not-run-by-wsta64",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def now_from_args(args: argparse.Namespace) -> _dt.datetime:
    if not args.now_utc:
        return utc_now()
    parsed = parse_utc_stamp(args.now_utc)
    if parsed is None:
        raise ValueError("--now-utc must be YYYYMMDDTHHMMSSZ")
    return parsed


def seconds_remaining(expires_utc: Any, now: _dt.datetime) -> int | None:
    expires = parse_utc_stamp(expires_utc)
    if expires is None:
        return None
    return int((expires - now).total_seconds())


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta64-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta64-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta64-blocked-{label}-missing"
    return path, None


def validate_command_template(command: Any,
                              initial_lease: Path,
                              renewal_source: Path) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        return False, "wsta64-blocked-live-template-invalid", {}
    required_flags = {
        "--execute-renewal-manual-stop",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--force-ttl-expiry-proof",
        "--force-manual-stop-proof",
    }
    missing = sorted(flag for flag in required_flags if flag not in command)
    if missing:
        return False, "wsta64-blocked-live-template-missing-flag", {"missing": missing}
    if "<native-confirm-token>" not in command or "<public-confirm-token>" not in command:
        return False, "wsta64-blocked-live-template-token-placeholder-missing", {}
    joined = "\n".join(command)
    if wsta58.wsta55.wsta45.wsta25.NATIVE_CONFIRM_TOKEN in joined:
        return False, "wsta64-blocked-live-template-raw-native-token", {}
    if wsta58.wsta55.wsta45.PUBLIC_CONFIRM_TOKEN in joined:
        return False, "wsta64-blocked-live-template-raw-public-token", {}
    if rel(initial_lease) not in command:
        return False, "wsta64-blocked-live-template-initial-lease-mismatch", {}
    if rel(renewal_source) not in command:
        return False, "wsta64-blocked-live-template-renewal-source-mismatch", {}
    return True, "ok", {
        "required_flags_present": True,
        "token_placeholders_present": True,
        "raw_token_values_logged": False,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "readiness": result.get("readiness", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta63.redaction_findings(payload)


def run(args: argparse.Namespace) -> dict[str, Any]:
    now = now_from_args(args)
    ts = utc_stamp(now)
    run_id = args.run_id or f"wsta64-persistent-session-readiness-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA64 host-only persistent session readiness audit",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta64-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta64-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta64_result.json"

    if args.wsta63_result_json is None:
        result["decision"] = "wsta64-blocked-wsta63-result-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    wsta63_path, path_error = require_private_path(args.wsta63_result_json, "wsta63-result")
    if path_error or wsta63_path is None:
        result["decision"] = path_error or "wsta64-blocked-wsta63-result"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    source = load_json(wsta63_path)
    session = source.get("session_redacted") or source.get("session") or {}
    result["readiness"] = {
        "wsta63_result": rel(wsta63_path),
        "initial_private_lease_artifact": session.get("initial_private_lease_artifact"),
        "renewal_wsta53_result": session.get("renewal_wsta53_result"),
        "wsta58_preflight_result": session.get("wsta58_preflight_result"),
        "min_initial_seconds_remaining": args.min_initial_seconds_remaining,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    if source.get("decision") != wsta63.PASS_DECISION:
        result["decision"] = "wsta64-blocked-wsta63-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    initial_lease, path_error = require_private_path(session.get("initial_private_lease_artifact"), "initial-lease")
    if path_error or initial_lease is None:
        result["decision"] = path_error or "wsta64-blocked-initial-lease"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    renewal_source, path_error = require_private_path(session.get("renewal_wsta53_result"), "renewal-source")
    if path_error or renewal_source is None:
        result["decision"] = path_error or "wsta64-blocked-renewal-source"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    wsta58_result_path, path_error = require_private_path(session.get("wsta58_preflight_result"), "wsta58-preflight")
    if path_error or wsta58_result_path is None:
        result["decision"] = path_error or "wsta64-blocked-wsta58-preflight"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    initial_ok, initial_decision, initial_detail = wsta58.wsta55.validate_artifact(initial_lease, now)
    remaining = seconds_remaining(initial_detail.get("expires_utc"), now)
    result["readiness"]["initial_seconds_remaining"] = remaining
    if not initial_ok:
        result["decision"] = f"wsta64-blocked-initial-{initial_decision}"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    if remaining is None or remaining < args.min_initial_seconds_remaining:
        result["decision"] = "wsta64-blocked-initial-lease-near-expiry"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    renewal_ok, renewal_decision, renewal_detail = wsta58.validate_renewal_source(renewal_source)
    if not renewal_ok:
        result["decision"] = renewal_decision
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    wsta58_preflight = load_json(wsta58_result_path)
    if wsta58_preflight.get("decision") != wsta58.PREFLIGHT_DECISION:
        result["decision"] = "wsta64-blocked-wsta58-preflight-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result
    checks = wsta58_preflight.get("checks") or {}
    if checks.get("renewal_lease_refresh_ready") is not True:
        result["decision"] = "wsta64-blocked-renewal-refresh-not-ready"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    template_ok, template_decision, template_detail = validate_command_template(
        session.get("live_command_template"),
        initial_lease,
        renewal_source,
    )
    if not template_ok:
        result["decision"] = template_decision
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = template_detail
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    result["checks"] = {
        "wsta63_pass": True,
        "initial_private_lease_unexpired": True,
        "initial_seconds_remaining_min_met": True,
        "renewal_source_wsta53_valid": True,
        "renewal_lease_minted_after_initial": True,
        "wsta58_preflight_pass": True,
        "wsta58_renewal_refresh_ready": True,
        "live_template_placeholders_only": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["readiness"].update({
        "state": "PUBLIC_OFF",
        "initial_ttl_sec": initial_detail.get("ttl_sec"),
        "renewal_ttl_sec": renewal_detail.get("ttl_sec"),
        "live_command_template_redacted": True,
        "token_placeholders_present": bool(template_detail.get("token_placeholders_present")),
        "ready_for_explicit_wsta58_live_gate": True,
    })
    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta64-blocked-public-summary-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta63-result-json", type=Path)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
    parser.add_argument("--now-utc")
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
        payload = {"decision": "wsta64-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
