#!/usr/bin/env python3
"""WSTA79 host-only persistent operator packet status.

WSTA78 renders an operator packet that is fresh at creation time.  WSTA79 turns
that packet into a current-time status: it consumes a private WSTA78 packet,
reruns WSTA78 from the original WSTA77 summary, and reports whether the packet
is still safe to use as a default-off handoff for an explicit WSTA58 live gate.

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

import run_wsta78_persistent_operator_packet as wsta78  # noqa: E402


REPO_ROOT = wsta78.REPO_ROOT
PRIVATE_ROOT = wsta78.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta78.DEFAULT_RUN_BASE
PASS_DECISION = "wsta79-persistent-operator-packet-status-pass"


def rel(path: Path) -> str:
    return wsta78.rel(path)


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
    return wsta78.load_json(path)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta78.is_under(path, root)


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
        "scope": "WSTA79 host-only persistent operator packet status",
        "default_mode": "host-only-revalidate-operator-packet-status",
        "input": "workspace/private/runs/server-distro/<wsta78-run>/wsta78_operator_packet.json",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--wsta78-operator-packet-json",
            "workspace/private/runs/server-distro/<wsta78-run>/wsta78_operator_packet.json",
        ],
        "live_execution": "not-run-by-wsta79",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "operator_packet_status": result.get("operator_packet_status", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta78.redaction_findings(payload)


def require_private_path(value: Any, label: str) -> tuple[Path | None, str | None]:
    if isinstance(value, Path):
        candidate = value
    elif isinstance(value, str) and value:
        candidate = Path(value)
    else:
        return None, f"wsta79-blocked-{label}-missing"
    path = resolve_path(candidate)
    if not is_under(path, PRIVATE_ROOT):
        return None, f"wsta79-blocked-{label}-nonprivate"
    if not path.exists():
        return None, f"wsta79-blocked-{label}-missing"
    return path, None


def validate_operator_packet(path: Path) -> tuple[bool, str, dict[str, Any]]:
    try:
        payload = load_json(path)
    except Exception as exc:  # noqa: BLE001
        return False, "wsta79-blocked-operator-packet-unreadable", {"error": str(exc)}
    if payload.get("decision") != wsta78.PASS_DECISION:
        return False, "wsta79-blocked-operator-packet-not-pass", {"decision": payload.get("decision")}
    packet = payload.get("operator_packet")
    if not isinstance(packet, dict):
        return False, "wsta79-blocked-operator-packet-missing", {}
    if packet.get("state") != "READY_OPERATOR_PACKET_DEFAULT_OFF":
        return False, "wsta79-blocked-operator-packet-not-ready", {"state": packet.get("state")}
    if packet.get("default_public_off") is not True:
        return False, "wsta79-blocked-default-public-off-missing", {}
    if packet.get("live_execution_requested") is not False:
        return False, "wsta79-blocked-live-execution-requested", {}
    if packet.get("public_url_value_logged") is not False:
        return False, "wsta79-blocked-public-url-logged", {}
    if packet.get("secret_values_logged") not in (0, "0", None):
        return False, "wsta79-blocked-secret-values-logged", {}
    source_summary, path_error = require_private_path(packet.get("source_wsta77_summary"), "source-summary")
    if path_error or source_summary is None:
        return False, path_error or "wsta79-blocked-source-summary", {}
    return True, "ok", {"payload": payload, "packet": packet, "source_summary": source_summary}


def selected_index_from_args(args: argparse.Namespace, packet: dict[str, Any]) -> int:
    if args.ready_index is not None:
        return int(args.ready_index)
    value = packet.get("selected_ready_index")
    if isinstance(value, int):
        return value
    return 0


def wsta78_args(run_dir: Path,
                summary_path: Path,
                ready_index: int,
                max_briefs: int,
                max_packets: int,
                min_remaining: int | None,
                now_utc: str | None) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta77-launch-summary-json",
        str(summary_path),
        "--ready-index",
        str(ready_index),
        "--max-briefs",
        str(max_briefs),
        "--max-packets",
        str(max_packets),
    ]
    if min_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(min_remaining)])
    if now_utc:
        argv.extend(["--now-utc", now_utc])
    return wsta78.build_arg_parser().parse_args(argv)


def logical_packet_match(old_packet: dict[str, Any], new_packet: dict[str, Any]) -> bool:
    return (
        old_packet.get("selected_wsta76_launch_brief") == new_packet.get("selected_wsta76_launch_brief")
        and old_packet.get("selected_wsta73_arming_packet") == new_packet.get("selected_wsta73_arming_packet")
        and old_packet.get("wsta58_live_command_template") == new_packet.get("wsta58_live_command_template")
    )


def command_template_match(old_packet: dict[str, Any], new_packet: dict[str, Any]) -> bool:
    return old_packet.get("wsta58_live_command_template") == new_packet.get("wsta58_live_command_template")


def build_status(packet_path: Path,
                 old_packet: dict[str, Any],
                 recheck: dict[str, Any],
                 recheck_path: Path,
                 selected_index: int,
                 out_json: Path,
                 out_md: Path) -> dict[str, Any]:
    new_packet = recheck.get("operator_packet") if isinstance(recheck.get("operator_packet"), dict) else {}
    recheck_pass = recheck.get("decision") == wsta78.PASS_DECISION
    packet_match = bool(recheck_pass and logical_packet_match(old_packet, new_packet))
    template_match = bool(recheck_pass and command_template_match(old_packet, new_packet))
    ready = bool(recheck_pass and packet_match and new_packet.get("ready_for_live") is True)
    state = "READY_TO_RUN_DEFAULT_OFF" if ready else "STALE_OR_NOT_READY"
    if recheck_pass and not packet_match:
        state = "DRIFT_RECHECK_REQUIRED"
    return {
        "state": state,
        "ready_for_live": ready,
        "wsta78_operator_packet": rel(packet_path),
        "wsta78_recheck_result": rel(recheck_path),
        "wsta78_recheck_decision": recheck.get("decision"),
        "wsta78_recheck_gate_detail": recheck.get("gate_detail", {}),
        "selected_ready_index": selected_index,
        "selected_wsta76_launch_brief": old_packet.get("selected_wsta76_launch_brief"),
        "fresh_selected_wsta76_launch_brief": new_packet.get("selected_wsta76_launch_brief"),
        "selected_wsta73_arming_packet": old_packet.get("selected_wsta73_arming_packet"),
        "fresh_selected_wsta73_arming_packet": new_packet.get("selected_wsta73_arming_packet"),
        "fresh_wsta76_launch_brief": new_packet.get("fresh_wsta76_launch_brief"),
        "wsta65_session_state": new_packet.get("wsta65_session_state"),
        "initial_seconds_remaining": new_packet.get("initial_seconds_remaining"),
        "packet_match": packet_match,
        "template_match": template_match,
        "ack_count": len(new_packet.get("operator_acknowledgements_required")
                         or old_packet.get("operator_acknowledgements_required") or []),
        "guardrail_count": len(new_packet.get("execution_guardrails") or old_packet.get("execution_guardrails") or []),
        "recommended_next_action": (
            "operator-may-run-explicit-wsta58-live-gate-from-current-packet"
            if ready
            else "rerun-wsta72-through-wsta78"
        ),
        "json_path": rel(out_json),
        "markdown_path": rel(out_md),
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(status: dict[str, Any]) -> str:
    lines = [
        "# WSTA Persistent Operator Packet Status",
        "",
        f"- State: `{status.get('state')}`",
        f"- Ready for live: `{str(bool(status.get('ready_for_live'))).lower()}`",
        f"- WSTA78 operator packet: `{status.get('wsta78_operator_packet')}`",
        f"- WSTA78 recheck: `{status.get('wsta78_recheck_result')}`",
        f"- WSTA78 recheck decision: `{status.get('wsta78_recheck_decision')}`",
        f"- Selected READY index: `{status.get('selected_ready_index')}`",
        f"- Selected WSTA76 brief: `{status.get('selected_wsta76_launch_brief')}`",
        f"- Fresh selected WSTA76 brief: `{status.get('fresh_selected_wsta76_launch_brief')}`",
        f"- Selected WSTA73 packet: `{status.get('selected_wsta73_arming_packet')}`",
        f"- Fresh selected WSTA73 packet: `{status.get('fresh_selected_wsta73_arming_packet')}`",
        f"- WSTA65 state: `{status.get('wsta65_session_state')}`",
        f"- Initial seconds remaining: `{status.get('initial_seconds_remaining')}`",
        f"- Packet match: `{str(bool(status.get('packet_match'))).lower()}`",
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
    run_id = args.run_id or f"wsta79-persistent-operator-packet-status-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA79 host-only persistent operator packet status",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta79-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta79-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta79_operator_packet_status.json"
    out_md = run_dir / "wsta79_operator_packet_status.md"

    if args.wsta78_operator_packet_json is None:
        result["decision"] = "wsta79-blocked-operator-packet-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    packet_path, path_error = require_private_path(args.wsta78_operator_packet_json, "operator-packet")
    if path_error or packet_path is None:
        result["decision"] = path_error or "wsta79-blocked-operator-packet"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    valid, decision, detail = validate_operator_packet(packet_path)
    if not valid:
        result["decision"] = decision
        result["gate_decision"] = decision
        result["gate_detail"] = detail
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    packet = detail["packet"]
    selected_index = selected_index_from_args(args, packet)
    recheck_dir = run_dir / "wsta78-recheck"
    recheck = wsta78.run(wsta78_args(
        recheck_dir,
        detail["source_summary"],
        selected_index,
        int(args.max_briefs),
        int(args.max_packets),
        args.min_initial_seconds_remaining,
        args.now_utc,
    ))
    recheck_path = recheck_dir / "wsta78_operator_packet.json"
    status = build_status(packet_path, packet, recheck, recheck_path, selected_index, out_json, out_md)
    result.update({
        "decision": PASS_DECISION,
        "gate_decision": "ok",
        "operator_packet_status": status,
        "checks": {
            "operator_packet_private": True,
            "wsta78_rechecked": True,
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
        result["decision"] = "wsta79-blocked-redaction-finding"
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
    parser.add_argument("--wsta78-operator-packet-json", type=Path)
    parser.add_argument("--ready-index", type=int)
    parser.add_argument("--max-briefs", type=int, default=wsta78.wsta77.DEFAULT_MAX_BRIEFS)
    parser.add_argument("--max-packets", type=int, default=wsta78.wsta77.wsta76.wsta75.DEFAULT_MAX_PACKETS)
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
        payload = {"decision": "wsta79-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
