#!/usr/bin/env python3
"""WSTA74 host-only persistent arming packet status.

WSTA73 creates an arming packet.  WSTA74 is a status layer for that packet: it
consumes the private WSTA73 packet, reruns WSTA73 against the original WSTA72
prepare-to-arm path, and reports whether the packet is still ready for an
explicit WSTA58 live gate.

It never executes the WSTA58 live gate.  It performs no device action, native
reboot, Wi-Fi association, DHCP, public tunnel, public smoke, userdata action,
switch-root, or flash.
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

import run_wsta73_persistent_arming_packet as wsta73  # noqa: E402


REPO_ROOT = wsta73.REPO_ROOT
PRIVATE_ROOT = wsta73.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta73.DEFAULT_RUN_BASE
PASS_DECISION = "wsta74-persistent-arming-status-pass"


def rel(path: Path) -> str:
    return wsta73.rel(path)


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(value: _dt.datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta73.is_under(path, root)


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
        "scope": "WSTA74 host-only persistent arming packet status",
        "default_mode": "host-only-revalidate-packet-status",
        "input": "workspace/private/runs/server-distro/<wsta73-run>/wsta73_arming_packet.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta73-arming-packet-json",
            "workspace/private/runs/server-distro/<wsta73-run>/wsta73_arming_packet.json",
        ],
        "live_execution": "not-run-by-wsta74",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "arming_status": result.get("arming_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta73.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta74-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta74-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta74-blocked-{label}-missing"
    return path, None


def validate_packet(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta74-blocked-arming-packet-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta73.PASS_DECISION:
        return False, "wsta74-blocked-arming-packet-not-pass", {"decision": payload.get("decision")}
    packet = payload.get("arming_packet")
    if not isinstance(packet, dict):
        return False, "wsta74-blocked-arming-packet-missing", {}
    if packet.get("state") != "ARMING_PACKET_READY_DEFAULT_OFF":
        return False, "wsta74-blocked-arming-packet-not-ready", {"state": packet.get("state")}
    if packet.get("default_public_off") is not True:
        return False, "wsta74-blocked-default-public-off-missing", {}
    if packet.get("live_execution_requested") is not False:
        return False, "wsta74-blocked-live-execution-requested", {}
    if packet.get("public_url_value_logged") is not False:
        return False, "wsta74-blocked-public-url-logged", {}
    if packet.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta74-blocked-secret-values-logged", {}
    prepare_path, path_error = require_private_path(packet.get("wsta72_prepare_to_arm"), "prepare-to-arm")
    if path_error or prepare_path is None:
        return False, path_error or "wsta74-blocked-prepare-to-arm", {}
    return True, "ok", {
        "payload": payload,
        "packet": packet,
        "prepare_path": prepare_path,
    }


def wsta73_args(run_dir: Path,
                prepare_path: Path,
                min_remaining: int | None,
                now_utc: str | None) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta72-prepare-to-arm-json",
        str(prepare_path),
    ]
    if min_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(min_remaining)])
    if now_utc:
        argv.extend(["--now-utc", now_utc])
    return wsta73.build_arg_parser().parse_args(argv)


def min_remaining_from_args(args: argparse.Namespace, packet: dict[str, Any]) -> int | None:
    if args.min_initial_seconds_remaining is not None:
        return int(args.min_initial_seconds_remaining)
    value = packet.get("min_initial_seconds_remaining")
    if value is None:
        return None
    return int(value)


def command_matches(old_packet: dict[str, Any], new_packet: dict[str, Any]) -> bool:
    return old_packet.get("wsta58_live_command_template") == new_packet.get("wsta58_live_command_template")


def build_status(packet_path: Path,
                 old_packet: dict[str, Any],
                 recheck: dict[str, Any],
                 recheck_path: Path,
                 out_json: Path,
                 out_md: Path) -> dict[str, Any]:
    new_packet = recheck.get("arming_packet") or {}
    recheck_pass = recheck.get("decision") == wsta73.PASS_DECISION
    template_match = bool(recheck_pass and command_matches(old_packet, new_packet))
    ready = bool(recheck_pass and template_match and new_packet.get("ready_for_live") is True)
    state = "READY_TO_EXECUTE_DEFAULT_OFF" if ready else "STALE_OR_NOT_READY"
    if recheck_pass and not template_match:
        state = "DRIFT_RECHECK_REQUIRED"
    return {
        "state": state,
        "ready_for_live": ready,
        "wsta73_arming_packet": rel(packet_path),
        "wsta73_recheck_result": rel(recheck_path),
        "wsta73_recheck_decision": recheck.get("decision"),
        "wsta73_recheck_gate_detail": recheck.get("gate_detail", {}),
        "wsta65_session_state": new_packet.get("wsta65_session_state"),
        "initial_seconds_remaining": new_packet.get("initial_seconds_remaining"),
        "template_match": template_match,
        "abort_condition_count": len(new_packet.get("abort_conditions") or old_packet.get("abort_conditions") or []),
        "ack_count": len(new_packet.get("operator_acknowledgements_required")
                         or old_packet.get("operator_acknowledgements_required") or []),
        "recommended_next_action": "operator-may-run-explicit-wsta58-live-gate" if ready else "rerun-wsta72-then-wsta73",
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(status: dict[str, Any]) -> str:
    lines = [
        "# WSTA Persistent Arming Packet Status",
        "",
        f"- State: `{status.get('state')}`",
        f"- Ready for live: `{str(bool(status.get('ready_for_live'))).lower()}`",
        f"- WSTA73 arming packet: `{status.get('wsta73_arming_packet')}`",
        f"- WSTA73 recheck: `{status.get('wsta73_recheck_result')}`",
        f"- WSTA73 recheck decision: `{status.get('wsta73_recheck_decision')}`",
        f"- WSTA65 state: `{status.get('wsta65_session_state')}`",
        f"- Initial seconds remaining: `{status.get('initial_seconds_remaining')}`",
        f"- Template match: `{str(bool(status.get('template_match'))).lower()}`",
        f"- Recommended next action: `{status.get('recommended_next_action')}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta74-persistent-arming-status-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA74 host-only persistent arming packet status",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta74-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta74-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta74_arming_status.json"
    out_md = run_dir / "wsta74_arming_status.md"

    if args.wsta73_arming_packet_json is None:
        result["decision"] = "wsta74-blocked-arming-packet-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    packet_path, path_error = require_private_path(args.wsta73_arming_packet_json, "arming-packet")
    if path_error or packet_path is None:
        result["decision"] = path_error or "wsta74-blocked-arming-packet"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    valid, decision, detail = validate_packet(packet_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    packet = detail["packet"]
    recheck_dir = run_dir / "wsta73-recheck"
    recheck = wsta73.run(wsta73_args(
        recheck_dir,
        detail["prepare_path"],
        min_remaining_from_args(args, packet),
        args.now_utc,
    ))
    recheck_path = recheck_dir / "wsta73_arming_packet.json"
    status = build_status(packet_path, packet, recheck, recheck_path, out_json, out_md)
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "arming_status": status,
        "checks": {
            "arming_packet_private": True,
            "wsta73_rechecked": True,
            "ready_for_live": bool(status.get("ready_for_live")),
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        },
    })
    md_text = markdown(status)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta74-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings + md_findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--wsta73-arming-packet-json", type=Path)
    parser.add_argument("--min-initial-seconds-remaining", type=int)
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
        payload = {"decision": "wsta74-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
