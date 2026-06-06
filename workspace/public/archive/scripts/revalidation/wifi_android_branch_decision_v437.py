#!/usr/bin/env python3
"""V437 host-side Wi-Fi branch decision gate.

V437 consumes V436 disabled-persistence evidence and chooses the next safe Wi-Fi
branch.  It is host-side only: it does not talk to the device, enable Wi-Fi,
scan, connect, change credentials, send traffic, expose servers, or mutate
routing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v437-android-wifi-branch-decision")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v436-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_v436_manifest() -> Path | None:
    candidates = sorted(
        [
            path / "manifest.json"
            for path in repo_path("tmp/wifi").glob("v436-android-wifi-disabled-persistence-handoff-live-*")
            if (path / "manifest.json").exists()
        ],
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def load_v436(path: Path | None) -> dict[str, Any]:
    manifest = path or latest_v436_manifest()
    if manifest is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False, "state": {}}
    resolved = repo_path(manifest)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False, "state": {}}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    comparison = (payload.get("context") or {}).get("comparison") or {}
    state = comparison.get("state") or (payload.get("classification") or {})
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "wifi_disable_executed": payload.get("wifi_disable_executed"),
        "wifi_bringup_executed": payload.get("wifi_bringup_executed"),
        "state": state,
    }


def state_bool(state: dict[str, Any], key: str) -> bool:
    sample = state.get("sample") or {}
    if key in state:
        return bool(state.get(key))
    return bool(sample.get(key))


def select_branch(v436: dict[str, Any]) -> dict[str, Any]:
    state = v436.get("state") or {}
    sample = state.get("sample") or {}
    contained = (
        bool(v436.get("pass"))
        and state_bool(state, "disabled")
        and state_bool(state, "no_wlan_ip")
        and state_bool(state, "route_absent")
        and state_bool(state, "connectivity_absent")
        and state_bool(state, "listener_safe")
    )
    if not v436.get("present"):
        decision = "v437-wifi-branch-missing-v436"
        pass_ok = False
        branch = "blocked"
        reason = "V436 disabled persistence evidence is missing"
        next_gate = "rerun V436 disabled persistence"
    elif not v436.get("pass"):
        decision = "v437-wifi-branch-v436-failed"
        pass_ok = False
        branch = "blocked"
        reason = "V436 disabled persistence did not pass"
        next_gate = "repair or rerun containment before branch decision"
    elif contained:
        decision = "v437-wifi-branch-controlled-reenable-selected"
        pass_ok = True
        branch = "controlled-android-reenable-observation"
        reason = "Android Wi-Fi is persistently contained, so the next Wi-Fi-progressing gate can safely observe controlled re-enable"
        next_gate = "V438 controlled Android Wi-Fi re-enable observation; no scan/connect/credentials/server/external probes"
    else:
        decision = "v437-wifi-branch-review-required"
        pass_ok = True
        branch = "manual-review"
        reason = "V436 passed but contained-state markers are incomplete"
        next_gate = "review V436 state before re-enable or native branch"
    return {
        "decision": decision,
        "pass": pass_ok,
        "branch": branch,
        "reason": reason,
        "next_gate": next_gate,
        "evidence_state": {
            "enabled_by_status": sample.get("enabled_by_status"),
            "disabled_by_status": sample.get("disabled_by_status"),
            "wlan0_has_ip": sample.get("wlan0_has_ip"),
            "default_route_wlan": sample.get("default_route_wlan"),
            "route_get_wlan": sample.get("route_get_wlan"),
            "connectivity_validated_wifi": sample.get("connectivity_validated_wifi"),
            "dns_surface_wlan": sample.get("dns_surface_wlan"),
            "global_listener_observed": sample.get("global_listener_observed"),
            "disabled": state.get("disabled"),
            "route_absent": state.get("route_absent"),
            "connectivity_absent": state.get("connectivity_absent"),
            "listener_safe": state.get("listener_safe"),
        },
        "blocked_actions": [
            "scan/connect",
            "credential operations",
            "server exposure",
            "external packet probes",
            "DHCP or routing mutation",
            "new Wi-Fi-facing listeners",
        ],
        "v438_constraints": [
            "only `cmd wifi set-wifi-enabled enabled` may be allowed as the bounded mutation",
            "capture pre/post status, route/DNS/connectivity/listener state",
            "do not issue scan/connect or credentials",
            "do not send ping/curl/nc/dig/nslookup traffic",
            "restore native v319 and verify rollback",
        ],
    }


def guardrails() -> list[str]:
    return [
        "host-side branch decision only",
        "no device commands and no device mutations",
        "no Wi-Fi enable/disable, scan/connect, credentials, server exposure, routing mutation, or external probes",
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v436 = load_v436(args.v436_manifest)
    if args.command == "plan":
        branch = {
            "decision": "v437-wifi-branch-plan-ready",
            "pass": True,
            "branch": "not-selected",
            "reason": "host-side Wi-Fi branch decision plan generated",
            "next_gate": "run V437 against V436 disabled-persistence evidence",
            "evidence_state": {},
            "blocked_actions": [
                "scan/connect",
                "credential operations",
                "server exposure",
                "external packet probes",
            ],
            "v438_constraints": [],
        }
    else:
        branch = select_branch(v436)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": branch["decision"],
        "pass": branch["pass"],
        "reason": branch["reason"],
        "host": collect_host_metadata(),
        "v436": v436,
        "branch": branch,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_disable_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    branch = manifest["branch"]
    state_rows = [[key, str(value)] for key, value in branch.get("evidence_state", {}).items()]
    blocked_rows = [[item] for item in branch.get("blocked_actions", [])]
    constraint_rows = [[item] for item in branch.get("v438_constraints", [])]
    return "\n".join(
        [
            "# V437 Wi-Fi Branch Decision",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- branch: `{branch['branch']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{branch['next_gate']}`",
            f"- v436_manifest: `{manifest['v436'].get('path') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_disable_executed: `{manifest['wifi_disable_executed']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence State",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Blocked Actions",
            "",
            markdown_table(["action"], blocked_rows if blocked_rows else [["-"]]),
            "",
            "## V438 Constraints",
            "",
            markdown_table(["constraint"], constraint_rows if constraint_rows else [["-"]]),
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
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"branch: {manifest['branch']['branch']}")
    print(f"next_gate: {manifest['branch']['next_gate']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_disable_executed: {manifest['wifi_disable_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
