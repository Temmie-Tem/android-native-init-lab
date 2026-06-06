#!/usr/bin/env python3
"""V457 Wi-Fi operator session outcome gate.

V457 is host-side only.  It reads V456/V447/V452 evidence and summarizes the
current one-session Wi-Fi handoff outcome without reading Wi-Fi secrets,
executing generated scripts, or touching the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v457-wifi-operator-session-outcome")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
READY_PACKET_DECISIONS = {
    "v456-operator-one-session-packet-ready",
    "v459-nm-profile-handoff-packet-ready",
}
PREFLIGHT_READY_DECISION = "v447-explicit-connect-flow-preflight-ready"
LIVE_PASS_DECISION = "v447-explicit-connect-flow-live-pass"
CLEANUP_PASS_DECISION = "v452-wifi-live-cleanup-proof-pass"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--wifi-root", type=Path, default=DEFAULT_WIFI_ROOT)
    parser.add_argument("--include-synthetic", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def ignored_candidate(path: Path, include_synthetic: bool) -> bool:
    if include_synthetic:
        return False
    text = str(path)
    return any(token in text for token in ("synthetic", "env-missing", "-plan-", "-dryrun-", "missing-policy"))


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "invalid", "pass": False, "error": str(exc)}
    payload["_path"] = str(path)
    payload["_run_dir"] = str(path.parent)
    try:
        payload["_mtime"] = path.stat().st_mtime
    except OSError:
        payload["_mtime"] = 0.0
    return payload


def latest(root: Path, pattern: str, include_synthetic: bool = False) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for path in repo_path(root).glob(pattern):
        if path.name != "manifest.json":
            continue
        if ignored_candidate(path, include_synthetic):
            continue
        rows.append(load_json(path))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def latest_v456(root: Path) -> dict[str, Any] | None:
    return latest(root, "v456-operator-one-session-packet-run*/manifest.json", include_synthetic=True)


def latest_operator_packet(root: Path) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for pattern in (
        "v456-operator-one-session-packet-run*/manifest.json",
        "v459-nm-profile-handoff-packet-run*/manifest.json",
    ):
        row = latest(root, pattern, include_synthetic=True)
        if row:
            rows.append(row)
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def nested_v445(live: dict[str, Any] | None) -> dict[str, Any]:
    if not live:
        return {}
    context = live.get("context") or {}
    nested = context.get("v445") or {}
    if nested:
        return nested
    run_dir = live.get("_run_dir")
    if run_dir:
        candidate = Path(run_dir) / "v445-android-wifi-explicit-connect-live" / "manifest.json"
        if candidate.exists():
            return load_json(candidate)
    return {}


def packet_command(packet: dict[str, Any] | None) -> str:
    payload = (packet or {}).get("packet") or {}
    return str(payload.get("nm_profile_command") or payload.get("one_session_command") or payload.get("preflight_command") or "")


def newest_payload(*payloads: dict[str, Any] | None) -> dict[str, Any] | None:
    rows = [item for item in payloads if item]
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def evidence_state(args: argparse.Namespace) -> dict[str, Any]:
    root = args.wifi_root
    live = latest(root, "v447-explicit-connect-flow-live-*/manifest.json", include_synthetic=args.include_synthetic)
    preflight = latest(root, "v447-explicit-connect-flow-private-preflight-*/manifest.json", include_synthetic=args.include_synthetic)
    stale_live = None
    if live and preflight and float(live.get("_mtime") or 0.0) < float(preflight.get("_mtime") or 0.0):
        stale_live = live
        live = None
    return {
        "operator_packet": latest_operator_packet(root),
        "v456": latest_v456(root),
        "preflight": preflight,
        "live": live,
        "stale_live": stale_live,
        "nested_v445": nested_v445(live),
        "cleanup": latest(root, "v452-wifi-live-cleanup-proof-*/manifest.json", include_synthetic=args.include_synthetic),
        "router_after_preflight": latest(root, "v449-wifi-handoff-result-router-after-preflight-*/manifest.json", include_synthetic=True),
        "readiness_after_preflight": latest(root, "v450-operator-preflight-readiness-after-preflight-*/manifest.json", include_synthetic=True),
        "cleanup_after_preflight": latest(root, "v452-wifi-live-cleanup-proof-after-preflight-*/manifest.json", include_synthetic=True),
        "router_after_live": latest(root, "v449-wifi-handoff-result-router-after-live-*/manifest.json", include_synthetic=True),
        "readiness_after_live": latest(root, "v450-operator-preflight-readiness-after-live-*/manifest.json", include_synthetic=True),
        "cleanup_after_live": latest(root, "v452-wifi-live-cleanup-proof-after-live-*/manifest.json", include_synthetic=True),
    }


def classify(command: str, state: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v457-wifi-operator-session-outcome-plan-ready",
            "pass": True,
            "reason": "operator session outcome gate plan generated",
            "next_gate": "run V457 after V456 packet generation or after the operator one-session script",
            "recommended_command": "",
        }

    packet = state.get("operator_packet") or state.get("v456")
    preflight = state.get("preflight")
    live = state.get("live")
    cleanup = newest_payload(state.get("cleanup_after_live"), state.get("cleanup"))
    command_text = packet_command(packet)

    if not packet:
        return {
            "decision": "v457-wifi-session-needs-v456-packet",
            "pass": False,
            "reason": "no V456/V459 operator handoff packet exists",
            "next_gate": "generate V459 saved-profile handoff packet or V456 one-session packet",
            "recommended_command": "python3 scripts/revalidation/wifi_operator_nm_profile_handoff_v459.py run",
        }
    if packet.get("decision") not in READY_PACKET_DECISIONS or packet.get("pass") is not True:
        return {
            "decision": "v457-wifi-session-v456-not-ready",
            "pass": False,
            "reason": str(packet.get("reason") or "latest operator handoff packet did not pass"),
            "next_gate": "repair or regenerate V459/V456 operator handoff packet",
            "recommended_command": "",
        }
    if not preflight and not live:
        return {
            "decision": "v457-wifi-session-awaiting-operator",
            "pass": True,
            "reason": "operator handoff packet is ready but no real V447 preflight/live evidence exists yet",
            "next_gate": "run generated operator script and provide local Wi-Fi input",
            "recommended_command": command_text,
        }
    if preflight and (preflight.get("decision") != PREFLIGHT_READY_DECISION or preflight.get("pass") is not True):
        return {
            "decision": "v457-wifi-session-preflight-blocked",
            "pass": False,
            "reason": str(preflight.get("reason") or "latest V447 private preflight did not pass"),
            "next_gate": "inspect preflight evidence and repair before retry",
            "recommended_command": command_text,
        }
    if not live:
        return {
            "decision": "v457-wifi-session-preflight-pass-live-pending",
            "pass": True,
            "reason": "latest V447 private preflight passed but live evidence does not exist yet",
            "next_gate": "rerun one-session script and type V447-LIVE after preflight passes, or use routed live command",
            "recommended_command": command_text,
        }
    if live.get("decision") != LIVE_PASS_DECISION or live.get("pass") is not True:
        nested = state.get("nested_v445") or {}
        return {
            "decision": "v457-wifi-session-live-blocked",
            "pass": False,
            "reason": str(live.get("reason") or nested.get("reason") or "latest V447 live evidence did not pass"),
            "next_gate": "inspect latest V447/V445 live evidence before retry",
            "recommended_command": "python3 scripts/revalidation/wifi_handoff_result_router_v449.py run",
        }
    if cleanup and cleanup.get("decision") == CLEANUP_PASS_DECISION and cleanup.get("pass") is True:
        return {
            "decision": "v457-wifi-session-live-cleanup-pass",
            "pass": True,
            "reason": "latest V447 live evidence passed and V452 cleanup proof passed",
            "next_gate": "plan bounded Wi-Fi stability or server binding policy",
            "recommended_command": "",
        }
    return {
        "decision": "v457-wifi-session-cleanup-proof-pending",
        "pass": False,
        "reason": "latest V447 live evidence passed but V452 cleanup proof is missing or not passing",
        "next_gate": "run V452 cleanup proof on latest live evidence before stability/server work",
        "recommended_command": "python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py run",
    }


def manifest_row(name: str, payload: dict[str, Any] | None) -> list[str]:
    if not payload:
        return [name, "-", "-", "-", "-"]
    return [
        name,
        str(payload.get("decision") or "-"),
        str(payload.get("pass")),
        str(payload.get("_run_dir") or "-"),
        str(payload.get("reason") or "-"),
    ]


def guardrails() -> list[str]:
    return [
        "host-side evidence summary only",
        "does not read Wi-Fi secret env values",
        "does not execute generated operator scripts",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    state = manifest["state"]
    rows = [
        manifest_row("v456_packet", state.get("v456")),
        manifest_row("operator_packet", state.get("operator_packet")),
        manifest_row("v447_private_preflight", state.get("preflight")),
        manifest_row("v447_live", state.get("live")),
        manifest_row("v447_stale_live", state.get("stale_live")),
        manifest_row("nested_v445", state.get("nested_v445")),
        manifest_row("v452_cleanup", state.get("cleanup")),
        manifest_row("v449_after_preflight", state.get("router_after_preflight")),
        manifest_row("v450_after_preflight", state.get("readiness_after_preflight")),
        manifest_row("v452_after_preflight", state.get("cleanup_after_preflight")),
        manifest_row("v449_after_live", state.get("router_after_live")),
        manifest_row("v450_after_live", state.get("readiness_after_live")),
        manifest_row("v452_after_live", state.get("cleanup_after_live")),
    ]
    return "\n".join(
        [
            "# V457 Wi-Fi Operator Session Outcome",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- recommended_command: `{manifest['classification'].get('recommended_command') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence State",
            "",
            markdown_table(["item", "decision", "pass", "run_dir", "reason"], rows),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    state = evidence_state(args) if args.command == "run" else {}
    classification = classify(args.command, state)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "state": state,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {classification['next_gate']}")
    if classification.get("recommended_command"):
        print(f"recommended_command: {classification['recommended_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
