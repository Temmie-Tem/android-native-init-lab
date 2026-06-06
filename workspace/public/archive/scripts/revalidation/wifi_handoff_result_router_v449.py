#!/usr/bin/env python3
"""V449 Wi-Fi handoff result router.

V449 is host-side only.  It reads V448/V447/V445 evidence and tells the
operator the next safe action without requiring Wi-Fi secrets, device access, or
manual manifest spelunking.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v449-wifi-handoff-result-router")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
READY_PACKET_DECISIONS = {
    "v448-operator-handoff-packet-ready",
    "v453-operator-postroute-packet-ready",
    "v454-operator-strict-postroute-packet-ready",
    "v456-operator-one-session-packet-ready",
    "v459-nm-profile-handoff-packet-ready",
}


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


def load_manifest(path: Path) -> dict[str, Any]:
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


def ignored_candidate(path: Path, include_synthetic: bool) -> bool:
    text = str(path)
    if include_synthetic:
        return False
    return any(token in text for token in ("synthetic", "env-missing", "-plan-", "-dryrun-", "missing-policy"))


def manifests(root: Path, pattern: str, include_synthetic: bool = False) -> list[dict[str, Any]]:
    resolved = repo_path(root)
    rows = []
    for path in resolved.glob(pattern):
        if path.name != "manifest.json":
            continue
        if ignored_candidate(path, include_synthetic):
            continue
        rows.append(load_manifest(path))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows


def latest(root: Path, pattern: str, include_synthetic: bool = False) -> dict[str, Any] | None:
    rows = manifests(root, pattern, include_synthetic)
    return rows[-1] if rows else None


def latest_packet(root: Path) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for pattern in (
        "v448-operator-handoff-packet-run*/manifest.json",
        "v453-operator-postroute-packet-run*/manifest.json",
        "v454-operator-strict-postroute-packet-run*/manifest.json",
        "v456-operator-one-session-packet-run*/manifest.json",
        "v459-nm-profile-handoff-packet-run*/manifest.json",
    ):
        rows.extend(manifests(root, pattern, include_synthetic=True))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def packet_commands(packet: dict[str, Any] | None) -> dict[str, str]:
    if not packet:
        return {}
    payload = packet.get("packet") or {}
    return {
        key: str(payload.get(key) or "")
        for key in (
            "preflight_command",
            "live_command",
            "preflight_script",
            "live_script",
            "one_session_command",
            "one_session_script",
            "nm_profile_command",
            "nm_profile_script",
        )
        if payload.get(key)
    }


def nested_v445(v447_live: dict[str, Any] | None) -> dict[str, Any]:
    if not v447_live:
        return {}
    context = v447_live.get("context") or {}
    return context.get("v445") or {}


def evidence_state(args: argparse.Namespace) -> dict[str, Any]:
    root = args.wifi_root
    packet = latest_packet(root)
    private_preflight = latest(root, "v447-explicit-connect-flow-private-preflight-*/manifest.json", include_synthetic=args.include_synthetic)
    live = latest(root, "v447-explicit-connect-flow-live-*/manifest.json", include_synthetic=args.include_synthetic)
    stale_live = None
    if live and private_preflight and float(live.get("_mtime") or 0.0) < float(private_preflight.get("_mtime") or 0.0):
        stale_live = live
        live = None
    return {
        "packet": packet,
        "private_preflight": private_preflight,
        "live": live,
        "stale_live": stale_live,
        "nested_v445": nested_v445(live),
        "packet_commands": packet_commands(packet),
    }


def classify(command: str, state: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v449-wifi-handoff-result-router-plan-ready",
            "pass": True,
            "reason": "handoff result router plan generated",
            "next_gate": "run V449 to route latest V448/V447/V445 evidence",
            "recommended_command": "",
        }

    packet = state.get("packet")
    preflight = state.get("private_preflight")
    live = state.get("live")
    nested = state.get("nested_v445") or {}
    commands = state.get("packet_commands") or {}

    if live:
        if live.get("decision") == "v447-explicit-connect-flow-live-pass" and live.get("pass") is True:
            return {
                "decision": "v449-wifi-live-pass-next-stability",
                "pass": True,
                "reason": "latest V447 live flow passed",
                "next_gate": "document live result and plan bounded Wi-Fi stability or server binding policy",
                "recommended_command": "",
            }
        return {
            "decision": "v449-wifi-live-failed-needs-triage",
            "pass": False,
            "reason": str(live.get("reason") or nested.get("reason") or "latest V447 live flow did not pass"),
            "next_gate": "inspect latest V447/V445 live evidence before retry",
            "recommended_command": "",
        }

    if preflight:
        if preflight.get("decision") == "v447-explicit-connect-flow-preflight-ready" and preflight.get("pass") is True:
            return {
                "decision": "v449-wifi-private-preflight-ready-run-live",
                "pass": True,
                "reason": "latest private V447 host preflight passed and V445 live was not run",
                "next_gate": "run V448 generated live script",
                "recommended_command": commands.get("live_command", ""),
            }
        return {
            "decision": "v449-wifi-private-preflight-blocked",
            "pass": False,
            "reason": str(preflight.get("reason") or "latest private V447 host preflight did not pass"),
            "next_gate": "inspect V447 preflight evidence and rerun host preflight after repair",
            "recommended_command": commands.get("preflight_command", ""),
        }

    if packet:
        if packet.get("decision") in READY_PACKET_DECISIONS and packet.get("pass") is True:
            return {
                "decision": "v449-wifi-handoff-packet-ready-run-preflight",
                "pass": True,
                "reason": "latest V448/V453/V454/V456/V459 handoff packet is ready and no private V447 preflight result exists yet",
                "next_gate": "run generated host preflight script",
                "recommended_command": commands.get("preflight_command", ""),
            }
        return {
            "decision": "v449-wifi-handoff-packet-blocked",
            "pass": False,
            "reason": str(packet.get("reason") or "latest V448 handoff packet did not pass"),
            "next_gate": "rerun or repair V448 packet generation",
            "recommended_command": "",
        }

    return {
        "decision": "v449-wifi-needs-handoff-packet",
        "pass": False,
        "reason": "no V448 handoff packet evidence was found",
        "next_gate": "run V448 packet generation first",
        "recommended_command": "python3 scripts/revalidation/wifi_operator_handoff_packet_v448.py run",
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
        "host-side evidence router only",
        "does not read Wi-Fi secret env values",
        "does not execute generated handoff scripts",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    state = manifest["state"]
    rows = [
        manifest_row("v448_packet", state.get("packet")),
        manifest_row("v447_private_preflight", state.get("private_preflight")),
        manifest_row("v447_live", state.get("live")),
        manifest_row("v447_stale_live", state.get("stale_live")),
        manifest_row("nested_v445", state.get("nested_v445")),
    ]
    commands = state.get("packet_commands") or {}
    command_rows = [[key, value] for key, value in commands.items()]
    return "\n".join(
        [
            "# V449 Wi-Fi Handoff Result Router",
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
            "## Packet Commands",
            "",
            markdown_table(["item", "value"], command_rows if command_rows else [["-", "-"]]),
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
    state = evidence_state(args) if args.command == "run" else {"packet_commands": {}}
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
