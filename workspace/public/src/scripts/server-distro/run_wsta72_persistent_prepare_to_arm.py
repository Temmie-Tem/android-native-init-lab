#!/usr/bin/env python3
"""WSTA72 host-only persistent prepare-to-arm orchestrator.

WSTA72 composes the default-off persistent exposure preparation ladder into one
operator command:

* WSTA63 prepares a fresh short persistent session;
* WSTA64 audits readiness;
* WSTA67 inventories the local run tree;
* WSTA69 renders an operator snapshot;
* WSTA70 selects one READY candidate and emits a launch manifest; and
* WSTA71 performs the last-moment launch-readiness audit.

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

import run_wsta63_persistent_session_controller as wsta63  # noqa: E402
import run_wsta64_persistent_session_readiness_audit as wsta64  # noqa: E402
import run_wsta67_persistent_session_inventory as wsta67  # noqa: E402
import run_wsta69_persistent_session_snapshot as wsta69  # noqa: E402
import run_wsta70_persistent_session_launch_manifest as wsta70  # noqa: E402
import run_wsta71_persistent_launch_readiness_audit as wsta71  # noqa: E402


REPO_ROOT = wsta71.REPO_ROOT
PRIVATE_ROOT = wsta71.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta71.DEFAULT_RUN_BASE
PASS_DECISION = "wsta72-persistent-prepare-to-arm-pass"
SHORT_SESSION_MAX_TTL_SEC = wsta63.SHORT_SESSION_MAX_TTL_SEC


def rel(path: Path) -> str:
    return wsta71.rel(path)


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
    return wsta71.is_under(path, root)


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
        "scope": "WSTA72 host-only persistent prepare-to-arm orchestrator",
        "default_mode": "fail-closed-host-only",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--prepare-to-arm",
            "--ttl-sec",
            str(SHORT_SESSION_MAX_TTL_SEC),
            "--ack-credentialed-wifi",
            "--ack-public-exposure",
            "--native-confirm-token-source",
            "private",
            "--public-confirm-token-source",
            "private",
        ],
        "live_execution": "not-run-by-wsta72",
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "pipeline": result.get("pipeline", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta71.redaction_findings(payload)


def validate_gate(args: argparse.Namespace) -> tuple[bool, str, dict[str, Any]]:
    if not args.prepare_to_arm:
        return False, "wsta72-blocked-prepare-to-arm-required", {}
    try:
        ttl_sec = int(args.ttl_sec)
    except (TypeError, ValueError):
        return False, "wsta72-blocked-ttl-invalid", {"ttl_sec": args.ttl_sec}
    if ttl_sec <= 0 or ttl_sec > SHORT_SESSION_MAX_TTL_SEC:
        return False, "wsta72-blocked-ttl-not-short", {
            "ttl_sec": ttl_sec,
            "short_session_max_ttl_sec": SHORT_SESSION_MAX_TTL_SEC,
        }
    if not args.ack_credentialed_wifi:
        return False, "wsta72-blocked-credentialed-wifi-ack-required", {}
    if not args.ack_public_exposure:
        return False, "wsta72-blocked-public-exposure-ack-required", {}
    if args.native_confirm_token_source != "private":
        return False, "wsta72-blocked-native-confirm-token-private-source-required", {}
    if args.public_confirm_token_source != "private":
        return False, "wsta72-blocked-public-confirm-token-private-source-required", {}
    return True, "ok", {"ttl_sec": ttl_sec}


def wsta63_args(run_dir: Path, ttl_sec: int, args: argparse.Namespace) -> argparse.Namespace:
    return wsta63.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--prepare-session",
        "--ttl-sec",
        str(ttl_sec),
        "--ack-credentialed-wifi",
        "--ack-public-exposure",
        "--native-confirm-token-source",
        "private",
        "--public-confirm-token-source",
        "private",
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ])


def wsta64_args(run_dir: Path, wsta63_result: Path) -> argparse.Namespace:
    return wsta64.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--wsta63-result-json",
        str(wsta63_result),
    ])


def wsta67_args(run_dir: Path, scan_root: Path, args: argparse.Namespace) -> argparse.Namespace:
    return wsta67.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--scan-root",
        str(scan_root),
        "--max-sessions",
        str(args.max_sessions),
        "--max-retire-markers",
        str(args.max_retire_markers),
    ])


def wsta69_args(run_dir: Path, inventory_path: Path) -> argparse.Namespace:
    return wsta69.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--wsta67-inventory-json",
        str(inventory_path),
    ])


def wsta70_args(run_dir: Path, inventory_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    return wsta70.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--wsta67-inventory-json",
        str(inventory_path),
        "--ready-index",
        str(args.ready_index),
    ])


def wsta71_args(run_dir: Path, launch_path: Path, args: argparse.Namespace) -> argparse.Namespace:
    return wsta71.build_arg_parser().parse_args([
        "--run-dir",
        str(run_dir),
        "--wsta70-launch-manifest-json",
        str(launch_path),
        "--min-initial-seconds-remaining",
        str(args.min_initial_seconds_remaining),
    ])


def pipeline_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "wsta63": run_dir / "wsta63",
        "wsta64": run_dir / "wsta64",
        "wsta67": run_dir / "wsta67-inventory",
        "wsta69": run_dir / "wsta69-snapshot",
        "wsta70": run_dir / "wsta70-launch",
        "wsta71": run_dir / "wsta71-readiness",
    }


def classify(decisions: dict[str, Any]) -> str:
    if decisions.get("wsta63") != wsta63.PASS_DECISION:
        return "wsta72-blocked-wsta63"
    if decisions.get("wsta64") != wsta64.PASS_DECISION:
        return "wsta72-blocked-wsta64"
    if decisions.get("wsta67") != wsta67.PASS_DECISION:
        return "wsta72-blocked-wsta67"
    if decisions.get("wsta69") != wsta69.PASS_DECISION:
        return "wsta72-blocked-wsta69"
    if decisions.get("wsta70") != wsta70.PASS_DECISION:
        return "wsta72-blocked-wsta70"
    if decisions.get("wsta71") != wsta71.PASS_DECISION:
        return "wsta72-blocked-wsta71"
    return PASS_DECISION


def markdown(pipeline: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in pipeline.get("wsta58_live_command_template") or [])
    lines = [
        "# WSTA Persistent Prepare-To-Arm",
        "",
        f"- State: `{pipeline.get('state')}`",
        f"- WSTA63: `{pipeline.get('wsta63_decision')}`",
        f"- WSTA64: `{pipeline.get('wsta64_decision')}`",
        f"- WSTA67: `{pipeline.get('wsta67_decision')}`",
        f"- WSTA69: `{pipeline.get('wsta69_decision')}`",
        f"- WSTA70: `{pipeline.get('wsta70_decision')}`",
        f"- WSTA71: `{pipeline.get('wsta71_decision')}`",
        f"- Initial seconds remaining: `{pipeline.get('initial_seconds_remaining')}`",
        "- Live execution requested: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Key Artifacts",
        "",
        f"- WSTA63 result: `{pipeline.get('wsta63_result')}`",
        f"- WSTA64 result: `{pipeline.get('wsta64_result')}`",
        f"- Inventory: `{pipeline.get('wsta67_inventory')}`",
        f"- Snapshot: `{pipeline.get('wsta69_snapshot')}`",
        f"- Launch manifest: `{pipeline.get('wsta70_launch_manifest')}`",
        f"- Launch readiness: `{pipeline.get('wsta71_launch_readiness')}`",
        "",
        "## WSTA58 Command Template",
        "",
        "```text",
        command,
        "```",
        "",
        "This orchestrator stops before live execution. Replace placeholders only when explicitly running WSTA58.",
        "",
    ]
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = utc_now()
    ts = utc_stamp(started)
    run_id = args.run_id or f"wsta72-persistent-prepare-to-arm-{ts}"
    run_dir = args.run_dir or (DEFAULT_RUN_BASE / run_id)
    run_dir = resolve_path(run_dir)
    result: dict[str, Any] = {
        "scope": "WSTA72 host-only persistent prepare-to-arm orchestrator",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta72-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta72-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta72_prepare_to_arm.json"
    out_md = run_dir / "wsta72_prepare_to_arm.md"

    gate_ok, gate_decision, gate_detail = validate_gate(args)
    result["gate_decision"] = gate_decision
    result["gate_detail"] = gate_detail
    if not gate_ok:
        result["decision"] = gate_decision
        result["checks"] = {
            "live_execution_requested": False,
            "public_url_value_logged": False,
            "secret_values_logged": 0,
        }
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    paths = pipeline_paths(run_dir)
    ttl_sec = int(gate_detail["ttl_sec"])

    w63 = wsta63.run(wsta63_args(paths["wsta63"], ttl_sec, args))
    wsta63_result = paths["wsta63"] / "wsta63_result.json"
    w64: dict[str, Any] = {}
    if w63.get("decision") == wsta63.PASS_DECISION:
        w64 = wsta64.run(wsta64_args(paths["wsta64"], wsta63_result))
    wsta64_result = paths["wsta64"] / "wsta64_result.json"

    w67: dict[str, Any] = {}
    w69: dict[str, Any] = {}
    w70: dict[str, Any] = {}
    w71: dict[str, Any] = {}
    inventory_path = paths["wsta67"] / "wsta67_inventory.json"
    snapshot_path = paths["wsta69"] / "wsta69_snapshot.json"
    launch_path = paths["wsta70"] / "wsta70_launch_manifest.json"
    readiness_path = paths["wsta71"] / "wsta71_launch_readiness.json"

    if w64.get("decision") == wsta64.PASS_DECISION:
        w67 = wsta67.run(wsta67_args(paths["wsta67"], run_dir, args))
    if w67.get("decision") == wsta67.PASS_DECISION:
        w69 = wsta69.run(wsta69_args(paths["wsta69"], inventory_path))
        w70 = wsta70.run(wsta70_args(paths["wsta70"], inventory_path, args))
    if w70.get("decision") == wsta70.PASS_DECISION:
        w71 = wsta71.run(wsta71_args(paths["wsta71"], launch_path, args))

    decisions = {
        "wsta63": w63.get("decision"),
        "wsta64": w64.get("decision"),
        "wsta67": w67.get("decision"),
        "wsta69": w69.get("decision"),
        "wsta70": w70.get("decision"),
        "wsta71": w71.get("decision"),
    }
    readiness = w71.get("readiness") or {}
    pipeline = {
        "state": "READY_TO_ARM_DEFAULT_OFF" if decisions["wsta71"] == wsta71.PASS_DECISION else "NOT_READY",
        "ttl_sec": ttl_sec,
        "ready_index": args.ready_index,
        "wsta63_decision": decisions["wsta63"],
        "wsta64_decision": decisions["wsta64"],
        "wsta67_decision": decisions["wsta67"],
        "wsta69_decision": decisions["wsta69"],
        "wsta70_decision": decisions["wsta70"],
        "wsta71_decision": decisions["wsta71"],
        "wsta63_result": rel(wsta63_result),
        "wsta64_result": rel(wsta64_result),
        "wsta67_inventory": rel(inventory_path),
        "wsta69_snapshot": rel(snapshot_path),
        "wsta70_launch_manifest": rel(launch_path),
        "wsta71_launch_readiness": rel(readiness_path),
        "initial_seconds_remaining": readiness.get("initial_seconds_remaining"),
        "wsta58_live_command_template": readiness.get("live_command_template") or [],
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["pipeline"] = pipeline
    result["checks"] = {
        "wsta63_pass": decisions["wsta63"] == wsta63.PASS_DECISION,
        "wsta64_pass": decisions["wsta64"] == wsta64.PASS_DECISION,
        "wsta67_pass": decisions["wsta67"] == wsta67.PASS_DECISION,
        "wsta69_pass": decisions["wsta69"] == wsta69.PASS_DECISION,
        "wsta70_pass": decisions["wsta70"] == wsta70.PASS_DECISION,
        "wsta71_pass": decisions["wsta71"] == wsta71.PASS_DECISION,
        "default_public_off": True,
        "live_execution_requested": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["decision"] = classify(decisions)
    if result["decision"] == PASS_DECISION:
        result["gate_decision"] = "ok"

    md_text = markdown(pipeline)
    findings = redaction_findings(public_summary(result))
    md_findings = redaction_findings({"markdown": md_text})
    if findings or md_findings:
        result["decision"] = "wsta72-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings + md_findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    if result["decision"] == PASS_DECISION:
        write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--ttl-sec", type=int, default=SHORT_SESSION_MAX_TTL_SEC)
    parser.add_argument("--prepare-to-arm", action="store_true")
    parser.add_argument("--ack-credentialed-wifi", action="store_true")
    parser.add_argument("--ack-public-exposure", action="store_true")
    parser.add_argument("--native-confirm-token-source", default="")
    parser.add_argument("--public-confirm-token-source", default="")
    parser.add_argument("--ready-index", type=int, default=0)
    parser.add_argument("--min-initial-seconds-remaining", type=int, default=wsta71.wsta65.DEFAULT_MIN_INITIAL_SECONDS_REMAINING)
    parser.add_argument("--max-sessions", type=int, default=wsta67.DEFAULT_MAX_SESSIONS)
    parser.add_argument("--max-retire-markers", type=int, default=wsta67.DEFAULT_MAX_SESSIONS)
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
        payload = {"decision": "wsta72-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
