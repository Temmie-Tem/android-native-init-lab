#!/usr/bin/env python3
"""WSTA88 one-command persistent operator workflow.

WSTA72 through WSTA80 are deliberately small gates.  WSTA88 is the operator
UX wrapper around those proven pieces: by default it creates a fresh private
default-off packet/status tree and stops at a WSTA80 execute gate.  Optional
WSTA58 live delegation is still guarded by the same explicit WSTA80
acknowledgement stack; nothing live runs by default.
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

import run_wsta72_persistent_prepare_to_arm as wsta72  # noqa: E402
import run_wsta73_persistent_arming_packet as wsta73  # noqa: E402
import run_wsta75_persistent_arming_inventory as wsta75  # noqa: E402
import run_wsta76_persistent_launch_brief as wsta76  # noqa: E402
import run_wsta77_persistent_launch_brief_summary as wsta77  # noqa: E402
import run_wsta78_persistent_operator_packet as wsta78  # noqa: E402
import run_wsta79_persistent_operator_packet_status as wsta79  # noqa: E402
import run_wsta80_persistent_operator_execute_gate as wsta80  # noqa: E402


REPO_ROOT = wsta80.REPO_ROOT
PRIVATE_ROOT = wsta80.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta80.DEFAULT_RUN_BASE
PREFLIGHT_DECISION = "wsta88-persistent-operator-workflow-preflight-pass"
PASS_DECISION = "wsta88-persistent-operator-workflow-live-pass"


def rel(path: Path) -> str:
    return wsta80.rel(path)


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


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta80.is_under(path, root)


def live_requested(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "execute_wsta58_from_status", False))


def safety_flags(args: argparse.Namespace, live_gate_ok: bool = False) -> dict[str, Any]:
    requested = live_requested(args)
    return {
        "device_action": requested and live_gate_ok,
        "boot_flash": False,
        "native_reboot": requested and live_gate_ok and bool(args.allow_native_reboot),
        "wifi_connect": "wsta80-wsta58-explicit-live-gated" if requested and live_gate_ok else False,
        "dhcp": "wsta80-wsta58-explicit-live-gated" if requested and live_gate_ok else False,
        "public_tunnel": "wsta80-wsta58-explicit-public-live-gated" if requested and live_gate_ok else False,
        "public_smoke": "wsta80-wsta58-explicit-public-live-gated" if requested and live_gate_ok else False,
        "userdata_touch": False,
        "switch_root": False,
        "native_confirm_token_value_logged": False,
        "public_confirm_token_value_logged": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA88 one-command persistent operator workflow",
        "default_mode": "host-only-preflight-default-public-off",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-to-execute",
            "--ttl-sec",
            str(wsta72.SHORT_SESSION_MAX_TTL_SEC),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ],
        "optional_live_execution": [
            "--execute-wsta58-from-status",
            "--allow-operator-live",
            "--allow-native-reboot",
            "--allow-public-live",
            "--force-ttl-expiry-proof",
            "--force-manual-stop-proof",
            "--native-confirm-token",
            "<native-confirm-token>",
            "--public-confirm-token",
            "<public-confirm-token>",
        ],
        "live_execution": "not-run-by-default",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "workflow": result.get("workflow", {}),
        "wsta80_redacted": result.get("wsta80_redacted", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta80.redaction_findings(payload)


def validate_gate(args: argparse.Namespace) -> tuple[bool, str, dict[str, Any]]:
    if not args.prepare_to_execute:
        return False, "wsta88-blocked-prepare-to-execute-required", {}
    try:
        ttl_sec = int(args.ttl_sec)
    except (TypeError, ValueError):
        return False, "wsta88-blocked-ttl-invalid", {"ttl_sec": args.ttl_sec}
    if ttl_sec <= 0 or ttl_sec > wsta72.SHORT_SESSION_MAX_TTL_SEC:
        return False, "wsta88-blocked-ttl-not-short", {
            "ttl_sec": ttl_sec,
            "short_session_max_ttl_sec": wsta72.SHORT_SESSION_MAX_TTL_SEC,
        }
    if not args.ack_credentialed_wifi:
        return False, "wsta88-blocked-credentialed-wifi-ack-required", {}
    if not args.ack_public_exposure:
        return False, "wsta88-blocked-public-exposure-ack-required", {}
    if args.native_confirm_token_source != "private":
        return False, "wsta88-blocked-native-confirm-token-private-source-required", {}
    if args.public_confirm_token_source != "private":
        return False, "wsta88-blocked-public-confirm-token-private-source-required", {}
    return True, "ok", {"ttl_sec": ttl_sec}


def workflow_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "wsta72": run_dir / "prepare",
        "wsta73": run_dir / "packet",
        "wsta75": run_dir / "inventory",
        "wsta76": run_dir / "brief",
        "wsta77": run_dir / "summary",
        "wsta78": run_dir / "operator",
        "wsta79": run_dir / "status",
        "wsta80_preflight": run_dir / "gate-preflight",
        "wsta80_live": run_dir / "gate-live",
    }


def wsta72_args(run_dir: Path, args: argparse.Namespace, ttl_sec: int) -> argparse.Namespace:
    return wsta72.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--prepare-to-arm",
        "--ttl-sec",
        str(ttl_sec),
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--native-confirm-token-source",
        "private",
        "--public-confirm-token-source",
        "private",
        "--ready-index",
        str(args.ready_index),
        "--min-initial-seconds-remaining",
        str(args.min_initial_seconds_remaining),
        "--max-sessions",
        str(args.max_sessions),
        "--max-retire-markers",
        str(args.max_retire_markers),
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ])


def wsta73_args(run_dir: Path, prepare_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = ["--run-dir", str(run_dir), "--wsta72-prepare-to-arm-json", str(prepare_path)]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta73.build_arg_parser().parse_args(argv)


def wsta75_args(run_dir: Path, scan_root: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--scan-root",
        str(scan_root),
        "--max-packets",
        str(args.max_packets),
    ]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta75.build_arg_parser().parse_args(argv)


def wsta76_args(run_dir: Path, inventory_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta75-arming-inventory-json",
        str(inventory_path),
        "--ready-index",
        str(args.ready_index),
        "--max-packets",
        str(args.max_packets),
    ]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta76.build_arg_parser().parse_args(argv)


def wsta77_args(run_dir: Path, scan_root: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--scan-root",
        str(scan_root),
        "--max-briefs",
        str(args.max_briefs),
        "--max-packets",
        str(args.max_packets),
        "--ready-index",
        str(args.ready_index),
    ]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta77.build_arg_parser().parse_args(argv)


def wsta78_args(run_dir: Path, summary_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta77-launch-summary-json",
        str(summary_path),
        "--ready-index",
        str(args.ready_index),
        "--max-briefs",
        str(args.max_briefs),
        "--max-packets",
        str(args.max_packets),
    ]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta78.build_arg_parser().parse_args(argv)


def wsta79_args(run_dir: Path, packet_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta78-operator-packet-json",
        str(packet_path),
        "--ready-index",
        str(args.ready_index),
        "--max-briefs",
        str(args.max_briefs),
        "--max-packets",
        str(args.max_packets),
    ]
    if args.min_initial_seconds_remaining is not None:
        argv.extend(["--min-initial-seconds-remaining", str(args.min_initial_seconds_remaining)])
    return wsta79.build_arg_parser().parse_args(argv)


def wsta80_args(run_dir: Path, status_path: Path, args: argparse.Namespace, *, live: bool) -> argparse.Namespace:
    argv = [
        "--run-dir",
        str(run_dir),
        "--wsta79-operator-packet-status-json",
        str(status_path),
    ]
    if live:
        argv.append("--execute-wsta58-from-status")
        for enabled, flag in (
            (args.allow_operator_live, "--allow-operator-live"),
            (args.allow_native_reboot, "--allow-native-reboot"),
            (args.allow_public_live, "--allow-public-live"),
            (args.ack_credentialed_wifi, "--ack-credentialed-wifi"),
            (args.ack_public_exposure, "--ack-public-exposure"),
            (args.force_ttl_expiry_proof, "--force-ttl-expiry-proof"),
            (args.force_manual_stop_proof, "--force-manual-stop-proof"),
        ):
            if enabled:
                argv.append(flag)
        argv.extend([
            "--native-confirm-token",
            args.native_confirm_token,
            "--public-confirm-token",
            args.public_confirm_token,
        ])
    return wsta80.build_arg_parser().parse_args(argv)


def append_step(result: dict[str, Any], name: str, payload: dict[str, Any], path: Path) -> None:
    workflow = result.setdefault("workflow", {})
    steps = workflow.setdefault("steps", {})
    steps[name] = {
        "decision": payload.get("decision"),
        "result": rel(path),
    }


def write_result(out_json: Path, result: dict[str, Any]) -> None:
    write_json(out_json, result)


def markdown(workflow: dict[str, Any]) -> str:
    lines = [
        "# WSTA Persistent Operator Workflow",
        "",
        f"- State: `{workflow.get('state')}`",
        f"- WSTA72: `{workflow.get('wsta72_decision')}`",
        f"- WSTA73: `{workflow.get('wsta73_decision')}`",
        f"- WSTA75: `{workflow.get('wsta75_decision')}`",
        f"- WSTA76: `{workflow.get('wsta76_decision')}`",
        f"- WSTA77: `{workflow.get('wsta77_decision')}`",
        f"- WSTA78: `{workflow.get('wsta78_decision')}`",
        f"- WSTA79: `{workflow.get('wsta79_decision')}`",
        f"- WSTA80 preflight: `{workflow.get('wsta80_preflight_decision')}`",
        f"- WSTA80 live: `{workflow.get('wsta80_live_decision')}`",
        "- Default public state: `PUBLIC_OFF`",
        f"- Live execution requested: `{str(bool(workflow.get('live_execution_requested'))).lower()}`",
        "",
        "## Key Artifacts",
        "",
        f"- WSTA72 prepare-to-arm: `{workflow.get('wsta72_prepare_to_arm')}`",
        f"- WSTA73 arming packet: `{workflow.get('wsta73_arming_packet')}`",
        f"- WSTA75 inventory: `{workflow.get('wsta75_arming_inventory')}`",
        f"- WSTA76 launch brief: `{workflow.get('wsta76_launch_brief')}`",
        f"- WSTA77 launch summary: `{workflow.get('wsta77_launch_summary')}`",
        f"- WSTA78 operator packet: `{workflow.get('wsta78_operator_packet')}`",
        f"- WSTA79 operator packet status: `{workflow.get('wsta79_operator_packet_status')}`",
        f"- WSTA80 execute gate: `{workflow.get('wsta80_execute_gate')}`",
        "",
        "This wrapper stops before live execution unless the explicit WSTA80/WSTA58 live gate flags are supplied.",
        "",
    ]
    return "\n".join(lines)


def classify(decisions: dict[str, Any], live: bool) -> str:
    expected = {
        "wsta72": wsta72.PASS_DECISION,
        "wsta73": wsta73.PASS_DECISION,
        "wsta75": wsta75.PASS_DECISION,
        "wsta76": wsta76.PASS_DECISION,
        "wsta77": wsta77.PASS_DECISION,
        "wsta78": wsta78.PASS_DECISION,
        "wsta79": wsta79.PASS_DECISION,
        "wsta80_preflight": wsta80.PREFLIGHT_DECISION,
    }
    for key, expected_decision in expected.items():
        if decisions.get(key) != expected_decision:
            return f"wsta88-blocked-{key}"
    if live:
        if decisions.get("wsta80_live") == wsta80.PASS_DECISION:
            return PASS_DECISION
        return "wsta88-blocked-wsta80-live"
    return PREFLIGHT_DECISION


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta88-persistent-operator-workflow-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA88 one-command persistent operator workflow",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta88-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(args),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta88-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta88_operator_workflow.json"
    out_md = run_dir / "wsta88_operator_workflow.md"

    gate_ok, gate_decision, gate_detail = validate_gate(args)
    result["gate_decision"] = gate_decision
    result["gate_detail"] = gate_detail
    if not gate_ok:
        result["decision"] = gate_decision
        result["checks"] = {
            "default_public_off": True,
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        result["ended_utc"] = utc_stamp()
        write_result(out_json, result)
        return result

    paths = workflow_paths(run_dir)
    decisions: dict[str, Any] = {}
    ttl_sec = int(gate_detail["ttl_sec"])

    w72 = wsta72.run(wsta72_args(paths["wsta72"], args, ttl_sec))
    decisions["wsta72"] = w72.get("decision")
    append_step(result, "wsta72", w72, paths["wsta72"] / "wsta72_prepare_to_arm.json")
    write_result(out_json, result)

    w73: dict[str, Any] = {}
    if decisions["wsta72"] == wsta72.PASS_DECISION:
        w73 = wsta73.run(wsta73_args(
            paths["wsta73"],
            paths["wsta72"] / "wsta72_prepare_to_arm.json",
            args,
        ))
    decisions["wsta73"] = w73.get("decision")
    append_step(result, "wsta73", w73, paths["wsta73"] / "wsta73_arming_packet.json")
    write_result(out_json, result)

    w75: dict[str, Any] = {}
    if decisions["wsta73"] == wsta73.PASS_DECISION:
        w75 = wsta75.run(wsta75_args(paths["wsta75"], run_dir, args))
    decisions["wsta75"] = w75.get("decision")
    append_step(result, "wsta75", w75, paths["wsta75"] / "wsta75_arming_inventory.json")
    write_result(out_json, result)

    w76: dict[str, Any] = {}
    if decisions["wsta75"] == wsta75.PASS_DECISION:
        w76 = wsta76.run(wsta76_args(
            paths["wsta76"],
            paths["wsta75"] / "wsta75_arming_inventory.json",
            args,
        ))
    decisions["wsta76"] = w76.get("decision")
    append_step(result, "wsta76", w76, paths["wsta76"] / "wsta76_launch_brief.json")
    write_result(out_json, result)

    w77: dict[str, Any] = {}
    if decisions["wsta76"] == wsta76.PASS_DECISION:
        w77 = wsta77.run(wsta77_args(paths["wsta77"], run_dir, args))
    decisions["wsta77"] = w77.get("decision")
    append_step(result, "wsta77", w77, paths["wsta77"] / "wsta77_launch_brief_summary.json")
    write_result(out_json, result)

    w78: dict[str, Any] = {}
    if decisions["wsta77"] == wsta77.PASS_DECISION:
        w78 = wsta78.run(wsta78_args(
            paths["wsta78"],
            paths["wsta77"] / "wsta77_launch_brief_summary.json",
            args,
        ))
    decisions["wsta78"] = w78.get("decision")
    append_step(result, "wsta78", w78, paths["wsta78"] / "wsta78_operator_packet.json")
    write_result(out_json, result)

    w79: dict[str, Any] = {}
    if decisions["wsta78"] == wsta78.PASS_DECISION:
        w79 = wsta79.run(wsta79_args(
            paths["wsta79"],
            paths["wsta78"] / "wsta78_operator_packet.json",
            args,
        ))
    decisions["wsta79"] = w79.get("decision")
    append_step(result, "wsta79", w79, paths["wsta79"] / "wsta79_operator_packet_status.json")
    write_result(out_json, result)

    w80_preflight: dict[str, Any] = {}
    if decisions["wsta79"] == wsta79.PASS_DECISION:
        w80_preflight = wsta80.run(wsta80_args(
            paths["wsta80_preflight"],
            paths["wsta79"] / "wsta79_operator_packet_status.json",
            args,
            live=False,
        ))
    decisions["wsta80_preflight"] = w80_preflight.get("decision")
    append_step(result, "wsta80_preflight", w80_preflight, paths["wsta80_preflight"] / "wsta80_execute_gate.json")
    result["wsta80_redacted"] = wsta80.public_summary(w80_preflight) if w80_preflight else {}
    write_result(out_json, result)

    live = live_requested(args)
    live_gate_ok = False
    w80_live: dict[str, Any] = {}
    if live and decisions["wsta80_preflight"] == wsta80.PREFLIGHT_DECISION:
        live_gate_ok, _ = wsta80.explicit_live_gate(wsta80_args(
            paths["wsta80_live"],
            paths["wsta79"] / "wsta79_operator_packet_status.json",
            args,
            live=True,
        ))
        w80_live = wsta80.run(wsta80_args(
            paths["wsta80_live"],
            paths["wsta79"] / "wsta79_operator_packet_status.json",
            args,
            live=True,
        ))
    decisions["wsta80_live"] = w80_live.get("decision")
    if w80_live:
        append_step(result, "wsta80_live", w80_live, paths["wsta80_live"] / "wsta80_execute_gate.json")
        result["wsta80_redacted"] = wsta80.public_summary(w80_live)

    workflow = result.setdefault("workflow", {})
    workflow.update({
        "state": "READY_FOR_EXPLICIT_WSTA58_LIVE_GATE" if decisions.get("wsta80_preflight") == wsta80.PREFLIGHT_DECISION else "NOT_READY",
        "ttl_sec": ttl_sec,
        "ready_index": args.ready_index,
        "wsta72_decision": decisions.get("wsta72"),
        "wsta73_decision": decisions.get("wsta73"),
        "wsta75_decision": decisions.get("wsta75"),
        "wsta76_decision": decisions.get("wsta76"),
        "wsta77_decision": decisions.get("wsta77"),
        "wsta78_decision": decisions.get("wsta78"),
        "wsta79_decision": decisions.get("wsta79"),
        "wsta80_preflight_decision": decisions.get("wsta80_preflight"),
        "wsta80_live_decision": decisions.get("wsta80_live"),
        "wsta72_prepare_to_arm": rel(paths["wsta72"] / "wsta72_prepare_to_arm.json"),
        "wsta73_arming_packet": rel(paths["wsta73"] / "wsta73_arming_packet.json"),
        "wsta75_arming_inventory": rel(paths["wsta75"] / "wsta75_arming_inventory.json"),
        "wsta76_launch_brief": rel(paths["wsta76"] / "wsta76_launch_brief.json"),
        "wsta77_launch_summary": rel(paths["wsta77"] / "wsta77_launch_brief_summary.json"),
        "wsta78_operator_packet": rel(paths["wsta78"] / "wsta78_operator_packet.json"),
        "wsta79_operator_packet_status": rel(paths["wsta79"] / "wsta79_operator_packet_status.json"),
        "wsta80_execute_gate": rel(paths["wsta80_preflight"] / "wsta80_execute_gate.json"),
        "default_public_off": True,
        "live_execution_requested": live,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    })
    result["checks"] = {
        "wsta72_pass": decisions.get("wsta72") == wsta72.PASS_DECISION,
        "wsta73_pass": decisions.get("wsta73") == wsta73.PASS_DECISION,
        "wsta75_pass": decisions.get("wsta75") == wsta75.PASS_DECISION,
        "wsta76_pass": decisions.get("wsta76") == wsta76.PASS_DECISION,
        "wsta77_pass": decisions.get("wsta77") == wsta77.PASS_DECISION,
        "wsta78_pass": decisions.get("wsta78") == wsta78.PASS_DECISION,
        "wsta79_pass": decisions.get("wsta79") == wsta79.PASS_DECISION,
        "wsta80_preflight_pass": decisions.get("wsta80_preflight") == wsta80.PREFLIGHT_DECISION,
        "wsta80_live_pass": decisions.get("wsta80_live") == wsta80.PASS_DECISION,
        "default_public_off": True,
        "live_execution_requested": live,
        "explicit_live_gate": live_gate_ok,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["decision"] = classify(decisions, live)
    result["gate_decision"] = "ok" if result["decision"] in {PREFLIGHT_DECISION, PASS_DECISION} else result["decision"]
    result["safety"] = safety_flags(args, live_gate_ok)

    md_text = markdown(workflow)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta88-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings + md_findings))}
        result["ended_utc"] = utc_stamp()
        write_result(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_result(out_json, result)
    if result["decision"] in {PREFLIGHT_DECISION, PASS_DECISION}:
        write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--ttl-sec", type=int, default=wsta72.SHORT_SESSION_MAX_TTL_SEC)
    parser.add_argument("--prepare-to-execute", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token-source", default="")
    parser.add_argument("--public-confirm-token-source", default="")
    parser.add_argument("--ready-index", type=int, default=0)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=wsta72.wsta71.wsta65.DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
    parser.add_argument("--max-sessions", type=int, default=wsta72.wsta67.DEFAULT_MAX_SESSIONS)
    parser.add_argument("--max-retire-markers", type=int, default=wsta72.wsta67.DEFAULT_MAX_SESSIONS)
    parser.add_argument("--max-packets", type=int, default=wsta75.DEFAULT_MAX_PACKETS)
    parser.add_argument("--max-briefs", type=int, default=wsta77.DEFAULT_MAX_BRIEFS)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--execute-wsta58-from-status", action="store_true")
    parser.add_argument("--allow-operator-live", action="store_true")
    parser.add_argument("--allow-native-reboot", action="store_true")
    parser.add_argument("--allow-public-live", action="store_true")
    parser.add_argument("--force-ttl-expiry-proof", action="store_true")
    parser.add_argument("--force-manual-stop-proof", action="store_true")
    parser.add_argument("--native-confirm-token", default="")
    parser.add_argument("--public-confirm-token", default="")
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
        payload = {"decision": "wsta88-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") in {PREFLIGHT_DECISION, PASS_DECISION} else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
