#!/usr/bin/env python3
"""V450 operator preflight readiness audit.

V450 is host-side only.  It verifies that the latest V448 handoff packet and
V449 routing state are safe for the operator to run, without reading Wi-Fi
secret env values or executing any generated handoff script.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v450-operator-preflight-readiness")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
READY_PACKET_DECISIONS = {
    "v448-operator-handoff-packet-ready",
    "v453-operator-postroute-packet-ready",
    "v454-operator-strict-postroute-packet-ready",
    "v456-operator-one-session-packet-ready",
    "v459-nm-profile-handoff-packet-ready",
}
SECRET_LITERAL_RE = re.compile(
    r"(?i)(codex-test-network|12345678|A90_WIFI_(?:SSID|PSK)=['\"][^'\"]+['\"]|"
    r"cmd\s+wifi\s+connect-network\s+\S+\s+(?:wpa2|wpa3)\s+\S+)"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--wifi-root", type=Path, default=DEFAULT_WIFI_ROOT)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


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


def latest_manifest(root: Path, pattern: str) -> dict[str, Any] | None:
    manifests = []
    for path in repo_path(root).glob(pattern):
        if path.name == "manifest.json":
            manifests.append(load_json(path))
    manifests.sort(key=lambda payload: float(payload.get("_mtime") or 0.0))
    return manifests[-1] if manifests else None


def latest_packet(root: Path) -> dict[str, Any] | None:
    manifests: list[dict[str, Any]] = []
    for pattern in (
        "v448-operator-handoff-packet-run*/manifest.json",
        "v453-operator-postroute-packet-run*/manifest.json",
        "v454-operator-strict-postroute-packet-run*/manifest.json",
        "v456-operator-one-session-packet-run*/manifest.json",
        "v459-nm-profile-handoff-packet-run*/manifest.json",
    ):
        for path in repo_path(root).glob(pattern):
            if path.name == "manifest.json":
                manifests.append(load_json(path))
    manifests.sort(key=lambda payload: float(payload.get("_mtime") or 0.0))
    return manifests[-1] if manifests else None


def env_state() -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(name, "")
        state[name] = {"present": name in os.environ, "length": len(value)}
    return state


def script_audit(path_text: str, expected_markers: list[str]) -> dict[str, Any]:
    path = Path(path_text)
    result: dict[str, Any] = {
        "path": path_text,
        "present": path.is_file(),
        "mode": "",
        "private_mode": False,
        "readable": False,
        "secret_literal_found": False,
        "markers": {},
        "issues": [],
    }
    if not path.is_file():
        result["issues"].append("script missing")
        return result
    mode = stat.S_IMODE(path.stat().st_mode)
    result["mode"] = oct(mode)
    result["private_mode"] = mode & 0o077 == 0
    if not result["private_mode"]:
        result["issues"].append("script is readable by group/other")
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        result["readable"] = True
    except Exception as exc:  # noqa: BLE001
        result["issues"].append(f"read failed: {exc}")
        return result
    result["secret_literal_found"] = bool(SECRET_LITERAL_RE.search(text))
    if result["secret_literal_found"]:
        result["issues"].append("secret-like literal or raw connect command found")
    for marker in expected_markers:
        result["markers"][marker] = marker in text
        if marker not in text:
            result["issues"].append(f"missing marker: {marker}")
    return result


def audit_scripts(packet: dict[str, Any] | None) -> dict[str, Any]:
    payload = (packet or {}).get("packet") or {}
    decision = str((packet or {}).get("decision") or "")
    if decision == "v459-nm-profile-handoff-packet-ready":
        preflight_markers = [
            "Select saved NetworkManager Wi-Fi profile number",
            "names and secrets are not printed",
            "nmcli",
            "trap cleanup EXIT",
            "wifi_explicit_connect_flow_v447.py",
            "--allow-read-wifi-env --i-understand-wifi-secret-env",
            "run",
        ]
    else:
        preflight_markers = [
            "read -r -p \"A90 Wi-Fi SSID: \" A90_WIFI_SSID",
            "read -r -s -p \"A90 Wi-Fi PSK: \" A90_WIFI_PSK",
            "trap cleanup EXIT",
            "wifi_explicit_connect_flow_v447.py",
            "--allow-read-wifi-env --i-understand-wifi-secret-env",
            "run",
        ]
    preflight = script_audit(
        str(payload.get("preflight_script") or ""),
        preflight_markers,
    )
    live = script_audit(
        str(payload.get("live_script") or ""),
        [
            "Type V447-LIVE",
            "--allow-live-v445",
            "--allow-android-boot-flash --assume-yes --i-understand-native-rollback",
            "--allow-explicit-scan-connect --i-understand-explicit-wifi-connect",
            "trap cleanup EXIT",
            "wifi_explicit_connect_flow_v447.py",
            "run",
        ],
    )
    return {
        "preflight": preflight,
        "live": live,
        "ok": not preflight["issues"] and not live["issues"],
    }


def route_state(args: argparse.Namespace) -> dict[str, Any]:
    packet = latest_packet(args.wifi_root)
    router = latest_manifest(args.wifi_root, "v449-wifi-handoff-result-router-*/manifest.json")
    private_preflight = latest_manifest(args.wifi_root, "v447-explicit-connect-flow-private-preflight-*/manifest.json")
    live = latest_manifest(args.wifi_root, "v447-explicit-connect-flow-live-*/manifest.json")
    stale_live = None
    if live and private_preflight and float(live.get("_mtime") or 0.0) < float(private_preflight.get("_mtime") or 0.0):
        stale_live = live
        live = None
    scripts = audit_scripts(packet)
    return {
        "packet": packet,
        "router": router,
        "private_preflight": private_preflight,
        "live": live,
        "stale_live": stale_live,
        "scripts": scripts,
        "env_state": env_state(),
    }


def classify(command: str, state: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v450-operator-preflight-readiness-plan-ready",
            "pass": True,
            "reason": "operator preflight readiness audit plan generated",
            "next_gate": "run V450 to verify generated handoff scripts before operator input",
            "recommended_command": "",
        }
    packet = state.get("packet")
    router = state.get("router")
    scripts = state.get("scripts") or {}
    private_preflight = state.get("private_preflight")
    live = state.get("live")
    if not packet:
        return {
            "decision": "v450-operator-preflight-needs-v448-packet",
            "pass": False,
            "reason": "no V448 packet evidence found",
            "next_gate": "run V448 packet generation",
            "recommended_command": "python3 scripts/revalidation/wifi_operator_handoff_packet_v448.py run",
        }
    if packet.get("decision") not in READY_PACKET_DECISIONS or packet.get("pass") is not True:
        return {
            "decision": "v450-operator-preflight-v448-not-ready",
            "pass": False,
            "reason": str(packet.get("reason") or "latest V448/V453/V454/V456/V459 packet did not pass"),
            "next_gate": "repair or rerun handoff packet generation",
            "recommended_command": "",
        }
    if not scripts.get("ok"):
        return {
            "decision": "v450-operator-preflight-script-audit-failed",
            "pass": False,
            "reason": "generated V448 scripts failed private marker audit",
            "next_gate": "regenerate V448 packet",
            "recommended_command": "",
        }
    if live:
        return {
            "decision": "v450-operator-preflight-live-exists-route-v449",
            "pass": True,
            "reason": "V447 live evidence already exists; route with V449",
            "next_gate": "run V449 to classify live result",
            "recommended_command": "python3 scripts/revalidation/wifi_handoff_result_router_v449.py run",
        }
    if private_preflight:
        if private_preflight.get("decision") == "v447-explicit-connect-flow-preflight-ready" and private_preflight.get("pass") is True:
            live_command = ((packet.get("packet") or {}).get("live_command") or "")
            return {
                "decision": "v450-operator-preflight-ready-for-live",
                "pass": True,
                "reason": "private host preflight has passed and live handoff is available",
                "next_gate": "run generated live script",
                "recommended_command": live_command,
            }
        return {
            "decision": "v450-operator-preflight-existing-preflight-blocked",
            "pass": False,
            "reason": str(private_preflight.get("reason") or "latest private preflight did not pass"),
            "next_gate": "inspect private preflight evidence and rerun after repair",
            "recommended_command": ((packet.get("packet") or {}).get("preflight_command") or ""),
        }
    router_decision = (router or {}).get("decision")
    if router_decision and router_decision != "v449-wifi-handoff-packet-ready-run-preflight":
        return {
            "decision": "v450-operator-preflight-router-not-preflight-next",
            "pass": False,
            "reason": f"latest V449 router decision is {router_decision}",
            "next_gate": "inspect V449 routing state",
            "recommended_command": "",
        }
    return {
        "decision": "v450-operator-preflight-ready-run-host-preflight",
        "pass": True,
        "reason": "V448/V453/V454/V456/V459 packet scripts are private and V449 routes the next step to host preflight",
        "next_gate": "run generated host preflight script and provide local Wi-Fi input",
        "recommended_command": ((packet.get("packet") or {}).get("preflight_command") or ""),
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


def script_rows(scripts: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in ("preflight", "live"):
        item = scripts.get(name) or {}
        rows.append(
            [
                name,
                str(item.get("present")),
                str(item.get("mode") or "-"),
                str(item.get("private_mode")),
                str(item.get("secret_literal_found")),
                "; ".join(item.get("issues") or []) or "-",
            ]
        )
    return rows


def guardrails() -> list[str]:
    return [
        "host-side readiness audit only",
        "does not read Wi-Fi secret env values",
        "does not execute generated handoff scripts",
        "checks generated scripts for private permissions and required prompt markers",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    state = manifest["state"]
    evidence_rows = [
        manifest_row("v448_packet", state.get("packet")),
        manifest_row("v449_router", state.get("router")),
        manifest_row("v447_private_preflight", state.get("private_preflight")),
        manifest_row("v447_live", state.get("live")),
        manifest_row("v447_stale_live", state.get("stale_live")),
    ]
    env_rows = [
        [name, str(data.get("present")), str(data.get("length"))]
        for name, data in (state.get("env_state") or {}).items()
    ]
    return "\n".join(
        [
            "# V450 Operator Preflight Readiness Audit",
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
            markdown_table(["item", "decision", "pass", "run_dir", "reason"], evidence_rows),
            "",
            "## Script Audit",
            "",
            markdown_table(["script", "present", "mode", "private", "secret_literal", "issues"], script_rows(state.get("scripts") or {})),
            "",
            "## Env State",
            "",
            markdown_table(["name", "present", "length"], env_rows if env_rows else [["-", "-", "-"]]),
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
    state = route_state(args) if args.command == "run" else {"env_state": env_state(), "scripts": {}}
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
