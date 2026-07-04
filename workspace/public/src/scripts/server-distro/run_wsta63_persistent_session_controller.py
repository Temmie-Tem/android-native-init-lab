#!/usr/bin/env python3
"""WSTA63 host-only persistent exposure session controller.

This runner prepares the next WSTA58 live session without executing it:

* create a fresh initial WSTA53/WSTA54 short lease artifact;
* create a fresh renewal WSTA53 source, leaving renewal lease minting deferred
  until after the initial live WSTA55 leg;
* run WSTA58 in preflight mode to prove the pair is accepted; and
* emit a redacted live command template with token placeholders.

It performs no device action, native reboot, Wi-Fi association, DHCP, public
tunnel, public smoke, userdata action, switch-root, or flash.
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

import run_wsta53_persistent_exposure_plan as wsta53  # noqa: E402
import run_wsta54_private_lease_artifact as wsta54  # noqa: E402
import run_wsta58_renewal_manual_stop_proof as wsta58  # noqa: E402


REPO_ROOT = wsta58.REPO_ROOT
PRIVATE_ROOT = wsta58.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta58.DEFAULT_RUN_BASE
PASS_DECISION = "wsta63-persistent-session-preflight-pass"
SHORT_SESSION_MAX_TTL_SEC = wsta58.wsta55.SHORT_LEASE_MAX_TTL_SEC


def rel(path: Path) -> str:
    return wsta58.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta58.is_under(path, root)


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
        "scope": "WSTA63 host-only persistent exposure session controller",
        "default_mode": "fail-closed-host-only",
        "short_session_max_ttl_sec": SHORT_SESSION_MAX_TTL_SEC,
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-session",
            "--ttl-sec",
            str(SHORT_SESSION_MAX_TTL_SEC),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ],
        "live_execution": "not-run-by-wsta63",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def validate_gate(args: argparse.Namespace) -> tuple[bool, str, dict[str, Any]]:
    if not args.prepare_session:
        return False, "wsta63-blocked-prepare-session-required", {}
    try:
        ttl_sec = int(args.ttl_sec)
    except (TypeError, ValueError):
        return False, "wsta63-blocked-ttl-invalid", {"ttl_sec": args.ttl_sec}
    if ttl_sec <= 0 or ttl_sec > SHORT_SESSION_MAX_TTL_SEC:
        return False, "wsta63-blocked-ttl-not-short", {
            "ttl_sec": ttl_sec,
            "short_session_max_ttl_sec": SHORT_SESSION_MAX_TTL_SEC,
        }
    if not args.ack_credentialed_wifi:
        return False, "wsta63-blocked-credentialed-wifi-ack-required", {}
    if not args.ack_public_exposure:
        return False, "wsta63-blocked-public-exposure-ack-required", {}
    if args.native_confirm_token_source != "private":
        return False, "wsta63-blocked-native-confirm-token-private-source-required", {}
    if args.public_confirm_token_source != "private":
        return False, "wsta63-blocked-public-confirm-token-private-source-required", {}
    return True, "ok", {"ttl_sec": ttl_sec}


def wsta53_args(run_dir: Path, ttl_sec: int) -> argparse.Namespace:
    return wsta53.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--ttl-sec",
        str(ttl_sec),
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--native-confirm-token-source",
        "private",
        "--public-confirm-token-source",
        "private",
    ])


def wsta54_args(run_dir: Path, wsta53_result: Path) -> argparse.Namespace:
    return wsta54.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--wsta53-result-json",
        str(wsta53_result),
    ])


def wsta58_preflight_args(run_dir: Path,
                          initial_lease: Path,
                          renewal_source: Path,
                          args: argparse.Namespace) -> argparse.Namespace:
    return wsta58.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--initial-lease-artifact-json",
        str(initial_lease),
        "--renewal-wsta53-result-json",
        str(renewal_source),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ])


def live_command_template(run_dir: Path, initial_lease: Path, renewal_source: Path) -> list[str]:
    return [
        "python3",
        rel(SCRIPT_DIR / "run_wsta58_renewal_manual_stop_proof.py"),
        "--run-dir",
        rel(run_dir / "wsta58-live"),
        "--initial-lease-artifact-json",
        rel(initial_lease),
        "--renewal-wsta53-result-json",
        rel(renewal_source),
        "--execute-renewal-manual-stop",
        "--allow-operator-live",
        "--allow-native-reboot",
        "--allow-public-live",
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--force-ttl-expiry-proof",
        "--force-manual-stop-proof",
        "--native-confirm-token",
        "<native-confirm-token>",
        "--public-confirm-token",
        "<public-confirm-token>",
    ]


def redacted_session(run_dir: Path,
                     ttl_sec: int,
                     initial_lease: Path | None,
                     renewal_source: Path | None,
                     wsta58_result: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "state": "PUBLIC_OFF",
        "default_state": "public-off",
        "ttl_sec": ttl_sec,
        "short_session_max_ttl_sec": SHORT_SESSION_MAX_TTL_SEC,
        "initial_private_lease_artifact": rel(initial_lease) if initial_lease else None,
        "renewal_wsta53_result": rel(renewal_source) if renewal_source else None,
        "renewal_lease_minted_after_initial": True,
        "wsta58_preflight_decision": (wsta58_result or {}).get("decision"),
        "wsta58_preflight_result": rel(run_dir / "wsta58-preflight" / "wsta58_result.json"),
        "live_command_template": live_command_template(run_dir, initial_lease, renewal_source)
        if initial_lease and renewal_source else [],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "session": result.get("session_redacted", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta58.redaction_findings(payload)


def classify(checks: dict[str, Any]) -> str:
    if not checks.get("initial_wsta53_pass"):
        return "wsta63-blocked-initial-wsta53"
    if not checks.get("initial_wsta54_pass"):
        return "wsta63-blocked-initial-wsta54"
    if not checks.get("renewal_source_wsta53_pass"):
        return "wsta63-blocked-renewal-source-wsta53"
    if not checks.get("wsta58_preflight_pass"):
        return "wsta63-blocked-wsta58-preflight"
    return PASS_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta63-persistent-session-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA63 host-only persistent exposure session controller",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta63-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta63-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = run_dir / "wsta63_result.json"
    manifest_path = run_dir / "wsta63_session_manifest.json"

    gate_ok, gate_decision, detail = validate_gate(args)
    result["gate_decision"] = gate_decision
    result["gate_detail"] = detail
    if not gate_ok:
        result["decision"] = gate_decision
        result["checks"] = {
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_path, result)
        return result

    ttl_sec = int(detail["ttl_sec"])
    initial_wsta53 = wsta53.run(wsta53_args(run_dir / "initial-wsta53", ttl_sec))
    initial_wsta53_result = run_dir / "initial-wsta53" / "wsta53_result.json"
    initial_wsta54: dict[str, Any] = {}
    initial_lease: Path | None = None
    if initial_wsta53.get("decision") == wsta53.PASS_DECISION:
        initial_wsta54 = wsta54.run(wsta54_args(run_dir / "initial-wsta54", initial_wsta53_result))
        if initial_wsta54.get("decision") == wsta54.PASS_DECISION:
            initial_lease = REPO_ROOT / str(initial_wsta54["private_lease_artifact"])

    renewal_wsta53 = wsta53.run(wsta53_args(run_dir / "renewal-source-wsta53", ttl_sec))
    renewal_source = run_dir / "renewal-source-wsta53" / "wsta53_result.json"
    wsta58_result: dict[str, Any] = {}
    if (
        initial_lease is not None
        and renewal_wsta53.get("decision") == wsta53.PASS_DECISION
    ):
        wsta58_result = wsta58.run(wsta58_preflight_args(
            run_dir / "wsta58-preflight",
            initial_lease,
            renewal_source,
            args,
        ))

    result["checks"] = {
        "initial_wsta53_pass": initial_wsta53.get("decision") == wsta53.PASS_DECISION,
        "initial_wsta54_pass": initial_wsta54.get("decision") == wsta54.PASS_DECISION,
        "initial_private_lease_present": initial_lease is not None,
        "renewal_source_wsta53_pass": renewal_wsta53.get("decision") == wsta53.PASS_DECISION,
        "renewal_lease_minted_after_initial": True,
        "wsta58_preflight_pass": wsta58_result.get("decision") == wsta58.PREFLIGHT_DECISION,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["session_redacted"] = redacted_session(
        run_dir,
        ttl_sec,
        initial_lease,
        renewal_source if renewal_wsta53.get("decision") == wsta53.PASS_DECISION else None,
        wsta58_result,
    )
    result["decision"] = classify(result["checks"])
    findings = redaction_findings(public_summary(result))
    if findings:
        result["decision"] = "wsta63-blocked-public-summary-redaction-finding"
        result["gate_detail"] = {"findings": findings}
    result["ended_utc"] = utc_stamp()
    write_json(manifest_path, result["session_redacted"])
    result["session_manifest"] = rel(manifest_path)
    write_json(out_path, result)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--ttl-sec", type=int, default=SHORT_SESSION_MAX_TTL_SEC)
    parser.add_argument("--prepare-session", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token-source", default="")
    parser.add_argument("--public-confirm-token-source", default="")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
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
        payload = {"decision": "wsta63-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
